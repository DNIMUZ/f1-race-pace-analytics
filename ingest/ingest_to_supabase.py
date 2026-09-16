"""
ETL: FastF1 API -> Supabase Postgres (star schema) for Power BI.

Transforms raw F1 laps into three star-schema tables:
    races    (dimension)  season, round, name, location, date, total laps
    drivers  (dimension)  season, driver code, number, full name, team
    laps     (fact)       one row per lap per driver per race

Usage (run from the repo root):
    # Upsert into Supabase Postgres (uses .env SUPABASE_DATABASE_URL)
    python ingest/ingest_to_supabase.py --year 2026

    # Fallback: write powerbi/*.csv files (no database required)
    python ingest/ingest_to_supabase.py --year 2026 --csv

Idempotent: safe to rerun (uses ON CONFLICT upserts / dataframe overwrite).
"""

import argparse
import logging
import os
import sys
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
OUT_DIR = ROOT / "powerbi"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("ingest")

LAP_COLUMNS = [
    "race_season",
    "race_round",
    "driver_code",
    "driver_number",
    "team",
    "lap_number",
    "lap_time_seconds",
    "compound",
    "tyre_life",
    "track_status",
    "pit_in_time",
    "pit_out_time",
    "is_personal_best",
    "stint",
]


def _load_dotenv():
    env_file = ROOT / ".env"
    if env_file.exists():
        load_dotenv(env_file)


def _enable_cache():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    import fastf1

    fastf1.Cache.enable_cache(str(CACHE_DIR))


def load_sessions(year, skip_failed=True):
    """Yield (event, session) pairs for every race weekend in the season."""
    import fastf1

    schedule = fastf1.get_event_schedule(year)
    for _, event in schedule.iterrows():
        event_name = event["EventName"] if "EventName" in event else event["Location"]
        if "testing" in str(event.get("OfficialEventName", "")).lower():
            logger.info(f"Skipping {event_name} (testing session)")
            continue
        # Races that haven't happened yet have no timing data; skip them
        # upfront instead of burning API calls that are doomed to fail.
        session_date = event.get("Session5Date")
        if pd.notna(session_date):
            try:
                if pd.Timestamp(session_date) > pd.Timestamp.now():
                    logger.info(f"Skipping {event_name} (future race, no data yet)")
                    continue
            except TypeError:
                pass  # tz-aware vs naive comparison; let the API decide below
        try:
            session = fastf1.get_session(year, event_name, "R")
            logger.info(f"Loading {year} {event_name} ...")
            session.load(
                laps=True,
                telemetry=False,
                weather=False,
                messages=False,
            )
            yield event, session
        except Exception as exc:  # noqa: BLE001 - one bad race should not kill the run
            if skip_failed:
                logger.warning(f"Skipping {event_name}: {exc}")
            else:
                raise


def _race_row(event, session):
    total_laps = None
    try:
        total_laps = int(session.total_laps) if session.total_laps else None
    except Exception:  # noqa: BLE001 - unloaded/future sessions provide no lap count
        pass
    return {
        "season": int(session.event["EventDate"].year),
        "round_number": int(session.event.get("RoundNumber", 0)),
        "name": event["EventName"],
        "official_name": event.get("OfficialEventName", ""),
        "country": event.get("Country", ""),
        "location": event.get("Location", ""),
        "event_date": session.event["EventDate"].date(),
        "total_laps": total_laps,
    }


def _driver_rows(session, race_round):
    rows = []
    for code in session.drivers:
        try:
            info = session.get_driver(code)
            rows.append(
                {
                    "race_season": int(session.event["EventDate"].year),
                    "race_round": race_round,
                    "driver_code": code,
                    "driver_number": int(info.DriverNumber),
                    "full_name": getattr(info, "FullName", code),
                    "team": getattr(info, "TeamName", None),
                }
            )
        except Exception:  # noqa: BLE001
            continue
    return rows


def _lap_rows(session, race_round):
    laps = session.laps
    if laps is None or laps.empty:
        return []

    season = int(session.event["EventDate"].year)
    df = laps.copy()
    if "LapTime" in df.columns:
        df["LapTimeSeconds"] = df["LapTime"].dt.total_seconds()
    df = df[df["LapTimeSeconds"].notna()]

    rows = []
    for _, lap in df.iterrows():
        rows.append(
            {
                "race_season": season,
                "race_round": race_round,
                "driver_code": _cell(lap, "Driver"),
                "driver_number": _cell(lap, "DriverNumber"),
                "team": _cell(lap, "Team"),
                "lap_number": int(lap["LapNumber"]),
                "lap_time_seconds": float(lap["LapTimeSeconds"]),
                "compound": _cell(lap, "Compound"),
                "tyre_life": _cell(lap, "TyreLife"),
                "track_status": _cell(lap, "TrackStatus"),
                "pit_in_time": _td_seconds(lap.get("PitInTime")),
                "pit_out_time": _td_seconds(lap.get("PitOutTime")),
                "is_personal_best": _cell(lap, "IsPersonalBest", numpy_compatible=True),
                "stint": _cell(lap, "Stint"),
            }
        )
    return rows


def _cell(series, key, numpy_compatible=False):
    value = series.get(key)
    if value is None or (isinstance(value, float) and pd.isna(value)):
        if numpy_compatible and value is None:
            return None
        return None
    if hasattr(value, "item") and not isinstance(value, str):
        value = value.item()
    return value


def _td_seconds(value):
    if value is None:
        return None
    if hasattr(value, "total_seconds"):
        return float(value.total_seconds())
    return value


def upsert_df(conn, table_name, rows, key_columns):
    """Upsert a list of dict rows into a Postgres table using ON CONFLICT."""
    import psycopg2
    import psycopg2.extras

    if isinstance(rows, list):
        if not rows:
            logger.info(f"No rows for {table_name}, skipping")
            return 0
        df = pd.DataFrame(rows)
    else:
        df = rows

    df = df.astype(object).where(pd.notnull(df), None)
    col_names = list(df.columns)

    # create placeholders
    with conn.cursor() as cur:
        cols_sql = ", ".join(f'"{c}"' for c in col_names)
        updates_sql = ", ".join(f'"{c}" = EXCLUDED."{c}"' for c in col_names if c not in key_columns)
        conflict_sql = ", ".join(key_columns)
        sql = (
            f'INSERT INTO public."{table_name}" ({cols_sql}) VALUES %s '
            f'ON CONFLICT ({conflict_sql}) DO UPDATE SET {updates_sql}'
        )
        values = [tuple(row[col] for col in col_names) for _, row in df.iterrows()]
        psycopg2.extras.execute_values(cur, sql, values, page_size=500)
        logger.info(f"Upserted {len(values)} rows into public.{table_name}")
        return len(values)


def write_csv(rows, filename):
    df = pd.DataFrame(rows) if isinstance(rows, list) else rows
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / filename
    df.to_csv(path, index=False)
    logger.info(f"Wrote {len(df)} rows -> {path}")
    return path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--csv", action="store_true", help="fallback: write powerbi/*.csv instead of Postgres")
    args = parser.parse_args()

    _load_dotenv()
    _enable_cache()

    conn = None
    if not args.csv:
        import psycopg2

        db_url = os.getenv("SUPABASE_DATABASE_URL")
        if not db_url:
            logger.error("SUPABASE_DATABASE_URL not set in .env. Use --csv, or see powerbi/.env.example")
            sys.exit(1)
        conn = psycopg2.connect(db_url)
        conn.autocommit = True

    race_rows, driver_rows, lap_rows = [], [], []
    try:
        for event, session in load_sessions(args.year):
            event_name = event.get("EventName", "?")
            try:
                rr = _race_row(event, session)
                drows = _driver_rows(session, rr["round_number"])
                lrows = _lap_rows(session, rr["round_number"])
            except Exception as exc:  # noqa: BLE001 - one bad race must not kill the run
                logger.warning(f"Skipping {event_name}: {exc}")
                continue
            race_rows.append(rr)
            driver_rows.extend(drows)
            lap_rows.extend(lrows)
            logger.info(f"{rr['name']}: {len(lrows)} laps, {len(drows)} drivers")
    finally:
        if conn:
            conn.close()

    if args.csv:
        write_csv(race_rows, "races.csv")
        write_csv(driver_rows, "drivers.csv")
        write_csv(lap_rows, "laps.csv")
        logger.info("CSV export complete.")
        return

    conn = psycopg2.connect(os.getenv("SUPABASE_DATABASE_URL"))
    conn.autocommit = True
    upsert_df(conn, "races", race_rows, ["season", "round_number"])
    upsert_df(conn, "drivers", driver_rows, ["race_season", "race_round", "driver_code"])
    upsert_df(conn, "laps", lap_rows, ["race_season", "race_round", "driver_code", "lap_number"])
    conn.close()
    logger.info("Supabase upsert complete.")


if __name__ == "__main__":
    main()
"""
Supabase warehouse access for the Streamlit app.

Reads the F1 star schema (races, laps) written by ingest/ingest_to_supabase.py
and reshapes it into the analytics-format DataFrame used by src/analytics.py.

Connection string comes from SUPABASE_DATABASE_URL:
  - Streamlit Secrets (st.secrets) when running on Streamlit Cloud
  - the .env file (git-ignored) when running locally
"""

import os
from pathlib import Path

import pandas as pd

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:
    pass

import psycopg2

CONNECT_TIMEOUT = 10

# Warehouse columns -> analytics-format columns (see src/analytics.py)
COLUMN_MAP = {
    "driver_code": "Driver",
    "lap_number": "LapNumber",
    "lap_time_seconds": "LapTimeSeconds",
    "compound": "Compound",
    "tyre_life": "TyreLife",
}


def _dsn() -> str:
    """Return the Supabase connection string from Secrets or .env."""
    try:
        import streamlit as st

        url = st.secrets.get("SUPABASE_DATABASE_URL")
        if url:
            return url
    except Exception:
        pass
    return os.getenv("SUPABASE_DATABASE_URL", "")


def get_connection():
    """Open a connection to the Supabase warehouse."""
    url = _dsn()
    if not url:
        raise RuntimeError(
            "SUPABASE_DATABASE_URL is not set. "
            "Add it to .env (local) or Streamlit > Settings > Secrets (cloud)."
        )
    return psycopg2.connect(url, connect_timeout=CONNECT_TIMEOUT)


def is_available() -> bool:
    """Cheap reachability probe: connect + SELECT 1."""
    try:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("select 1")
            cur.fetchone()
        return True
    except Exception:
        return False


def list_seasons() -> list:
    """Seasons present in the races table, ascending."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("select distinct season from public.races order by season")
        return [row[0] for row in cur.fetchall()]


def list_races(season: int) -> list:
    """Grand Prix names for a season, in calendar order."""
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            "select name from public.races where season = %s order by round_number",
            (season,),
        )
        return [row[0] for row in cur.fetchall()]


def to_analytics_format(laps_df: pd.DataFrame, rename_map: dict = None) -> pd.DataFrame:
    """
    Rename warehouse laps columns to the analytics format and drop invalid laps.

    Pure function (no DB) so it can be unit-tested.
    """
    cols = rename_map or COLUMN_MAP
    missing = [c for c in cols if c not in laps_df.columns]
    if missing:
        raise ValueError(f"Warehouse laps missing required columns: {missing}")

    df = laps_df[cols.keys()].rename(columns=cols)
    return df[df["LapTimeSeconds"].notna()].reset_index(drop=True)


def load_race_from_db(season: int, race_name: str) -> pd.DataFrame:
    """
    Load one race's laps from the warehouse in analytics format.

    Returns an empty DataFrame when the race has no laps in the warehouse.
    """
    query = """
        select l.driver_code, l.lap_number, l.lap_time_seconds,
               l.compound, l.tyre_life
        from public.laps l
        join public.races r
          on r.season = l.race_season
         and r.round_number = l.race_round
        where r.season = %s and r.name = %s
        order by l.driver_code, l.lap_number
    """
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(query, (season, race_name))
        rows = cur.fetchall()
        columns = [d[0] for d in cur.description]

    if not rows:
        return pd.DataFrame(columns=COLUMN_MAP.values())

    return to_analytics_format(pd.DataFrame(rows, columns=columns))
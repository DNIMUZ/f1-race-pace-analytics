"""
🏎️ Box-Box Analytics: F1 Race Pace Dashboard
Interactive Streamlit dashboard for analyzing F1 race data.
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from src.analytics import (
    load_race_data,
    plot_pace_analysis,
    plot_tyre_degradation,
    get_pit_stops,
    get_driver_stats,
    get_race_narrative,
    get_stint_summary,
    plot_field_delta,
    plot_strategy_grid,
    chart_theme,
)
from src import db
from src.db import load_race_results
import logging

# Configure Streamlit page
st.set_page_config(
    page_title="Box-Box Analytics",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# Keep Streamlit/FastF1's own noisy loggers (they emit DEBUG tracebacks on
# live-source loads) from cluttering the console; app's own logger stays INFO.
for _noisy in ("fastf1", "matplotlib", "urllib3"):
    logging.getLogger(_noisy).setLevel(logging.WARNING)

# ============================================================================
# SIDEBAR: DATA SOURCE + RACE SELECTION
# ============================================================================

st.sidebar.markdown("<div class='side-brand'>Box-Box</div>", unsafe_allow_html=True)
st.sidebar.markdown("---")


@st.cache_data
def db_is_available() -> bool:
    return db.is_available()


source_choice = st.sidebar.radio(
    "Data source",
    ["Auto (warehouse first)", "FastF1 (live)", "Supabase warehouse"],
    index=0,
    help="Auto uses the Supabase warehouse when reachable, otherwise falls back to FastF1.",
)

db_available = db_is_available() if source_choice != "FastF1 (live)" else False

if source_choice == "FastF1 (live)":
    st.sidebar.caption(
        "Tip: on Streamlit Cloud the F1 timing API is usually blocked "
        "(lap data fails to load). Use the Supabase warehouse — it has "
        "all 14 completed 2026 rounds."
    )
    use_db = False
elif source_choice == "Supabase warehouse":
    use_db = True
else:
    use_db = db_available

st.sidebar.markdown("---")

if use_db and not db_available:
    st.sidebar.error(
        "The warehouse isn't reachable yet. "
        "Add SUPABASE_DATABASE_URL under Settings → Secrets, "
        "or switch to FastF1 (live)."
    )
    st.stop()

if use_db:
    try:
        db_seasons = db.list_seasons()
    except RuntimeError as e:
        st.sidebar.error(f"Couldn't reach the warehouse. {e}")
        st.stop()
    if not db_seasons:
        st.sidebar.error("The warehouse is empty. Run the ingest script first.")
        st.stop()
    seasons = db_seasons
else:
    seasons = [2026, 2025, 2024, 2023]

year = st.sidebar.selectbox("Season", seasons, index=0)

FALLBACK_RACES = [
    'Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco',
    'Barcelona', 'Austria', 'Britain', 'Belgium', 'Hungary',
    'Netherlands', 'Italy', 'Spain',
]


@st.cache_data
def fastf1_races(season: int) -> list:
    try:
        import fastf1
        schedule = fastf1.get_event_schedule(season)
        names = [
            row['EventName']
            for _, row in schedule.iterrows()
            if pd.notna(row.get('Session5Date'))
        ]
        return names if names else FALLBACK_RACES
    except Exception:
        return FALLBACK_RACES


if use_db:
    try:
        races = db.list_races(year)
    except RuntimeError as e:
        st.sidebar.error(f"Couldn't reach the warehouse. {e}")
        st.stop()
    if not races:
        st.sidebar.error(f"No races in the warehouse for {year}. Run the ingest script.")
        st.stop()
else:
    races = fastf1_races(year)

race_name = st.sidebar.selectbox("Grand Prix", races, index=0)

st.sidebar.markdown("---")

if use_db:
    st.sidebar.caption("Source — Supabase warehouse\nraces · laps")
else:
    st.sidebar.caption("Source — FastF1 (live timing)")

# ============================================================================
# APPLE-LIKE VISUAL LANGUAGE (light)
# ============================================================================

LIGHT_CSS = """
<style>
    :root {
        --ink: #1D1D1F;
        --muted: #6E6E73;
        --faint: #86868B;
        --line: #ECECEE;
        --card: #F7F7F8;
        --accent: #D70015;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .stApp { background: #FFFFFF; }

    .block-container { max-width: 1180px; margin: 0 auto; }

    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }

    section[data-testid="stSidebar"] {
        background: #FAFAFA;
        border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] hr { border-color: var(--line); }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        box-shadow: none !important;
        border-radius: 10px;
        border: 1px solid #E3E3E6 !important;
        background: #FFFFFF;
    }
    div[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    div[data-baseweb="option"],
    li[data-baseweb="option"] {
        color: var(--ink) !important;
    }
    div[data-baseweb="option"]:hover,
    div[data-baseweb="option"]:focus,
    li[data-baseweb="option"]:hover,
    li[data-baseweb="option"]:focus {
        background-color: var(--card) !important;
        color: var(--ink) !important;
    }
    div[data-baseweb="tag"] {
        border-radius: 8px;
        background-color: var(--accent) !important;
    }
    div[data-baseweb="tag"] span {
        color: #FFFFFF !important;
    }
    div[data-baseweb="tag"] svg {
        fill: #FFFFFF !important;
    }

    button[data-baseweb="tab"] {
        font-size: 14px;
        letter-spacing: .01em;
        color: var(--muted);
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: var(--accent);
        font-weight: 600;
    }
    div[data-baseweb="tab-highlight"] {
        background-color: var(--accent);
    }

    /* Brand hero */
    .hero-eyebrow {
        font-size: 12px;
        letter-spacing: .16em;
        text-transform: uppercase;
        color: var(--faint);
        margin-bottom: 14px;
    }
    .hero-title {
        font-size: 2.7rem;
        font-weight: 700;
        letter-spacing: -.03em;
        color: var(--ink);
        line-height: 1.08;
        margin: 0 0 14px;
    }
    .hero-subtitle {
        font-size: 1.06rem;
        color: var(--muted);
        line-height: 1.5;
        max-width: 640px;
        margin: 0;
    }

    .side-brand {
        font-size: 15px;
        font-weight: 700;
        letter-spacing: -.01em;
        color: var(--ink);
        padding: 4px 0 10px;
    }

    .view-caption {
        font-size: 13px;
        letter-spacing: .02em;
        color: var(--muted);
        margin-top: 30px;
    }

    .stat-card {
        background: var(--card);
        border-radius: 16px;
        padding: 18px 20px 20px;
        height: 100%;
    }
    .stat-label {
        font-size: 11px;
        letter-spacing: .08em;
        text-transform: uppercase;
        color: var(--muted);
        margin: 0 0 8px;
    }
    .stat-value {
        font-size: 2.1rem;
        font-weight: 600;
        letter-spacing: -.02em;
        color: var(--ink);
        line-height: 1.05;
        margin: 0;
    }
    .stat-unit {
        font-size: 1rem;
        font-weight: 400;
        color: var(--faint);
        margin-left: 4px;
    }

    .table-wrap {
        overflow-x: auto;
        background: var(--card);
        border: 1px solid var(--line);
        border-radius: 14px;
        padding: 6px 4px;
    }
    .apple-table {
        width: 100%;
        border-collapse: collapse;
        font-family: inherit;
        font-size: 13px;
    }
    .apple-table th {
        text-align: left;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: .06em;
        color: var(--muted);
        padding: 10px 14px;
    }
    .apple-table td {
        text-align: left;
        color: var(--ink);
        padding: 9px 14px;
        border-bottom: 1px solid var(--line);
    }
    .apple-table tr:last-child td { border-bottom: none; }

    .footer {
        text-align: center;
        color: var(--faint);
        font-size: 12px;
        line-height: 1.8;
    }
    .footer a { color: var(--ink); text-decoration: none; }

    /* Result status badges */
    .res-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 999px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .04em;
    }
    .res-Finished { background: #DDF3E4; color: #1D7A3B; }
    .res-DNF { background: #FDE4E4; color: #B30000; }
    .res-DSQ { background: #1D1D1F; color: #FFFFFF; }
    .res-DNS { background: #FFF3E0; color: #B56A00; }
    .res-DNQ { background: #EDEDEF; color: #6E6E73; }
    .res-Unknown, .res-NotClassified { background: #EDEDEF; color: #6E6E73; }
</style>
"""

st.markdown(LIGHT_CSS, unsafe_allow_html=True)


def apple_table(df: pd.DataFrame) -> None:
    """Render a DataFrame as a smooth, static Apple-style table."""
    float_cols = {c: "{:.2f}" for c in df.select_dtypes(include="float").columns}
    styled = (
        df.style
        .hide(axis='index')
        .format(float_cols)
        .set_table_attributes('class="apple-table"')
        .to_html(border=0)
    )
    st.markdown(f"<div class='table-wrap'>{styled}</div>", unsafe_allow_html=True)


def result_badge(status_class: str) -> str:
    """Render a status badge span for the result table."""
    safe = "".join(c for c in str(status_class) if c.isalnum() or c == "_")
    return f"<span class='res-badge res-{safe}'>{str(status_class)}</span>"


def result_table(results: pd.DataFrame) -> None:
    """Render the official classification with coloured status badges."""
    rows_html = []
    for _, r in results.iterrows():
        pos = int(r["Position"]) if pd.notna(r["Position"]) else "–"
        grid = int(r["Grid"]) if pd.notna(r["Grid"]) else "–"
        delta = ""
        if pd.notna(r["Position"]) and pd.notna(r["Grid"]):
            diff = int(r["Grid"]) - int(r["Position"])
            if diff > 0:
                delta = f"<span style='color:#1D7A3B;font-weight:600'>▲ {diff}</span>"
            elif diff < 0:
                delta = f"<span style='color:#B30000;font-weight:600'>▼ {abs(diff)}</span>"
            else:
                delta = "<span style='color:#86868B'>–</span>"
        points = f"{float(r['Points']):g}" if pd.notna(r["Points"]) else ""
        laps = int(r["Laps"]) if pd.notna(r["Laps"]) else "–"
        full = r["FullName"] if pd.notna(r["FullName"]) else ""
        team = r["Team"] if pd.notna(r["Team"]) else ""
        rows_html.append(
            f"<tr>"
            f"<td>{pos}</td>"
            f"<td><b>{r['Driver']}</b> <span style='color:#86868B;font-size:12px'>{full}</span></td>"
            f"<td>{team}</td>"
            f"<td>{grid}</td>"
            f"<td>{delta}</td>"
            f"<td>{result_badge(r['StatusClass'])}</td>"
            f"<td>{points}</td>"
            f"<td>{laps}</td>"
            f"</tr>"
        )
    st.markdown(
        "<div class='table-wrap'><table class='apple-table'>"
        "<thead><tr><th>Pos</th><th>Driver</th><th>Team</th><th>Grid</th>"
        "<th>± vs grid</th><th>Status</th><th>Pts</th><th>Laps</th></tr></thead>"
        f"<tbody>{''.join(rows_html)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


# ============================================================================
# MAIN HEADER
# ============================================================================

display_race = race_name.replace(" Grand Prix", "")

st.markdown(
    f"""
    <div class='hero-eyebrow'>Formula 1 · {year} season</div>
    <div class='hero-title'>Box-Box Analytics</div>
    <p class='hero-subtitle'>Race pace, tyre behaviour and pit-stop timing — one focused view on every Grand Prix.</p>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
# DATA LOADING
# ============================================================================

@st.cache_data
def load_cached_data(source, year, race):
    try:
        if source == "db":
            laps_df = db.load_race_from_db(year, race)
            if laps_df.empty:
                st.error(f"No laps for {year} {race} in the warehouse. Run the ingest script.")
                return None
            return laps_df
        return load_race_data(year, race)
    except Exception as e:
        st.error(f"Couldn't load this race. {e}")
        return None

source_tag = "db" if use_db else "fastf1"
source_label = "Supabase warehouse" if use_db else "FastF1"

with st.spinner(f"Loading {display_race} from {source_label}…"):
    laps = load_cached_data(source_tag, year, race_name)

if laps is None or laps.empty:
    st.error("Nothing to show for this race. Try another selection.")
    st.stop()

st.markdown(
    f"<div class='view-caption'>Now viewing — {display_race} Grand Prix, {year} · "
    f"{len(laps):,} valid laps across {len(laps['Driver'].unique())} drivers</div>",
    unsafe_allow_html=True,
)

# ============================================================================
# DRIVER SELECTION
# ============================================================================

st.markdown("#### Drivers")

all_drivers = sorted(laps['Driver'].unique())
default_drivers = all_drivers[:3] if len(all_drivers) >= 3 else all_drivers

selected_drivers = st.multiselect(
    "Which drivers to compare",
    options=all_drivers,
    default=default_drivers,
    placeholder="Choose at least one",
    key="driver_select",
)

if not selected_drivers:
    selected_drivers = all_drivers

st.markdown("---")

# ============================================================================
# TABS: RACE STORY + ANALYSIS
# ============================================================================

tab_story, tab_pace, tab_tyre, tab_pits, tab_stats, tab_result = st.tabs(
    ["Race Story", "Pace", "Tyres", "Pit Stops", "Driver Stats", "Result"]
)

# ============================================================================
# TAB 1: RACE STORY
# ============================================================================

with tab_story:
    with st.expander("New here? F1 terms, in plain English"):
        st.markdown("""
        | Term | What it means |
        |---|---|
        | **Lap time** | How long one lap took. A stopwatch — **lower is better**. |
        | **Compound** | The tyre type: SOFT (red, fastest but wears quickest), MEDIUM (orange, balanced), HARD (grey, slowest but lasts longest). |
        | **Stint** | The laps a driver runs on one set of tyres before pitting. |
        | **Pit stop** | Coming in to change tyres — it costs time now to gain time (fresher tyres) later. |
        | **Tyre life / tyre age** | How old the current set is, in laps driven. |
        | **Delta** | A difference. Negative = faster than the reference; positive = slower. |
        | **Typical lap (median)** | The middle value of a driver's laps — a fair "normal pace" that ignores one-off fast or slow laps. |
        | **Consistency** | How much lap times bounce around (standard deviation). Lower = steadier. |
        | **Tyre wear (s/lap)** | Pace lost per extra lap on the same set, read from the slope of the pace line. |
        """)

    st.markdown("##### Race in one read")
    story = get_race_narrative(laps)
    tightness = (
        "competitive"
        if story["field_tightness"] < 1.0
        else "processional"
        if story["field_tightness"] > 2.5
        else "moderately stratified"
    )
    st.markdown(
        f"""
        <p class='hero-subtitle' style='max-width:none'>
        {story['fastest_driver']} turned the fastest lap of the race, a
        {story['fastest_lap']:.3f}s effort on lap {story['fastest_lap_number']}.
        On sustained pace, <b>{story['pace_leader']}</b> led the field with a
        typical lap of {story['pace_median']:.3f}s. {story['most_consistent']}
        was the steadiest hand on the wheel ({story['most_consistent_std']:.3f}s
        spread between their best and worst laps), while
        {story['most_volatile']} was the most uneven ({story['most_volatile_std']:.3f}s).
        A spread of {story['field_tightness']:.2f}s between drivers' typical
        laps makes this a {tightness} race. The single biggest slowdown against
        a driver's own typical pace belonged to {story['swing_driver']} on lap
        {story['swing_lap']} — {story['swing_seconds']:.3f}s.
        </p>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("##### Relative pace vs the field")
    st.caption("Each driver's lap time minus the field median for that lap. "
               "Below zero = faster than the midfield reference.")
    st.plotly_chart(plot_field_delta(laps, selected_drivers), use_container_width=True)
    with st.expander("How to read: relative pace"):
        st.markdown("""
        - For every race lap we take the **median (midpoint) lap time across all drivers**. That's the "field".
        - Each line is a selected driver **minus that reference**: below 0 → faster than the average field that lap; above → slower.
        - **Falling line** = gaining on the field (fresh tyres, clear air). **Rising line** = losing time (tyre wear, traffic, an error).
        - **Sharp one-lap spikes** are usually incidents or lapped traffic — those are your story moments.
        - The dashed line at 0 is the midfield reference — hover any point to see the exact delta, stint and compound.
        """)

    st.markdown("##### Strategy map")
    st.caption("Stint lengths per driver, coloured by compound: red SOFT, "
               "orange MEDIUM, grey HARD, green INTERMEDIATE, blue WET.")
    st.plotly_chart(plot_strategy_grid(laps, selected_drivers), use_container_width=True)
    with st.expander("How to read: strategy map"):
        st.markdown("""
        - Each **row is one driver**; each **coloured block is one stint** — the laps they ran on a single set of tyres.
        - **Gaps between blocks** are pit stops: while in the pits the driver isn't producing pace, so the block just ends.
        - Colours = compound. **Few long blocks** = conservative, tyre-saving strategy. **Many short blocks** = aggressive, push-hard strategy.
        - Hover a block to see the exact stints lap range and compound.
        """)

    st.markdown("##### Stint pace")
    st.caption("Tyre wear (s/lap) is how much pace is lost per extra lap on "
               "that compound — small or negative means healthy tyres.")
    stint_table = get_stint_summary(laps)
    stint_table = stint_table[stint_table["Driver"].isin(selected_drivers)]
    apple_table(stint_table)
    with st.expander("How to read: stint pace table"):
        st.markdown("""
        - One row per **stint** (a driver's run on one set of tyres).
        - **Avg lap / Best lap (s)** — the normal and the fastest lap of that stint. Lower = faster.
        - **Tyre wear (s/lap)** — the slope of the pace line on that set. Around 0 = tyres holding up well; clearly positive = heavy wear; negative (rare) = getting faster as the stint went on.
        - Compare **the same compound across drivers** to see who manages tyres best — that's where races are won.
        """)

# ============================================================================
# TAB 2: RACE PACE
# ============================================================================

with tab_pace:
    st.markdown("##### Lap time evolution")
    st.caption("How each driver's pace unfolds, lap by lap. **Lower = faster** — lap time is a stopwatch.")
    st.plotly_chart(plot_pace_analysis(laps, selected_drivers), use_container_width=True)

    with st.expander("How to read this chart"):
        st.markdown("""
        - Each **line is a driver** and each dot is **one lap time**.
        - **Going down = getting faster** (fresh tyres, clear track). **Going up = getting slower** (tyre wear, traffic, an error).
        - A low, flat line = fast and consistent. A jagged line = eventful race.
        - Hover any point to see the **compound** and **tyre age** for that lap.
        """)

# ============================================================================
# TAB 3: TYRE DEGRADATION
# ============================================================================

with tab_tyre:
    st.markdown("##### Tyre performance")
    st.caption("Lap time against tyre age, for each compound.")

    selected_driver_tyre = st.selectbox(
        "Driver",
        options=selected_drivers if selected_drivers else all_drivers,
        key="tyre_driver",
    )

    st.plotly_chart(plot_tyre_degradation(laps, selected_driver_tyre), use_container_width=True)
    with st.expander("How to read this chart"):
        st.markdown("""
        - **X axis**: how old this set of tyres is (laps driven). **Y axis**: lap time — lower = faster.
        - **A rising line = degradation**: the tyres get slower the older they get.
        - **A steeper line** means that compound (or this driver's style) eats tyres faster.
        - **A flat line** means the tyres are holding up well — great tyre management.
        """)

    stats = get_driver_stats(laps, selected_driver_tyre)
    if stats:
        cards = [
            ("Best lap", stats['best_lap']),
            ("Average lap", stats['avg_lap']),
            ("Consistency", stats['std_dev']),
            ("Total laps", stats['total_laps']),
        ]
        stat_cols = st.columns(4)
        for col, (label, value) in zip(stat_cols, cards):
            with col:
                if label == "Total laps":
                    st.markdown(
                        f"<div class='stat-card'><p class='stat-label'>{label}</p>"
                        f"<p class='stat-value'>{value}</p></div>",
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f"<div class='stat-card'><p class='stat-label'>{label}</p>"
                        f"<p class='stat-value'>{value:.2f}<span class='stat-unit'>s</span></p></div>",
                        unsafe_allow_html=True,
                    )

# ============================================================================
# TAB 4: PIT STOPS
# ============================================================================

with tab_pits:
    st.markdown("##### Pit stops")
    st.caption("When tyres were changed, and for what compound.")

    pit_stops = get_pit_stops(laps)

    if not pit_stops.empty:
        pit_stops_filtered = (
            pit_stops[pit_stops['Driver'].isin(selected_drivers)]
            .sort_values('LapNumber')
            .copy()
        )

        display = pit_stops_filtered.rename(columns={'LapNumber': 'Lap'})
        display['Compound'] = (
            display['CompoundIn'].fillna('?') + ' → ' + display['CompoundOut'].fillna('?')
            if 'CompoundIn' in display.columns
            else display['CompoundOut']
        )
        time_col = 'Stop (s)' if 'StopTime' in display.columns else 'Pit lap (s)'
        display[time_col] = display['StopTime'] if 'StopTime' in display.columns else display['LapTimeSeconds']

        apple_table(display[['Driver', 'Lap', 'Compound', time_col]])
        with st.expander("How to read this table"):
            st.markdown("""
            - One row per **pit stop**. **Lap** = when the stop happened, **Compound** = old → new tyre (`?` = unknown).
            - **Stop (s)** = time spent in the pit box (official timing). When timing isn't available, 'Pit lap (s)' is shown instead — the slow in-lap, which includes the pit-lane speed limit.
            - Short stop, right strategy moment → big race impact. The bar chart below counts stops per driver.
            """)

        pit_count = pit_stops[pit_stops['Driver'].isin(selected_drivers)].groupby('Driver').size().reset_index(name='count')

        fig_pits = go.Figure(data=[
            go.Bar(
                x=pit_count['Driver'],
                y=pit_count['count'],
                marker_color='#D70015',
                text=pit_count['count'],
                textposition='outside',
                cliponaxis=False,
            )
        ])
        fig_pits.update_layout(
            xaxis_title='Driver',
            yaxis_title='Stops',
            height=400,
            **chart_theme(),
        )
        st.plotly_chart(fig_pits, use_container_width=True)
    else:
        st.info("No pit stops detected in this race.")

# ============================================================================
# TAB 5: DRIVER STATS
# ============================================================================

with tab_stats:
    st.markdown("##### Driver comparison")
    st.caption("Best, average and consistency, side by side.")

    stats_data = []
    for driver in selected_drivers:
        driver_stats = get_driver_stats(laps, driver)
        if driver_stats:
            stats_data.append({
                'Driver': driver,
                'Best (s)': f"{driver_stats['best_lap']:.3f}",
                'Average (s)': f"{driver_stats['avg_lap']:.3f}",
                'Median (s)': f"{driver_stats['median_lap']:.3f}",
                'Consistency (s)': f"{driver_stats['std_dev']:.3f}",
                'Laps': driver_stats['total_laps'],
            })

    if stats_data:
        apple_table(pd.DataFrame(stats_data))
        with st.expander("How to read this table"):
            st.markdown("""
            - **Best (s)** — fastest single lap of the race (lower = better).
            - **Average / Median (s)** — typical pace. Median ignores one-off fast/slow laps.
            - **Consistency (s)** — how much laps bounce around the average. Lower = steadier driver, kinder to tyres.
            - **Laps** — how many valid laps were counted for this driver.
            """)
    else:
        st.warning("No stats available for these drivers.")

# ============================================================================
# TAB 6: RACE RESULT / CLASSIFICATION
# ============================================================================

with tab_result:
    st.markdown("##### Official classification")
    st.caption("Final standings with grid comparison and race status.")

    if not use_db:
        st.info("Race results are served from the warehouse. Switch the data source "
                "to Auto or Supabase warehouse.")
    else:
        results = load_race_results(year, race_name)
        if results.empty:
            st.info(
                f"No results in the warehouse for {year} {race_name} yet. "
                "Run `python ingest/ingest_to_supabase.py --year {year}` to add them."
            )
        else:
            result_table(results)
            with st.expander("How to read this table"):
                st.markdown("""
                - **Pos** — official finish position. No number = not classified (retired or excluded).
                - **± vs grid** — places gained (▲) or lost (▼) compared to where they started.
                - **Status badges** — green **Finished**, red **DNF** (did not finish),
                  black **DSQ** (disqualified), orange **DNS** (did not start),
                  grey **DNQ** (did not qualify).
                - **Pts** — championship points scored. **Laps** — how many laps completed.
                - DNF drivers' laps are still available in the Pace/Tyres tabs —
                  partial races are valuable data too.
                """)

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    """
    <div class='footer'>
    Box-Box Analytics — speed, measured.<br>
    FastF1 · Supabase · Streamlit &nbsp;|&nbsp; <a href='https://github.com/diniemuzaffar/f1-race-pace-analytics'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True,
)
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
    chart_theme,
)
from src import db
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

# ============================================================================
# SIDEBAR: MODE + DATA SOURCE + RACE SELECTION
# ============================================================================

st.sidebar.markdown("<div class='side-brand'>Box-Box</div>", unsafe_allow_html=True)

dark = st.sidebar.toggle("Dark mode", value=False, help="Night view for a calm read.")

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
    'Netherlands', 'Italy',
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
# APPLE-LIKE VISUAL LANGUAGE
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
</style>
"""

DARK_CSS = """
<style>
    :root {
        --ink: #F5F5F7;
        --muted: #A1A1A6;
        --faint: #6E6E73;
        --line: #2C2C2E;
        --card: #1C1C1E;
        --accent: #FF453A;
        color-scheme: dark;
    }

    html, body, [class*="css"] {
        font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text",
                     "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }

    .stApp { background: #000000 !important; }

    .block-container { max-width: 1180px; margin: 0 auto; }

    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu, footer { visibility: hidden; }

    section[data-testid="stSidebar"] {
        background: #161618 !important;
        border-right: 1px solid var(--line);
    }
    section[data-testid="stSidebar"] hr { border-color: var(--line); }

    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        box-shadow: none !important;
        border-radius: 10px;
        border: 1px solid #3A3A3C !important;
        background: #1C1C1E !important;
    }
    div[data-baseweb="select"] div[class*="SingleValue"],
    div[data-baseweb="select"] div[class*="multiValue"],
    div[data-baseweb="select"] div[class*="valueContainer"] {
        color: var(--ink) !important;
    }
    div[data-baseweb="select"] input::placeholder,
    div[data-baseweb="input"] input::placeholder {
        color: var(--faint) !important;
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
    label { color: var(--ink) !important; }
    div[data-testid="stSidebar"] p,
    [data-testid="stRadio"] p { color: var(--ink); }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] h4,
    [data-testid="stMarkdownContainer"] h5,
    [data-testid="stMarkdownContainer"] li,
    details summary,
    [data-testid="stExpander"] p { color: var(--ink) !important; }
    [data-testid="stCaptionContainer"] p,
    [data-testid="stSpinner"] p,
    details { color: var(--muted) !important; }

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
        border: 1px solid var(--line);
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
</style>
"""

st.markdown(DARK_CSS if dark else LIGHT_CSS, unsafe_allow_html=True)


def apple_table(df: pd.DataFrame) -> None:
    """Render a DataFrame as a smooth, static Apple-style table."""
    styled = (
        df.style
        .hide(axis='index')
        .format({df.columns[-1]: '{:.2f}'})
        .set_table_attributes('class="apple-table"')
        .to_html(border=0)
    )
    st.markdown(f"<div class='table-wrap'>{styled}</div>", unsafe_allow_html=True)


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
# TABS: MAIN ANALYSIS
# ============================================================================

tab_pace, tab_tyre, tab_pits, tab_stats = st.tabs(["Pace", "Tyres", "Pit Stops", "Driver Stats"])

# ============================================================================
# TAB 1: RACE PACE
# ============================================================================

with tab_pace:
    st.markdown("##### Lap time evolution")
    st.caption("How each driver’s pace unfolds, lap by lap.")
    st.plotly_chart(plot_pace_analysis(laps, selected_drivers, dark=dark), use_container_width=True)

    with st.expander("What to look for"):
        st.markdown("""
        - **A downward trend** — fresh rubber, or a strong phase of the race
        - **An upward trend** — degradation starting to bite
        - **A flat line** — consistent, controlled pace
        - **Sharp spikes** — traffic, errors or strategy moments
        """)

# ============================================================================
# TAB 2: TYRE DEGRADATION
# ============================================================================

with tab_tyre:
    st.markdown("##### Tyre performance")
    st.caption("Lap time against tyre age, for each compound.")

    selected_driver_tyre = st.selectbox(
        "Driver",
        options=selected_drivers if selected_drivers else all_drivers,
        key="tyre_driver",
    )

    st.plotly_chart(plot_tyre_degradation(laps, selected_driver_tyre, dark=dark), use_container_width=True)

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
# TAB 3: PIT STOPS
# ============================================================================

with tab_pits:
    st.markdown("##### Pit stops")
    st.caption("When tyres were changed, and for what compound.")

    pit_stops = get_pit_stops(laps)

    if not pit_stops.empty:
        pit_stops_filtered = pit_stops[pit_stops['Driver'].isin(selected_drivers)].sort_values('LapNumber')
        apple_table(
            pit_stops_filtered.rename(columns={
                'Driver': 'Driver',
                'LapNumber': 'Lap',
                'CompoundOut': 'Compound',
                'LapTimeSeconds': 'Pit lap time (s)'
            })
        )

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
            **chart_theme(dark),
        )
        st.plotly_chart(fig_pits, use_container_width=True)
    else:
        st.info("No pit stops detected in this race.")

# ============================================================================
# TAB 4: DRIVER STATS
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
    else:
        st.warning("No stats available for these drivers.")

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
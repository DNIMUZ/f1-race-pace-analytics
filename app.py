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
    get_driver_stats
)
import logging

# Configure Streamlit page
st.set_page_config(
    page_title="🏎️ Box-Box Analytics",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom CSS for better styling
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .header-title {
        color: #FF0000;
        font-size: 3em;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SIDEBAR: RACE SELECTION
# ============================================================================

st.sidebar.header("🏁 Select Race")
st.sidebar.markdown("---")

# Sidebar inputs
year = st.sidebar.selectbox(
    "📅 Season",
    [2026, 2025, 2024, 2023],
    index=0
)

races = [
    'Bahrain', 'Saudi Arabia', 'Australia', 'Japan', 'China',
    'Miami', 'Monaco', 'Canada', 'Spain', 'Austria',
    'Silverstone', 'Hungary', 'Belgium', 'Italy', 'Singapore'
]

race_name = st.sidebar.selectbox(
    "🏁 Grand Prix",
    races,
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info(
    "📊 **Data Source:** FastF1 (Official FIA Timing Data)\n\n"
    "This dashboard uses real, telemetry-backed F1 timing data from FastF1."
)

# ============================================================================
# MAIN HEADER
# ============================================================================

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"<div class='header-title'>🏎️ Box-Box Analytics</div>", unsafe_allow_html=True)
    st.markdown(f"### {year} {race_name} Grand Prix — Race Pace & Strategy")
with col2:
    st.markdown("")  # Spacing

st.markdown("Analyze F1 race pace, tyre degradation, and pit stop strategies using official timing data.")
st.markdown("---")

# ============================================================================
# DATA LOADING
# ============================================================================

# Use Streamlit caching to avoid reloading data
@st.cache_data
def load_cached_data(year, race):
    try:
        return load_race_data(year, race)
    except Exception as e:
        st.error(f"❌ Error loading race data: {e}")
        return None

# Load data with spinner
with st.spinner(f"📡 Loading {year} {race_name} GP data from FastF1..."):
    laps = load_cached_data(year, race_name)

if laps is None or laps.empty:
    st.error("Could not load race data. Please try another race/year combination.")
    st.stop()

# Display data summary
st.success(f"✅ Loaded {len(laps)} laps from {len(laps['Driver'].unique())} drivers")

# ============================================================================
# DRIVER SELECTION
# ============================================================================

st.subheader("👥 Select Drivers to Compare")

all_drivers = sorted(laps['Driver'].unique())
default_drivers = all_drivers[:3] if len(all_drivers) >= 3 else all_drivers

selected_drivers = st.multiselect(
    "Choose drivers (or leave empty to show all)",
    options=all_drivers,
    default=default_drivers,
    key="driver_select"
)

if not selected_drivers:
    selected_drivers = all_drivers

st.markdown("---")

# ============================================================================
# TABS: MAIN ANALYSIS
# ============================================================================

tab1, tab2, tab3, tab4 = st.tabs(["📊 Race Pace", "🛞 Tyre Degradation", "⛽ Pit Stops", "📈 Driver Stats"])

# ============================================================================
# TAB 1: RACE PACE
# ============================================================================

with tab1:
    st.subheader("Lap Time Evolution")
    st.markdown(
        "Visualize how lap times evolve throughout the race. "
        "Steeper drops indicate better pace; flat lines show consistency."
    )
    
    if selected_drivers:
        fig_pace = plot_pace_analysis(laps, selected_drivers)
        st.plotly_chart(fig_pace, use_container_width=True)
        
        # Add insights
        with st.expander("📊 What to look for"):
            st.markdown("""
            - **Downward slope:** Tyre warm-up or fresh rubber after pit stop
            - **Upward slope:** Tyre degradation (older tyres = slower)
            - **Flat line:** Consistent pace (often indicator of great driving)
            - **Sharp spikes:** Mistakes, traffic, or fuel adjustment
            """)
    else:
        st.warning("Select at least one driver")

# ============================================================================
# TAB 2: TYRE DEGRADATION
# ============================================================================

with tab2:
    st.subheader("Tyre Degradation Analysis")
    st.markdown(
        "Compare tyre performance across compounds (SOFT, MEDIUM, HARD). "
        "Shows lap time vs. tyre age in laps."
    )
    
    selected_driver_tyre = st.selectbox(
        "Choose a driver to analyze",
        options=selected_drivers if selected_drivers else all_drivers,
        key="tyre_driver"
    )
    
    if selected_driver_tyre:
        fig_tyre = plot_tyre_degradation(laps, selected_driver_tyre)
        st.plotly_chart(fig_tyre, use_container_width=True)
        
        # Driver stats for selected driver
        stats = get_driver_stats(laps, selected_driver_tyre)
        if stats:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("🏁 Best Lap", f"{stats['best_lap']:.2f}s")
            with col2:
                st.metric("📊 Avg Lap", f"{stats['avg_lap']:.2f}s")
            with col3:
                st.metric("📈 Consistency (σ)", f"{stats['std_dev']:.2f}s")
            with col4:
                st.metric("🔢 Total Laps", stats['total_laps'])

# ============================================================================
# TAB 3: PIT STOPS
# ============================================================================

with tab3:
    st.subheader("Pit Stop Timeline & Strategy")
    st.markdown("See when each driver made pit stops and what compounds were used.")
    
    pit_stops = get_pit_stops(laps)
    
    if not pit_stops.empty:
        # Filter pit stops by selected drivers
        pit_stops_filtered = pit_stops[pit_stops['Driver'].isin(selected_drivers)].sort_values('LapNumber')
        
        # Display pit stop table
        st.dataframe(
            pit_stops_filtered.rename(columns={
                'Driver': '👤 Driver',
                'LapNumber': '🔢 Lap',
                'CompoundOut': '🛞 Compound',
                'LapTimeSeconds': '⏱️ Pit Lap Time (s)'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        # Pit stop count chart
        st.subheader("Pit Stops per Driver")
        pit_count = pit_stops[pit_stops['Driver'].isin(selected_drivers)].groupby('Driver').size().reset_index(name='Pit Stops')
        
        fig_pits = go.Figure(data=[
            go.Bar(
                x=pit_count['Driver'],
                y=pit_count['Pit Stops'],
                marker_color='#FF0000',
                text=pit_count['Pit Stops'],
                textposition='outside'
            )
        ])
        fig_pits.update_layout(
            title="Number of Pit Stops by Driver",
            xaxis_title="Driver",
            yaxis_title="Pit Stops",
            height=400,
            template='plotly_white'
        )
        st.plotly_chart(fig_pits, use_container_width=True)
    else:
        st.info("No pit stops detected in this race")

# ============================================================================
# TAB 4: DRIVER STATS
# ============================================================================

with tab4:
    st.subheader("Driver Performance Summary")
    st.markdown("Compare key metrics across all selected drivers")
    
    # Build stats for all selected drivers
    stats_data = []
    for driver in selected_drivers:
        driver_stats = get_driver_stats(laps, driver)
        if driver_stats:
            stats_data.append({
                'Driver': driver,
                'Best Lap (s)': f"{driver_stats['best_lap']:.3f}",
                'Avg Lap (s)': f"{driver_stats['avg_lap']:.3f}",
                'Median Lap (s)': f"{driver_stats['median_lap']:.3f}",
                'Std Dev (s)': f"{driver_stats['std_dev']:.3f}",
                'Total Laps': driver_stats['total_laps']
            })
    
    if stats_data:
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)
    else:
        st.warning("No stats available for selected drivers")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #999; font-size: 0.9em;'>
    🏎️ <b>Box-Box Analytics</b> — Built with FastF1, Pandas, Plotly & Streamlit<br>
    📊 Official FIA Timing Data | 📱 Open Source | 🔗 <a href='https://github.com/diniemuzaffar/f1-race-pace-analytics'>GitHub</a>
    </div>
    """,
    unsafe_allow_html=True
)

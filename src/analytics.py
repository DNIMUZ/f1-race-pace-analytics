"""
Core analytics functions for F1 race data analysis.
Provides utilities for pace analysis, tyre degradation, and pit stop detection.
"""

import fastf1
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import List, Optional
import logging
import os
from pathlib import Path

# Create cache directory if it doesn't exist
cache_dir = Path(__file__).parent.parent / 'data' / 'cache'
cache_dir.mkdir(parents=True, exist_ok=True)

# Enable FastF1 caching for faster subsequent loads
fastf1.Cache.enable_cache(str(cache_dir))

logger = logging.getLogger(__name__)

# Apple-like neutral chart theme shared by all Plotly figures
APPLE_THEME_LAYOUT = {
    "template": "plotly_white",
    "font": dict(
        family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
        size=13,
        color="#1D1D1F",
    ),
    "margin": dict(l=70, r=30, t=24, b=52),
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "hoverlabel": dict(bgcolor="#1D1D1F", font=dict(color="#FFFFFF", size=13)),
    "xaxis": dict(showgrid=True, gridcolor="#ECECEE", zeroline=False),
    "yaxis": dict(showgrid=True, gridcolor="#ECECEE", zeroline=False),
    "legend": dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="rgba(0,0,0,0)",
    ),
}

APPLE_THEME_LAYOUT_DARK = {
    "template": "plotly_dark",
    "font": dict(
        family="-apple-system, 'Segoe UI', Helvetica, Arial, sans-serif",
        size=13,
        color="#F5F5F7",
    ),
    "margin": dict(l=70, r=30, t=24, b=52),
    "plot_bgcolor": "rgba(0,0,0,0)",
    "paper_bgcolor": "rgba(0,0,0,0)",
    "hoverlabel": dict(bgcolor="#F5F5F7", font=dict(color="#1D1D1F", size=13)),
    "xaxis": dict(showgrid=True, gridcolor="#2C2C2E", zeroline=False),
    "yaxis": dict(showgrid=True, gridcolor="#2C2C2E", zeroline=False),
    "legend": dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0,
        bgcolor="rgba(0,0,0,0)",
    ),
}


def chart_theme(dark: bool = False) -> dict:
    """Pick the chart layout for the current mode."""
    return APPLE_THEME_LAYOUT_DARK if dark else APPLE_THEME_LAYOUT


ACCENT_CYCLIC = [
    "#D70015",
    "#1D1D1F",
    "#6E6E73",
    "#A2845E",
    "#0071E3",
    "#AF52DE",
    "#FF9500",
    "#00C7BE",
    "#34C759",
    "#5E5CE6",
]


def load_race_data(year: int, race: str) -> pd.DataFrame:
    """
    Load F1 race session data and return laps dataframe.
    
    Args:
        year: Championship year (e.g., 2024, 2025, 2026)
        race: Grand Prix name (e.g., 'Bahrain', 'Monaco', 'Canada')
    
    Returns:
        DataFrame with lap data, including LapTime converted to seconds
    
    Raises:
        ValueError: If race data cannot be loaded
    """
    try:
        session = fastf1.get_session(year, race, 'R')  # 'R' = Race
        session.load()

        # On Streamlit Cloud (or any host where livetiming.formula1.com is
        # blocked), FastF1 silently swallows API failures inside soft
        # exceptions and never sets the _laps attribute. Detect that here
        # and raise a clear, actionable error instead of the cryptic
        # "The data you are trying to access has not been loaded yet."
        if not hasattr(session, '_laps'):
            raise ValueError(
                "FastF1 could not retrieve lap data for this session. "
                "This usually happens on Streamlit Cloud because the "
                "official F1 timing API (livetiming.formula1.com) blocks "
                "cloud datacenter IPs. Use the Supabase warehouse source "
                "(default) instead of FastF1 live, or run the app locally "
                "where the API is reachable."
            )

        laps = session.laps

        # Convert LapTime to seconds for easier analysis
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

        # Keep official pit-lane timing in seconds so pit stops can be detected
        # from timing data instead of compound-change heuristics.
        laps = _expose_pit_timing(laps)

        # Filter out invalid laps (pit stops, outlaps, etc.)
        laps = laps[laps['LapTimeSeconds'].notna()].copy()

        logger.info(f"Loaded {len(laps)} valid laps from {year} {race} GP")
        return laps

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Failed to load race data: {e}")
        raise ValueError(f"Could not load {year} {race} data: {e}")


def plot_pace_analysis(laps: pd.DataFrame, drivers: List[str], dark: bool = False) -> go.Figure:
    """
    Plot lap time evolution for selected drivers.
    Shows consistency, pace, and degradation over the race.
    
    Args:
        laps: DataFrame with lap data
        drivers: List of driver abbreviations (e.g., ['VER', 'LEC', 'HAM'])
    
    Returns:
        Plotly figure with interactive lap time chart
    """
    fig = go.Figure()

    for i, driver in enumerate(drivers):
        driver_laps = laps[laps['Driver'] == driver].sort_values('LapNumber')

        fig.add_trace(go.Scatter(
            x=driver_laps['LapNumber'],
            y=driver_laps['LapTimeSeconds'],
            mode='lines+markers',
            name=driver,
            line=dict(width=2, color=ACCENT_CYCLIC[i % len(ACCENT_CYCLIC)]),
            marker=dict(size=5),
            text=[f"Compound: {c}<br>Tyre Life: {t}"
                  for c, t in zip(driver_laps['Compound'], driver_laps['TyreLife'])],
            hovertemplate='<b>%{fullData.name}</b><br>Lap %{x}<br>Time: %{y:.3f}s<br>%{text}<extra></extra>'
        ))

    fig.update_layout(
        xaxis_title='Lap number',
        yaxis_title='Lap time (s)',
        hovermode='x unified',
        height=560,
        **chart_theme(dark)
    )

    return fig


def plot_tyre_degradation(laps: pd.DataFrame, driver: str, dark: bool = False) -> go.Figure:
    """
    Plot tyre degradation curve showing lap time vs tyre age.
    Separate traces for each compound (SOFT, MEDIUM, HARD).
    
    Args:
        laps: DataFrame with lap data
        driver: Driver abbreviation (e.g., 'VER')
    
    Returns:
        Plotly figure with tyre degradation analysis
    """
    driver_laps = laps[laps['Driver'] == driver].copy()
    
    if driver_laps.empty:
        return go.Figure().add_annotation(text=f"No data for driver {driver}")
    
    fig = go.Figure()
    
    for compound in sorted(driver_laps['Compound'].unique()):
        stint = driver_laps[driver_laps['Compound'] == compound].sort_values('TyreLife')
        
        # Color mapping for compounds
        color_map = {
            'SOFT': '#d32f2f',    # Red
            'MEDIUM': '#f57c00',  # Orange
            'HARD': '#fff176'     # Yellow
        }
        
        fig.add_trace(go.Scatter(
            x=stint['TyreLife'],
            y=stint['LapTimeSeconds'],
            mode='markers+lines',
            name=f'{compound} ({len(stint)} laps)',
            marker=dict(size=8, color=color_map.get(compound, 'blue')),
            line=dict(width=2),
            hovertemplate='<b>%{fullData.name}</b><br>Tyre Age: %{x} laps<br>Lap Time: %{y:.3f}s<extra></extra>'
        ))
    
    fig.update_layout(
        xaxis_title='Tyre age (laps)',
        yaxis_title='Lap time (s)',
        height=560,
        **chart_theme(dark)
    )

    return fig


def _expose_pit_timing(laps: pd.DataFrame) -> pd.DataFrame:
    """Convert FastF1 PitInTime/PitOutTime timedeltas into float seconds."""
    for col in ("PitInTime", "PitOutTime"):
        if col in laps.columns:
            laps[col] = pd.to_timedelta(laps[col], errors="coerce").dt.total_seconds()
    return laps


# Canonical output schema for the two pit-stop detection methods.
PIT_STOP_TIMING_COLUMNS = [
    "Driver",
    "LapNumber",
    "CompoundIn",
    "CompoundOut",
    "PitInTime",
    "PitOutTime",
    "StopTime",
]
FALLBACK_COLUMNS = [
    "Driver",
    "LapNumber",
    "CompoundIn",
    "CompoundOut",
    "LapTimeSeconds",
]


def _pit_stops_from_timing(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Detect pit stops from official pit-lane timing (PitInTime/PitOutTime, seconds).

    A stop is recorded on every lap where PitInTime is present (the inlap).
    CompoundOut is the compound fitted afterwards, read from the outlap (the
    next lap), along with its PitOutTime; StopTime is the elapsed pit time.
    """
    stops = laps[laps["PitInTime"].notna()].copy()
    if stops.empty:
        return pd.DataFrame(columns=PIT_STOP_TIMING_COLUMNS)

    # Shift the outlap one lap back so it lines up with the pit-in lap:
    # outlap row (LapNumber N+1) is keyed as N, attaching its compound and
    # pit-exit time to the pit-in lap.
    next_laps = laps[["Driver", "LapNumber", "Compound", "PitOutTime"]].copy()
    next_laps["LapNumber"] = next_laps["LapNumber"] - 1

    merged = stops.merge(
        next_laps,
        on=["Driver", "LapNumber"],
        how="left",
        suffixes=("", "_Next"),
    )

    rows = pd.DataFrame(
        {
            "Driver": merged["Driver"],
            "LapNumber": merged["LapNumber"],
            "CompoundIn": merged["Compound"],
            "CompoundOut": merged["Compound_Next"],
            "PitInTime": merged["PitInTime"],
            "PitOutTime": merged["PitOutTime_Next"],
            "StopTime": merged["PitOutTime_Next"] - merged["PitInTime"],
        }
    )
    return rows.sort_values("LapNumber").reset_index(drop=True)


def _pit_stops_from_compound_change(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Heuristic fallback: detect pit stops as compound changes between consecutive laps.

    Used when official pit-lane timing is missing (e.g. legacy CSV exports).
    """
    laps_sorted = laps.sort_values(["Driver", "LapNumber"]).copy()

    pit_stops_list = []
    for driver in laps_sorted["Driver"].unique():
        driver_laps = laps_sorted[laps_sorted["Driver"] == driver].reset_index(drop=True)

        for i in range(len(driver_laps) - 1):
            current_compound = driver_laps.loc[i, "Compound"]
            next_compound = driver_laps.loc[i + 1, "Compound"]

            # Pit stop occurred if compound changed
            if (
                current_compound != next_compound
                and pd.notna(current_compound)
                and pd.notna(next_compound)
            ):
                pit_stops_list.append(
                    {
                        "Driver": driver,
                        "LapNumber": driver_laps.loc[i, "LapNumber"],
                        "CompoundIn": current_compound,
                        "CompoundOut": next_compound,  # New tyre after pit stop
                        "LapTimeSeconds": driver_laps.loc[i, "LapTimeSeconds"],
                    }
                )

    if pit_stops_list:
        return (
            pd.DataFrame(pit_stops_list)
            .sort_values("LapNumber")
            .reset_index(drop=True)
        )
    return pd.DataFrame(columns=FALLBACK_COLUMNS)


def get_pit_stops(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Extract pit stop events from lap data.

    Primary method: official pit-lane timing (PitInTime / PitOutTime, in
    seconds) when available — records the inlap, compounds in/out and the
    elapsed pit time. Falls back to compound-change detection for sources
    without timing columns.

    Returns a DataFrame with Driver, LapNumber, CompoundIn, CompoundOut plus
    either StopTime/PitInTime/PitOutTime (timing) or LapTimeSeconds (fallback).
    """
    if "PitInTime" in laps.columns and laps["PitInTime"].notna().any():
        return _pit_stops_from_timing(laps)
    return _pit_stops_from_compound_change(laps)


def get_driver_stats(laps: pd.DataFrame, driver: str) -> dict:
    """
    Calculate summary statistics for a driver's race performance.
    
    Args:
        laps: DataFrame with lap data
        driver: Driver abbreviation (e.g., 'VER')
    
    Returns:
        Dictionary with key metrics (best lap, consistency, avg lap time, etc.)
    """
    driver_laps = laps[laps['Driver'] == driver]['LapTimeSeconds']
    
    if driver_laps.empty:
        return {}
    
    return {
        'best_lap': driver_laps.min(),
        'avg_lap': driver_laps.mean(),
        'std_dev': driver_laps.std(),
        'total_laps': len(driver_laps),
        'median_lap': driver_laps.median()
    }

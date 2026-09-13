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

ACCENT_CYCLIC = [
    "#1D1D1F",
    "#D70015",
    "#0071E3",
    "#6E6E73",
    "#34C759",
    "#AF52DE",
    "#FF9500",
    "#00C7BE",
    "#A2845E",
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
        laps = session.laps
        
        # Convert LapTime to seconds for easier analysis
        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()
        
        # Filter out invalid laps (pit stops, outlaps, etc.)
        laps = laps[laps['LapTimeSeconds'].notna()].copy()
        
        logger.info(f"Loaded {len(laps)} valid laps from {year} {race} GP")
        return laps
    
    except Exception as e:
        logger.error(f"Failed to load race data: {e}")
        raise ValueError(f"Could not load {year} {race} data: {e}")


def plot_pace_analysis(laps: pd.DataFrame, drivers: List[str]) -> go.Figure:
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
        **APPLE_THEME_LAYOUT
    )

    return fig


def plot_tyre_degradation(laps: pd.DataFrame, driver: str) -> go.Figure:
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
        **APPLE_THEME_LAYOUT
    )

    return fig


def get_pit_stops(laps: pd.DataFrame) -> pd.DataFrame:
    """
    Extract pit stop events from lap data.
    Detects pit stops as moments where tyre compound changes between consecutive laps.
    
    Args:
        laps: DataFrame with lap data
    
    Returns:
        DataFrame with pit stop details (Driver, LapNumber, CompoundIn, CompoundOut, etc.)
    """
    laps_sorted = laps.sort_values(['Driver', 'LapNumber']).copy()
    
    # Detect pit stops: compound changes between consecutive laps
    pit_stops_list = []
    
    for driver in laps_sorted['Driver'].unique():
        driver_laps = laps_sorted[laps_sorted['Driver'] == driver].reset_index(drop=True)
        
        for i in range(len(driver_laps) - 1):
            current_compound = driver_laps.loc[i, 'Compound']
            next_compound = driver_laps.loc[i + 1, 'Compound']
            
            # Pit stop occurred if compound changed
            if current_compound != next_compound and pd.notna(current_compound) and pd.notna(next_compound):
                pit_stops_list.append({
                    'Driver': driver,
                    'LapNumber': driver_laps.loc[i, 'LapNumber'],
                    'CompoundOut': next_compound,  # New tyre after pit stop
                    'LapTimeSeconds': driver_laps.loc[i, 'LapTimeSeconds']
                })
    
    if pit_stops_list:
        return pd.DataFrame(pit_stops_list).sort_values('LapNumber')
    else:
        return pd.DataFrame(columns=['Driver', 'LapNumber', 'CompoundOut', 'LapTimeSeconds'])


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

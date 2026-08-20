import pandas as pd

from src.analytics import (
    get_driver_stats,
    get_pit_stops,
    plot_pace_analysis,
    plot_tyre_degradation,
)


def sample_laps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "Driver": ["VER", "VER", "VER", "HAM"],
            "LapNumber": [1, 2, 3, 1],
            "Compound": ["MEDIUM", "MEDIUM", "HARD", "SOFT"],
            "TyreLife": [1, 2, 1, 1],
            "LapTimeSeconds": [92.1, 92.4, 93.0, 93.5],
        }
    )


def test_get_pit_stops_detects_compound_change() -> None:
    pit_stops = get_pit_stops(sample_laps())

    assert len(pit_stops) == 1
    assert pit_stops.iloc[0]["Driver"] == "VER"
    assert pit_stops.iloc[0]["LapNumber"] == 2
    assert pit_stops.iloc[0]["CompoundOut"] == "HARD"


def test_get_driver_stats_returns_expected_metrics() -> None:
    stats = get_driver_stats(sample_laps(), "VER")

    assert stats["best_lap"] == 92.1
    assert stats["avg_lap"] == (92.1 + 92.4 + 93.0) / 3
    assert stats["total_laps"] == 3
    assert stats["median_lap"] == 92.4


def test_plot_functions_return_plotly_figures() -> None:
    laps = sample_laps()

    pace_figure = plot_pace_analysis(laps, ["VER"])
    tyre_figure = plot_tyre_degradation(laps, "VER")

    assert len(pace_figure.data) == 1
    assert len(tyre_figure.data) == 2


def test_get_pit_stops_returns_empty_schema_without_changes() -> None:
    laps = sample_laps().assign(Compound="MEDIUM")

    pit_stops = get_pit_stops(laps)

    assert pit_stops.empty
    assert list(pit_stops.columns) == [
        "Driver",
        "LapNumber",
        "CompoundOut",
        "LapTimeSeconds",
    ]

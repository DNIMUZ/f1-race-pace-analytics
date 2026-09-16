import pandas as pd
import pytest

from src.analytics import (
    get_driver_stats,
    get_pit_stops,
    plot_pace_analysis,
    plot_tyre_degradation,
    derive_stints,
    get_stint_summary,
    get_field_pace_delta,
    get_race_narrative,
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


def sample_laps_with_timing() -> pd.DataFrame:
    """VER pits at the end of lap 3 (inlap), outlaps on lap 4."""
    return pd.DataFrame(
        {
            "Driver": ["VER", "VER", "VER", "VER", "HAM"],
            "LapNumber": [1, 2, 3, 4, 1],
            "Compound": ["MEDIUM", "MEDIUM", "MEDIUM", "HARD", "SOFT"],
            "TyreLife": [1, 2, 3, 1, 1],
            "LapTimeSeconds": [92.1, 92.4, 97.0, 94.0, 93.5],
            "PitInTime": [None, None, 536.0, None, None],
            "PitOutTime": [None, None, None, 562.0, None],
        }
    )


def test_get_pit_stops_detects_compound_change() -> None:
    pit_stops = get_pit_stops(sample_laps())

    assert len(pit_stops) == 1
    assert pit_stops.iloc[0]["Driver"] == "VER"
    assert pit_stops.iloc[0]["LapNumber"] == 2
    assert pit_stops.iloc[0]["CompoundIn"] == "MEDIUM"
    assert pit_stops.iloc[0]["CompoundOut"] == "HARD"


def test_get_pit_stops_uses_official_timing_when_available() -> None:
    pit_stops = get_pit_stops(sample_laps_with_timing())

    assert len(pit_stops) == 1
    row = pit_stops.iloc[0]
    assert row["Driver"] == "VER"
    assert row["LapNumber"] == 3
    assert row["CompoundIn"] == "MEDIUM"
    assert row["CompoundOut"] == "HARD"
    assert row["PitInTime"] == 536.0
    assert row["PitOutTime"] == 562.0
    assert row["StopTime"] == 26.0


def test_get_pit_stops_falls_back_when_timing_is_all_null() -> None:
    laps = sample_laps_with_timing().assign(PitInTime=None, PitOutTime=None)

    pit_stops = get_pit_stops(laps)

    assert len(pit_stops) == 1  # only VER's MEDIUM -> HARD change at lap 3
    assert pit_stops.iloc[0]["LapNumber"] == 3
    assert "StopTime" not in pit_stops.columns
    assert "LapTimeSeconds" in pit_stops.columns


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
        "CompoundIn",
        "CompoundOut",
        "LapTimeSeconds",
    ]


def test_derive_stints_increments_on_compound_change() -> None:
    stints = derive_stints(sample_laps())

    ver = stints[stints["Driver"] == "VER"].sort_values("LapNumber")
    assert list(ver["Stint"]) == [1, 1, 2]  # MEDIUM, MEDIUM, HARD
    assert ver["Stint"].dtype.kind == "i"


def test_get_stint_summary_reports_compound_and_average() -> None:
    summary = get_stint_summary(sample_laps())

    ver_stint_1 = summary[(summary["Driver"] == "VER") & (summary["Stint"] == 1)]
    assert ver_stint_1["Compound"].iloc[0] == "MEDIUM"
    assert ver_stint_1["Avg lap (s)"].iloc[0] == pytest.approx((92.1 + 92.4) / 2)


def test_get_field_pace_delta_negative_when_faster_than_field() -> None:
    delta = get_field_pace_delta(sample_laps(), "VER")

    lap1 = delta[delta["LapNumber"] == 1].iloc[0]
    # VER 92.1 vs field median of (92.1, 93.5) = 92.8 -> faster (negative)
    assert lap1["DeltaSeconds"] == pytest.approx(92.1 - 92.8)


def test_get_race_narrative_returns_story_metrics() -> None:
    story = get_race_narrative(sample_laps())

    assert story["fastest_driver"] == "VER"
    assert story["fastest_lap"] == 92.1
    assert story["pace_leader"] == "VER"
    assert story["swing_driver"] == "VER"
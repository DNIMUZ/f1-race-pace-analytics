import pandas as pd
import pytest

from src.db import (
    COLUMN_MAP,
    RESULTS_COLUMN_MAP,
    classify_result_status,
    to_analytics_format,
    to_results_format,
)


def warehouse_laps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "driver_code": ["VER", "VER", "HAM"],
            "lap_number": [1, 2, 1],
            "lap_time_seconds": [92.1, None, 93.5],
            "compound": ["MEDIUM", "HARD", "SOFT"],
            "tyre_life": [1, 1, 1],
            "pit_in_time": [None, 536.0, 900.0],
            "pit_out_time": [None, None, None],
        }
    )


def test_to_analytics_format_renames_columns() -> None:
    result = to_analytics_format(warehouse_laps())

    assert list(result.columns) == [
        "Driver",
        "LapNumber",
        "LapTimeSeconds",
        "Compound",
        "TyreLife",
        "PitInTime",
        "PitOutTime",
    ]
    assert result["Driver"].tolist() == ["VER", "HAM"]


def test_to_analytics_format_keeps_pit_timing() -> None:
    result = to_analytics_format(warehouse_laps())

    ham = result[result["Driver"] == "HAM"]
    assert ham.iloc[0]["PitInTime"] == 900.0
    assert pd.isna(ham.iloc[0]["PitOutTime"])


def test_to_analytics_format_drops_rows_with_null_lap_time() -> None:
    result = to_analytics_format(warehouse_laps())

    assert len(result) == 2
    assert result["LapTimeSeconds"].notna().all()


def test_to_analytics_format_raises_on_missing_columns() -> None:
    incomplete = warehouse_laps().drop(columns=["tyre_life"])

    with pytest.raises(ValueError, match="required columns"):
        to_analytics_format(incomplete)


def test_column_map_covers_analytics_contract() -> None:
    expected = {
        "Driver",
        "LapNumber",
        "LapTimeSeconds",
        "Compound",
        "TyreLife",
        "PitInTime",
        "PitOutTime",
    }

    assert set(COLUMN_MAP.values()) == expected


def warehouse_results() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "driver_code": ["VER", "WIL", "NOR"],
            "full_name": ["Max Verstappen", "George Russell", "Lando Norris"],
            "team": ["Red Bull", "Mercedes", "McLaren"],
            "grid_position": [2, 1, 5],
            "position": [1, None, 3],
            "classified_position": ["P1", None, "P3"],
            "status": ["Finished", "DNF", "Finished"],
            "points": [25, None, 15],
            "laps": [58, 40, 58],
        }
    )


def test_results_column_map_covers_contract() -> None:
    assert set(RESULTS_COLUMN_MAP.values()) == {
        "Driver",
        "FullName",
        "Team",
        "Grid",
        "Position",
        "Classified",
        "Status",
        "Points",
        "Laps",
    }


def test_classify_result_status_maps_status_strings() -> None:
    assert classify_result_status("Finished") == "Finished"
    assert classify_result_status("+1 Lap") == "Finished"
    assert classify_result_status("DNF") == "DNF"
    assert classify_result_status("Accident") == "DNF"
    assert classify_result_status("Engine") == "DNF"
    assert classify_result_status("DSQ") == "DSQ"
    assert classify_result_status("Disqualified") == "DSQ"
    assert classify_result_status("DNS") == "DNS"
    assert classify_result_status("DNQ") == "DNQ"
    assert classify_result_status(None) == "Unknown"


def test_to_results_format_maps_status_and_moves_unclassified_last() -> None:
    result = to_results_format(warehouse_results())

    assert list(result.columns) == [
        "Driver",
        "FullName",
        "Team",
        "Grid",
        "Position",
        "Classified",
        "Status",
        "Points",
        "Laps",
        "StatusClass",
    ]
    assert result.loc[0, "Driver"] == "VER"
    assert result.loc[1, "Driver"] == "NOR"
    assert result.loc[2, "Driver"] == "WIL"  # DNF (no position) sorted last
    assert result.loc[2, "StatusClass"] == "DNF"


def test_to_results_format_raises_on_missing_columns() -> None:
    incomplete = warehouse_results().drop(columns=["points"])

    with pytest.raises(ValueError, match="required columns"):
        to_results_format(incomplete)
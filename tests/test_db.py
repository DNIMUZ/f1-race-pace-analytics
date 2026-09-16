import pandas as pd
import pytest

from src.db import COLUMN_MAP, to_analytics_format


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
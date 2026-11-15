"""Tests for ai.preprocess."""
import pandas as pd

from ai.preprocess import add_mission_day, split_usable


def frame():
    t = pd.Timestamp("2026-11-01T00:00:00Z")
    rows = [
        ("A2", "HEART_RATE", 61.0, t + pd.Timedelta(minutes=1), "valid", 0),
        ("A1", "HEART_RATE", 60.0, t + pd.Timedelta(minutes=2), "valid", 1),
        ("A1", "HEART_RATE", 0.0, t + pd.Timedelta(minutes=1), "invalid", 2),
        ("A1", "HEART_RATE", None, t + pd.Timedelta(minutes=3), "missing", 3),
        ("A1", "HEART_RATE", 59.0, t, "valid", 4),
        ("A1", "HEART_RATE", 59.0, t, "duplicate", 5),
        ("A1", "HEART_RATE", 71.0, t + pd.Timedelta(minutes=9), "suspect", 6),
    ]
    return pd.DataFrame(rows, columns=["astronaut_code", "metric_code", "value", "measured_at",
                                       "quality_status", "row_id"])


def test_split_keeps_only_valid_rows_in_usable():
    usable, excluded = split_usable(frame())
    assert set(usable["quality_status"]) == {"valid"} and len(usable) == 3
    assert set(excluded["quality_status"]) == {"invalid", "missing", "duplicate", "suspect"} and len(excluded) == 4
    assert len(usable) + len(excluded) == 7                # nothing is lost


def test_usable_is_sorted_by_astronaut_metric_time_and_reindexed():
    usable, _ = split_usable(frame())
    assert list(usable["row_id"]) == [4, 1, 0]             # A1 00:00, A1 00:02, A2 00:01
    assert list(usable.index) == [0, 1, 2]


def test_excluded_keeps_original_order():
    _, excluded = split_usable(frame())
    assert list(excluded["row_id"]) == [2, 3, 5, 6]


def test_split_does_not_modify_input_and_creates_row_id_when_absent():
    df = frame().drop(columns="row_id")
    before = df.copy()
    usable, excluded = split_usable(df)
    pd.testing.assert_frame_equal(df, before)
    assert "row_id" in usable.columns


def test_split_requires_validated_frame():
    try:
        split_usable(frame().drop(columns="quality_status"))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_mission_day_boundaries():
    df = pd.DataFrame({"measured_at": pd.to_datetime(
        ["2026-11-01T00:00:00Z", "2026-11-01T23:59:59Z", "2026-11-02T00:00:00Z", "2026-11-14T12:00:00Z"], utc=True)})
    out = add_mission_day(df)
    assert list(out["mission_day"]) == [1, 1, 2, 14]
    assert "mission_day" not in df.columns                 # input untouched


def test_mission_day_custom_start_naive_or_aware():
    df = pd.DataFrame({"measured_at": pd.to_datetime(["2026-11-03T05:00:00Z"], utc=True)})
    assert list(add_mission_day(df, "2026-11-01")["mission_day"]) == [3]
    assert list(add_mission_day(df, pd.Timestamp("2026-11-02T13:00:00Z"))["mission_day"]) == [2]   # floors to the day

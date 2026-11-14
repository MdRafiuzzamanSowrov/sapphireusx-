"""Integration test: the validator against Task 1's planted answer key (SIMULATED data).

This checks that the CODE finds the data-quality cases that were planted. It says nothing
about accuracy on real sensor data.
"""
from functools import lru_cache
from pathlib import Path

import pandas as pd

from ai.loader import load_planted_events, load_task1_vitals
from ai.validator import validate

TASK1 = Path(__file__).resolve().parents[2] / "data" / "task1"

# event -> (expected reason code, expected number of flagged rows)
EXPECTED = {
    "E11": ("impossible_value", 3),   # HR reads 0
    "E12": ("flatline", 90),          # HR stuck at 71 for 90 min
    "E13": ("device_missing", 200),   # 2 h sensor gap across 5 metrics
    "E14": ("impossible_value", 1),   # respiratory rate -1
    "E15": ("impossible_value", 1),   # SpO2 127
    "E16": ("duplicate", 10),         # 10 duplicated HR rows
    "E17": ("device_invalid", 6),     # device-flagged bad SpO2
    "E18": ("out_of_scale", 1),       # stress score 9 on 1-5 scale
}


@lru_cache(maxsize=1)
def _data():
    v = validate(load_task1_vitals(TASK1 / "simulated_vitals_long.zip"))
    ev = load_planted_events(TASK1 / "planted_events.csv")
    return v, ev


def _in_event(v, e):
    return ((v["astronaut_code"] == e.participant_id) & v["metric_code"].isin(e.metric_codes)
            & (v["measured_at"] >= e.start) & (v["measured_at"] < e.end))


def test_every_planted_data_quality_case_is_found():
    v, ev = _data()
    for event_id, (reason, count) in EXPECTED.items():
        e = ev[ev.event_id == event_id].iloc[0]
        rows = v[_in_event(v, e)]
        hits = rows[rows["dq_reasons"].str.contains(reason)]
        assert len(hits) == count, f"{event_id}: expected {count} rows with {reason}, got {len(hits)}"


def test_no_unexplained_flags_outside_planted_cases():
    v, ev = _data()
    dq = ev[ev.category == "data_quality"]
    explained = pd.Series(False, index=v.index)
    for e in dq.itertuples():
        explained |= _in_event(v, e)
    unexplained = v[(v["dq_reasons"] != "") & ~explained]
    assert len(unexplained) == 0, unexplained[["astronaut_code", "metric_code", "measured_at", "dq_reasons"]].head()


def test_exercise_recovery_and_sleep_readings_are_not_flagged():
    v, ev = _data()
    dq = ev[ev.category == "data_quality"]
    in_case = pd.Series(False, index=v.index)
    for e in dq.itertuples():
        in_case |= _in_event(v, e)
    normal = v[v["context"].isin(["exercise", "recovery", "asleep"]) & ~in_case]
    assert len(normal) > 30000
    assert (normal["quality_status"] == "valid").all()


def test_device_invalid_rows_are_not_health_data():
    v, _ = _data()
    bad = v[v["quality_status"] != "valid"]
    # whatever is not 'valid' must never be usable by baselines/detectors
    assert (bad["quality_status"].isin(["missing", "invalid", "suspect", "duplicate"])).all()
    assert set(v["quality_status"]) == {"valid", "missing", "invalid", "suspect", "duplicate"}


def test_status_counts_match_the_answer_key_totals():
    v, _ = _data()
    counts = v["quality_status"].value_counts().to_dict()
    assert counts == {"valid": 134946, "missing": 200, "suspect": 90, "invalid": 12, "duplicate": 10}

"""Integration tests on the Task 1 SIMULATED data: validator -> preprocess -> baseline."""
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from ai.baseline import attach_baselines, baseline_coverage
from ai.config import load_config
from ai.loader import load_planted_events, load_task1_vitals
from ai.preprocess import add_mission_day, split_usable
from ai.validator import validate

TASK1 = Path(__file__).resolve().parents[2] / "data" / "task1"
DISABLED = {"BODY_MASS", "RADIATION_DOSE_CUMULATIVE", "SYMPTOM_BACK_PAIN",
            "SYMPTOM_HEADACHE", "SYMPTOM_NAUSEA", "SYMPTOM_VISION_CHANGE"}


@lru_cache(maxsize=1)
def _data():
    v = validate(load_task1_vitals(TASK1 / "simulated_vitals_long.zip"))
    usable, excluded = split_usable(v)
    return attach_baselines(add_mission_day(usable)), usable, excluded


def test_usable_and_excluded_counts():
    b, usable, excluded = _data()
    assert len(usable) == 134946 and len(excluded) == 312 and len(b) == len(usable)
    assert (b["quality_status"] == "valid").all()


def test_disabled_metrics_are_not_configured_and_nothing_else_is():
    b, _, _ = _data()
    nc = b["baseline_status"] == "not_configured"
    assert set(b.loc[nc, "metric_code"]) == DISABLED
    assert not b.loc[~nc, "metric_code"].isin(DISABLED).any()


def test_invariants_of_ready_baselines():
    b, _, _ = _data()
    ok = b[b["baseline_status"] == "ok"]
    assert len(ok) > 100000
    assert ok["baseline_median"].notna().all() and ok["baseline_scale"].gt(0).all()
    assert ok["baseline_span_hours"].ge(24).all()
    assert (ok["baseline_as_of"] <= ok["measured_at"]).all()                 # never later than the reading
    assert (ok["baseline_as_of"] > ok["measured_at"] - pd.Timedelta(hours=1)).all()
    assert ok["baseline_n"].ge(3).all()
    not_ok = b[b["baseline_status"] != "ok"]
    assert not_ok["baseline_median"].isna().all()


def test_no_baseline_during_the_first_24_hours():
    b, _, _ = _data()
    first_day = b[b["measured_at"] < b["measured_at"].min() + pd.Timedelta(hours=24)]
    assert len(first_day) > 5000
    assert (first_day["baseline_status"] != "ok").all()


def test_baselines_match_an_independent_brute_force_calculation():
    b, usable, _ = _data()
    cfg = load_config()
    enabled = b[b["baseline_status"] != "not_configured"]
    sample = enabled.sample(300, random_state=7)
    keys = ["astronaut_code", "metric_code", "context"]
    groups = {k: g for k, g in usable.groupby(keys)}
    n_checked_ok = 0
    for r in sample.itertuples():
        g = groups[(r.astronaut_code, r.metric_code, r.context)]
        as_of = r.measured_at.floor("h")
        w = g[(g["measured_at"] >= as_of - pd.Timedelta(days=7)) & (g["measured_at"] < as_of)]
        assert r.baseline_n == len(w), (r.astronaut_code, r.metric_code, r.measured_at)
        if r.baseline_status == "ok":
            n_checked_ok += 1
            med = w["value"].median()
            assert abs(r.baseline_median - med) < 1e-9
            assert abs(r.baseline_mad - (w["value"] - med).abs().median()) < 1e-9
            floor = cfg["metrics"][r.metric_code]["baseline"].get("min_scale", 0)
            assert abs(r.baseline_scale - max(1.4826 * r.baseline_mad, floor)) < 1e-9
    assert n_checked_ok > 150


def test_planted_health_events_with_continuous_metrics_have_baselines():
    b, _, _ = _data()
    ev = load_planted_events(TASK1 / "planted_events.csv")
    for event_id in ["E02", "E03", "E06", "E08"]:
        e = ev[ev.event_id == event_id].iloc[0]
        rows = b[(b["astronaut_code"] == e.participant_id) & b["metric_code"].isin(e.metric_codes)
                 & (b["measured_at"] >= e.start) & (b["measured_at"] < e.end)
                 & ~b["metric_code"].isin(DISABLED)]
        assert len(rows) > 0 and (rows["baseline_status"] == "ok").all(), event_id


def test_exercise_baseline_is_higher_than_awake_for_heart_rate():
    b, _, _ = _data()
    last = b[(b["metric_code"] == "HEART_RATE") & (b["mission_day"] == 14) & (b["baseline_status"] == "ok")]
    med = last.groupby(["astronaut_code", "context"])["baseline_median"].median().unstack()
    assert (med["exercise"] > med["awake"] + 30).all()
    assert (med["asleep"] < med["awake"]).all()


def test_coverage_report_shape_and_known_gap():
    b, _, _ = _data()
    cov = baseline_coverage(b)
    assert {"metric_code", "context", "readings", "with_baseline", "share_with_baseline"} <= set(cov.columns)
    temp_rec = cov[(cov.metric_code == "BODY_TEMPERATURE") & (cov.context == "recovery")].iloc[0]
    assert temp_rec["with_baseline"] == 0                                    # too few readings: documented limitation
    hr_awake = cov[(cov.metric_code == "HEART_RATE") & (cov.context == "awake")].iloc[0]
    assert hr_awake["share_with_baseline"] > 0.9

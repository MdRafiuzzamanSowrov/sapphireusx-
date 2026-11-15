"""Unit tests for ai.validator on small hand-made frames, plus config checks."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from ai.config import ConfigError, load_config
from ai.validator import quality_episodes, summarize, validate

T0 = pd.Timestamp("2026-11-01T00:00:00Z")
UNITS = {"HEART_RATE": "bpm", "BLOOD_OXYGEN_SPO2": "%", "RESPIRATORY_RATE": "breaths/min",
         "STRESS_SCORE": "score_1_to_5", "SYMPTOM_HEADACHE": "yes_no", "SLEEP_DURATION": "hours",
         "RADIATION_DOSE_CUMULATIVE": "mSv"}


def mk(rows):
    """rows: (astronaut, metric, value, minute_offset[, device_status[, unit]])"""
    recs = []
    for r in rows:
        a, m, v, off = r[:4]
        status = r[4] if len(r) > 4 else "valid"
        unit = r[5] if len(r) > 5 else UNITS.get(m, "x")
        recs.append({"astronaut_code": a, "metric_code": m, "value": v, "unit": unit,
                     "measured_at": T0 + pd.Timedelta(minutes=off), "context": "awake",
                     "device_quality_status": status})
    df = pd.DataFrame(recs)
    df["row_id"] = np.arange(len(df))
    return df


def one(metric, value, status="valid", unit=None):
    row = ("A1", metric, value, 0, status) if unit is None else ("A1", metric, value, 0, status, unit)
    return validate(mk([row])).iloc[0]


# ------------------------------------------------------------- single-row rules
def test_normal_rows_are_valid():
    for metric, value in [("HEART_RATE", 62), ("BLOOD_OXYGEN_SPO2", 97), ("STRESS_SCORE", 3), ("SYMPTOM_HEADACHE", 1)]:
        r = one(metric, value)
        assert r["quality_status"] == "valid" and r["dq_reasons"] == "", (metric, value)


def test_boundary_values_are_valid():
    assert one("BLOOD_OXYGEN_SPO2", 100)["quality_status"] == "valid"
    assert one("SLEEP_DURATION", 0)["quality_status"] == "valid"
    assert one("HEART_RATE", 0.1)["quality_status"] == "valid"
    assert one("STRESS_SCORE", 1)["quality_status"] == "valid"
    assert one("STRESS_SCORE", 5)["quality_status"] == "valid"


def test_impossible_values_are_invalid():
    for metric, value in [("HEART_RATE", 0), ("HEART_RATE", -5), ("BLOOD_OXYGEN_SPO2", 127),
                          ("BLOOD_OXYGEN_SPO2", -1), ("RESPIRATORY_RATE", -1)]:
        r = one(metric, value)
        assert r["quality_status"] == "invalid" and r["dq_reasons"] == "impossible_value", (metric, value)


def test_device_marked_valid_does_not_override_impossible_values():
    rows = [one("HEART_RATE", 0), one("BLOOD_OXYGEN_SPO2", 127), one("STRESS_SCORE", 9)]
    assert [r["device_quality_status"] for r in rows] == ["valid"] * 3
    assert [r["quality_status"] for r in rows] == ["invalid"] * 3
    assert [r["dq_reasons"] for r in rows] == ["impossible_value", "impossible_value", "out_of_scale"]


def test_out_of_scale_values_are_invalid():
    for metric, value in [("STRESS_SCORE", 9), ("STRESS_SCORE", 2.5), ("STRESS_SCORE", 0), ("SYMPTOM_HEADACHE", 2)]:
        r = one(metric, value)
        assert r["quality_status"] == "invalid" and r["dq_reasons"] == "out_of_scale", (metric, value)


def test_device_missing_invalid_and_empty_value():
    r = one("HEART_RATE", np.nan, "missing")
    assert r["quality_status"] == "missing" and r["dq_reasons"] == "device_missing"
    r = one("BLOOD_OXYGEN_SPO2", 84, "invalid")        # plausible-looking value, device says bad
    assert r["quality_status"] == "invalid" and r["dq_reasons"] == "device_invalid"
    r = one("HEART_RATE", np.nan, "valid")             # device says valid but there is no number
    assert r["quality_status"] == "missing" and r["dq_reasons"] == "empty_value"


def test_device_invalid_plausible_value_is_excluded_from_usable_rows():
    v = validate(mk([("A1", "BLOOD_OXYGEN_SPO2", 84, 0, "invalid"),
                     ("A1", "BLOOD_OXYGEN_SPO2", 98, 1, "valid")]))
    assert list(v["quality_status"]) == ["invalid", "valid"]
    assert v.loc[0, "dq_reasons"] == "device_invalid"


def test_unit_mismatch_and_unknown_metric():
    r = one("HEART_RATE", 62, unit="bpm_per_hour")
    assert r["quality_status"] == "invalid" and "unit_mismatch" in r["dq_reasons"]
    r = one("MADE_UP_METRIC", 5)
    assert r["quality_status"] == "invalid" and "unknown_metric" in r["dq_reasons"]


# ------------------------------------------------------------- duplicates
def test_duplicate_first_kept_later_flagged():
    v = validate(mk([("A1", "HEART_RATE", 60, 0), ("A1", "HEART_RATE", 60, 0), ("A1", "HEART_RATE", 61, 1)]))
    assert list(v["quality_status"]) == ["valid", "duplicate", "valid"]
    assert v.loc[1, "dq_reasons"] == "duplicate"


def test_duplicate_with_different_value_is_conflict():
    v = validate(mk([("A1", "HEART_RATE", 60, 0), ("A1", "HEART_RATE", 75, 0)]))
    assert list(v["quality_status"]) == ["valid", "duplicate"]
    assert v.loc[1, "dq_reasons"] == "duplicate_conflict"


# ------------------------------------------------------------- flat-line
def hr_run(astronaut, n, value=71, start=0):
    return [(astronaut, "HEART_RATE", value, start + i) for i in range(n)]


def test_flatline_threshold():
    assert set(validate(mk(hr_run("A1", 29)))["quality_status"]) == {"valid"}
    v = validate(mk(hr_run("A1", 30)))
    assert set(v["quality_status"]) == {"suspect"} and set(v["dq_reasons"]) == {"flatline"}


def test_flatline_broken_by_a_change():
    rows = hr_run("A1", 20) + [("A1", "HEART_RATE", 72, 20)] + hr_run("A1", 20, start=21)
    assert set(validate(mk(rows))["quality_status"]) == {"valid"}


def test_flatline_not_inflated_by_duplicates():
    rows = hr_run("A1", 25) + hr_run("A1", 10)            # 10 exact duplicate rows
    v = validate(mk(rows))
    assert (v["quality_status"] == "duplicate").sum() == 10
    assert (v["quality_status"] == "suspect").sum() == 0   # 25 distinct readings < 30


def test_flatline_runs_do_not_cross_astronauts():
    rows = hr_run("A1", 20) + hr_run("A2", 20)
    assert set(validate(mk(rows))["quality_status"]) == {"valid"}


def test_flatline_only_applies_to_configured_metrics():
    rows = [("A1", "BLOOD_OXYGEN_SPO2", 98, i) for i in range(40)]
    assert set(validate(mk(rows))["quality_status"]) == {"valid"}


# ------------------------------------------------------------- monotonic
def test_running_total_must_not_decrease():
    v = validate(mk([("A1", "RADIATION_DOSE_CUMULATIVE", 1.0, 0), ("A1", "RADIATION_DOSE_CUMULATIVE", 2.0, 60),
                     ("A1", "RADIATION_DOSE_CUMULATIVE", 1.5, 120), ("A1", "RADIATION_DOSE_CUMULATIVE", 2.5, 180)]))
    assert list(v["quality_status"]) == ["valid", "valid", "invalid", "valid"]
    assert v.loc[2, "dq_reasons"] == "non_monotonic"


# ------------------------------------------------------------- behaviour
def test_original_order_kept_and_input_not_modified():
    df = mk([("A1", "HEART_RATE", 60, 5), ("A1", "HEART_RATE", 61, 0)])
    before = df.copy()
    v = validate(df)
    assert list(v["row_id"]) == [0, 1]
    pd.testing.assert_frame_equal(df, before)
    assert "quality_status" not in df.columns


def test_missing_required_columns_raise():
    try:
        validate(pd.DataFrame({"value": [1.0]}))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_summary_and_episodes():
    rows = [("A1", "HEART_RATE", 0, 0), ("A1", "HEART_RATE", 0, 1), ("A1", "HEART_RATE", 0, 2),
            ("A1", "HEART_RATE", 62, 3), ("A1", "HEART_RATE", -1, 300)]
    v = validate(mk(rows))
    s = summarize(v)
    assert s["rows"] == 5 and s["usable_rows"] == 1 and s["by_reason"] == {"impossible_value": 4}
    ep = quality_episodes(v)
    assert list(ep["n_rows"]) == [3, 1]                      # 3-row episode, then a separate 1-row episode


# ------------------------------------------------------------- config
def test_default_config_loads_and_covers_all_19_metrics():
    cfg = load_config()
    assert len(cfg["metrics"]) == 19 and cfg["status"] == "PROVISIONAL"


def test_malformed_config_is_rejected():
    for text in ["metrics: []", "metrics:\n  heart_rate:\n    unit: bpm\n",
                 "metrics:\n  HEART_RATE:\n    unit: bpm\n    validity: {bogus: 1}\n",
                 "metrics:\n  HEART_RATE:\n    unit: bpm\n    flatline_min_run: 1\n",
                 "metrics:\n  HEART_RATE:\n    validity: {}\n"]:
        p = Path(tempfile.mkdtemp()) / "c.yaml"
        p.write_text(text, encoding="utf-8")
        try:
            load_config(p)
        except ConfigError:
            continue
        raise AssertionError(f"config accepted: {text!r}")

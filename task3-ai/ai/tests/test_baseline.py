"""Unit tests for ai.baseline on small constructed frames, plus baseline config checks."""
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

from ai.baseline import MAD_TO_SIGMA, attach_baselines
from ai.config import ConfigError, load_config
from ai.preprocess import split_usable
from ai.validator import validate

T0 = pd.Timestamp("2026-11-01T00:00:00Z")
CFG = {
    "baseline": {"lookback_days": 7, "as_of_step_minutes": 60, "min_points": 20, "min_span_hours": 24},
    "metrics": {
        "HEART_RATE": {"unit": "bpm", "baseline": {"min_scale": 1}},
        "SYMPTOM_NAUSEA": {"unit": "yes_no", "baseline": {"enabled": False}},
    },
}


def mk(times_min, values, metric="HEART_RATE", context="awake", astronaut="A1"):
    df = pd.DataFrame({
        "astronaut_code": astronaut, "metric_code": metric, "context": context,
        "value": np.asarray(values, dtype=float),
        "measured_at": [T0 + pd.Timedelta(minutes=int(m)) for m in times_min],
    })
    df["row_id"] = np.arange(len(df))
    return df


def cycle_frame(days):
    """HR every 10 min for `days` days, values cycle 60..64 (median 62, MAD 1)."""
    minutes = np.arange(0, days * 1440, 10)
    return mk(minutes, 60 + (np.arange(len(minutes)) % 5))


def at(df, day, hh, mm=0):
    """Row of attach_baselines output nearest to day (1-based) hh:mm."""
    t = T0 + pd.Timedelta(days=day - 1, hours=hh, minutes=mm)
    return df[df["measured_at"] == t].iloc[0]


# --------------------------------------------------------------- readiness
def test_first_day_has_no_baseline():
    out = attach_baselines(cycle_frame(1), CFG)
    assert set(out["baseline_status"]) == {"insufficient_history"}
    assert out["baseline_median"].isna().all()


def test_baseline_values_when_ready():
    out = attach_baselines(cycle_frame(3), CFG)
    r = at(out, 3, 12, 30)                                  # as_of 12:00, 360 earlier readings
    assert r["baseline_status"] == "ok" and r["baseline_n"] == 360
    assert r["baseline_median"] == 62.0 and r["baseline_mad"] == 1.0
    assert abs(r["baseline_scale"] - MAD_TO_SIGMA) < 1e-9
    assert r["baseline_span_hours"] == 60.0
    assert r["baseline_as_of"] == T0 + pd.Timedelta(days=2, hours=12)


def test_min_points_boundary():
    cfg = {"baseline": {"lookback_days": 7, "as_of_step_minutes": 60, "min_points": 5, "min_span_hours": 0},
           "metrics": {"HEART_RATE": {"unit": "bpm", "baseline": {"min_scale": 1}}}}
    out = attach_baselines(mk(np.arange(10) * 60, [60] * 10), cfg)    # one reading per hour
    status = list(out["baseline_status"])
    assert status[4] == "insufficient_history"              # 4 earlier readings
    assert status[5] == "ok"                                # 5 earlier readings
    assert list(out["baseline_n"])[:6] == [0, 1, 2, 3, 4, 5]


def test_min_span_requirement():
    cfg = {"baseline": {"lookback_days": 7, "as_of_step_minutes": 60, "min_points": 3, "min_span_hours": 24},
           "metrics": {"HEART_RATE": {"unit": "bpm", "baseline": {"min_scale": 1}}}}
    out = attach_baselines(mk([0, 60, 120, 180, 24 * 60 + 60], [60] * 5), cfg)   # many points, but over 3 h
    assert list(out["baseline_status"]) == ["insufficient_history"] * 4 + ["ok"]


# --------------------------------------------------------------- no peeking
def test_future_values_never_change_earlier_baselines():
    base = cycle_frame(4)
    changed = base.copy()
    changed.loc[changed["measured_at"] >= T0 + pd.Timedelta(days=1, hours=12), "value"] = 200.0
    a, b = attach_baselines(base, CFG), attach_baselines(changed, CFG)
    early = a["measured_at"] < T0 + pd.Timedelta(days=1, hours=13)      # as_of <= 12:00, data < 12:00
    assert (a.loc[early, "baseline_status"] == "ok").sum() > 50         # the check is meaningful
    for col in ["baseline_status", "baseline_median", "baseline_mad", "baseline_n"]:
        pd.testing.assert_series_equal(a.loc[early, col], b.loc[early, col])
    # ...while a much later row does see the changed data (the test can fail)
    assert at(a, 4, 12, 30)["baseline_median"] == 62.0
    assert at(b, 4, 12, 30)["baseline_median"] == 200.0


def test_a_reading_is_not_part_of_its_own_baseline():
    base = cycle_frame(3)
    changed = base.copy()
    t = T0 + pd.Timedelta(days=2, hours=12, minutes=30)
    changed.loc[changed["measured_at"] == t, "value"] = 500.0
    a, b = attach_baselines(base, CFG), attach_baselines(changed, CFG)
    for col in ["baseline_median", "baseline_mad", "baseline_scale", "baseline_n"]:
        assert at(a, 3, 12, 30)[col] == at(b, 3, 12, 30)[col]


def test_same_hour_readings_are_not_used():
    out = attach_baselines(cycle_frame(3), CFG)
    r12_00, r12_50 = at(out, 3, 12, 0), at(out, 3, 12, 50)
    assert r12_00["baseline_n"] == r12_50["baseline_n"] == 360         # both use data before 12:00 only


# --------------------------------------------------------------- statistics
def test_contexts_have_separate_baselines():
    frames = []
    for d in range(4):
        day = d * 1440
        frames.append(mk(day + 360 + np.arange(0, 480, 10), [60] * 48, context="awake"))       # 06:00-13:50
        frames.append(mk(day + 840 + np.arange(60), [120] * 60, context="exercise"))           # 14:00-14:59
    df = pd.concat(frames, ignore_index=True)
    df["row_id"] = np.arange(len(df))
    out = attach_baselines(df, CFG)
    last = out[out["measured_at"] >= T0 + pd.Timedelta(days=3)]
    ex = last[(last.context == "exercise") & (last.baseline_status == "ok")]
    aw = last[(last.context == "awake") & (last.baseline_status == "ok")]
    assert len(ex) > 0 and len(aw) > 0
    assert set(ex["baseline_median"]) == {120.0} and set(aw["baseline_median"]) == {60.0}


def test_median_resists_a_single_spike_inside_the_window():
    base = cycle_frame(3)
    spiked = base.copy()
    spiked.loc[spiked["measured_at"] == T0 + pd.Timedelta(days=1, hours=5), "value"] = 250.0
    assert at(attach_baselines(spiked, CFG), 3, 12, 30)["baseline_median"] == 62.0


def test_scale_floor_when_readings_are_constant():
    out = attach_baselines(mk(np.arange(0, 3 * 1440, 10), [60] * 432), CFG)
    r = at(out, 3, 12, 30)
    assert r["baseline_mad"] == 0.0 and r["baseline_scale"] == 1.0     # floor = min_scale


def test_lookback_excludes_old_readings():
    minutes = np.arange(0, 10 * 1440, 30)
    values = np.where(minutes < 1440, 200.0, 60.0)                      # day 1 is very different
    out = attach_baselines(mk(minutes, values), CFG)
    r = at(out, 9, 12, 30)                                              # window = day 2 12:00 .. day 9 12:00
    assert r["baseline_median"] == 60.0 and r["baseline_n"] == 7 * 48


# --------------------------------------------------------------- configuration, safety, robustness
def test_not_configured_metrics():
    n = mk(np.arange(0, 3 * 1440, 60), [0] * 72, metric="SYMPTOM_NAUSEA", context="not_applicable")
    u = mk(np.arange(0, 3 * 1440, 60), [60] * 72, metric="NOT_IN_CONFIG")
    out = attach_baselines(pd.concat([n, u], ignore_index=True), CFG)
    assert set(out["baseline_status"]) == {"not_configured"}
    assert out["baseline_median"].isna().all() and (out["baseline_n"] == 0).all()
    assert out["baseline_as_of"].isna().all()


def test_invalid_and_missing_rows_never_enter_a_baseline():
    df = cycle_frame(3)
    df["unit"] = "bpm"
    df["device_quality_status"] = "valid"
    bad = df["measured_at"].isin([T0 + pd.Timedelta(days=1, hours=h) for h in (3, 4, 5, 6, 7)])
    df.loc[bad, "value"] = 0.0                                          # impossible heart rate
    usable, excluded = split_usable(validate(df))
    assert len(excluded) == int(bad.sum()) and (usable["value"] > 0).all()
    out = attach_baselines(usable)                                      # default config
    r = out[out["measured_at"] == T0 + pd.Timedelta(days=2, hours=12, minutes=30)].iloc[0]
    window = usable[(usable.measured_at >= r["baseline_as_of"] - pd.Timedelta(days=7))
                    & (usable.measured_at < r["baseline_as_of"])]
    assert len(window) == 360 - 5                                       # the 5 zero readings are not counted
    assert r["baseline_n"] == len(window)
    assert r["baseline_median"] == 62.0


def test_row_order_and_time_zone_do_not_change_results():
    df = cycle_frame(3)
    ref = attach_baselines(df, CFG).set_index("row_id")
    shuffled = df.sample(frac=1.0, random_state=1)
    s = attach_baselines(shuffled, CFG).set_index("row_id").loc[ref.index]
    pd.testing.assert_series_equal(ref["baseline_median"], s["baseline_median"])
    pd.testing.assert_series_equal(ref["baseline_n"], s["baseline_n"])
    tz = df.copy()
    tz["measured_at"] = tz["measured_at"].dt.tz_convert("Europe/Paris")
    z = attach_baselines(tz, CFG).set_index("row_id").loc[ref.index]
    pd.testing.assert_series_equal(ref["baseline_status"], z["baseline_status"])
    pd.testing.assert_series_equal(ref["baseline_median"], z["baseline_median"])


def test_input_not_modified_and_columns_added():
    df = cycle_frame(2)
    before = df.copy()
    out = attach_baselines(df, CFG)
    pd.testing.assert_frame_equal(df, before)
    for col in ["baseline_status", "baseline_median", "baseline_mad", "baseline_scale",
                "baseline_n", "baseline_span_hours", "baseline_as_of"]:
        assert col in out.columns


def test_missing_columns_raise():
    try:
        attach_baselines(pd.DataFrame({"value": [1.0]}), CFG)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# --------------------------------------------------------------- config validation
def test_default_config_has_baseline_settings():
    cfg = load_config()
    assert cfg["baseline"]["lookback_days"] == 7 and cfg["baseline"]["min_span_hours"] == 24
    disabled = [m for m, c in cfg["metrics"].items() if (c.get("baseline") or {}).get("enabled") is False]
    assert sorted(disabled) == ["BODY_MASS", "RADIATION_DOSE_CUMULATIVE", "SYMPTOM_BACK_PAIN",
                                "SYMPTOM_HEADACHE", "SYMPTOM_NAUSEA", "SYMPTOM_VISION_CHANGE"]


def test_bad_baseline_config_is_rejected():
    head = "metrics:\n  HEART_RATE:\n    unit: bpm\n"
    bad = [
        "baseline: {min_points: 2}\n" + head,
        "baseline: {lookback_days: 0}\n" + head,
        "baseline: {bogus: 1}\n" + head,
        "baseline: {as_of_step_minutes: 7}\n" + head,
        "baseline: [1, 2]\n" + head,
        head + "    baseline: {enabled: 'yes'}\n",
        head + "    baseline: {min_scale: -1}\n",
        head + "    baseline: {min_points: 1}\n",
        head + "    baseline: {unknown: 1}\n",
    ]
    for text in bad:
        p = Path(tempfile.mkdtemp()) / "c.yaml"
        p.write_text(text, encoding="utf-8")
        try:
            load_config(p)
        except ConfigError:
            continue
        raise AssertionError(f"config accepted: {text!r}")

"""Tests for ai.schema and ai.loader (plain asserts, run with pytest)."""
import json
import tempfile
from pathlib import Path

import pandas as pd

from ai.loader import load_planted_events, load_task1_vitals
from ai.schema import (SchemaError, dataframe_to_records, validate_measurement_record)

ROOT = Path(__file__).resolve().parents[2]
TASK1 = ROOT / "data" / "task1"

HEADER = ("participant_id,timestamp,indicator,value,unit,context,quality_status,"
          "data_origin,collection_method,source_note\n")
ROW = "DEMO-01,2026-11-01T00:00:00Z,heart_rate,62,bpm,awake,valid,SIMULATED,sensor,sim\n"


def _write(text: str) -> Path:
    d = Path(tempfile.mkdtemp())
    p = d / "x.csv"
    p.write_text(text, encoding="utf-8")
    return p


def _raises_schema_error(fn) -> bool:
    try:
        fn()
    except SchemaError:
        return True
    return False


def good_record(**over):
    rec = {"astronaut_code": "AST-001", "metric_code": "HEART_RATE", "value": 75.0, "unit": "bpm",
           "measured_at": "2026-11-14T10:00:00Z", "source_type": "synthetic", "quality_status": "valid"}
    rec.update(over)
    return rec


# ---------------------------------------------------------------- loader
def test_loader_maps_fields():
    df = load_task1_vitals(_write(HEADER + ROW))
    r = df.iloc[0]
    assert r["astronaut_code"] == "DEMO-01"
    assert r["metric_code"] == "HEART_RATE"
    assert r["source_type"] == "synthetic"
    assert r["device_quality_status"] == "valid"
    assert str(r["measured_at"].tz) == "UTC"
    assert r["row_id"] == 0


def test_loader_rejects_old_file_without_context_column():
    old = "participant_id,timestamp,indicator,value,unit,data_origin,collection_method,source_note\n"
    assert _raises_schema_error(lambda: load_task1_vitals(_write(old + "DEMO-01,2026-11-01T00:00:00Z,heart_rate,62,bpm,SIMULATED,sensor,s\n")))


def test_loader_rejects_unknown_origin_status_context_and_bad_time():
    bad_origin = ROW.replace("SIMULATED", "MYSTERY")
    bad_status = ROW.replace(",valid,", ",ok,")
    bad_context = ROW.replace(",awake,", ",dancing,")
    bad_time = ROW.replace("2026-11-01T00:00:00Z", "yesterday")
    for body in (bad_origin, bad_status, bad_context, bad_time):
        assert _raises_schema_error(lambda b=body: load_task1_vitals(_write(HEADER + b))), body


def test_loader_rejects_non_numeric_value_but_accepts_empty():
    assert _raises_schema_error(lambda: load_task1_vitals(_write(HEADER + ROW.replace(",62,", ",abc,"))))
    df = load_task1_vitals(_write(HEADER + ROW.replace(",62,", ",,").replace(",valid,", ",missing,")))
    assert pd.isna(df.iloc[0]["value"])


def test_loader_missing_file():
    try:
        load_task1_vitals(Path("does_not_exist.csv"))
    except FileNotFoundError:
        return
    raise AssertionError("expected FileNotFoundError")


def test_real_file_shape_and_labels():
    df = load_task1_vitals(TASK1 / "simulated_vitals_long.zip")
    assert len(df) == 135258
    assert sorted(df["astronaut_code"].unique()) == ["DEMO-01", "DEMO-02", "DEMO-03", "DEMO-04"]
    assert set(df["source_type"]) == {"synthetic"}           # nothing is labelled real
    assert df["metric_code"].nunique() == 19
    assert df["measured_at"].min() >= pd.Timestamp("2026-11-01", tz="UTC")


def test_planted_events_loader():
    ev = load_planted_events(TASK1 / "planted_events.csv")
    assert len(ev) == 20
    assert ev.loc[ev.event_id == "E02", "metric_codes"].iloc[0] == ["HEART_RATE", "HEART_RATE_VARIABILITY"]


# ---------------------------------------------------------------- schema
def test_valid_record_has_no_errors():
    assert validate_measurement_record(good_record()) == []
    assert validate_measurement_record(good_record(value=None, quality_status="missing")) == []
    assert validate_measurement_record(good_record(context="awake")) == []


def test_invalid_records_are_rejected():
    bad = [
        good_record(source_type="made_up"),
        good_record(quality_status="ok"),
        good_record(measured_at="2026-11-14 10:00:00"),
        good_record(measured_at="2026-13-45T10:00:00Z"),
        good_record(metric_code="heart rate"),
        good_record(value="75"),
        good_record(value=float("nan")),
        good_record(value=True),
        good_record(value=None, quality_status="valid"),   # null value but claims a reading
        good_record(context="dancing"),
        good_record(extra_field=1),
    ]
    for rec in bad:
        assert validate_measurement_record(rec) != [], rec
    rec = good_record()
    del rec["unit"]
    assert validate_measurement_record(rec) != []
    assert validate_measurement_record("not a dict") != []


def test_dataframe_to_records_is_json_safe_and_valid():
    df = load_task1_vitals(_write(HEADER + ROW + ROW.replace("00:00:00Z", "00:01:00Z").replace(",62,", ",,").replace(",valid,", ",missing,")))
    df["quality_status"] = df["device_quality_status"]
    recs = dataframe_to_records(df)
    json.dumps(recs)                                          # must not raise (no NaN objects)
    assert recs[1]["value"] is None
    assert recs[0]["measured_at"] == "2026-11-01T00:00:00Z"
    for rec in recs:
        assert validate_measurement_record(rec) == [], rec

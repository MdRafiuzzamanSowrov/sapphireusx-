"""Orchestration for the vital-sign monitoring pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ai.detectors import detect
from ai.baseline import BASELINE_COLUMNS, attach_baselines
from ai.loader import load_metric_table, load_reference_ranges, load_task1_vitals
from ai.preprocess import split_usable
from ai.schema import dataframe_to_records, validate_analysis_payload
from ai.validator import validate


def analyze_vitals(measurements, reference_ranges=None):
    """Run quality checks and reference-band screening on a measurement table or Task 1 file."""
    if isinstance(measurements, (str, Path)):
        frame = load_task1_vitals(measurements)
    else:
        frame = measurements.copy()
    quality = validate(frame)
    usable, excluded = split_usable(quality)
    baselined = attach_baselines(usable)
    baseline_by_id = baselined.set_index("row_id") if "row_id" in baselined else None
    if baseline_by_id is not None:
        for column in BASELINE_COLUMNS:
            quality[column] = quality["row_id"].map(baseline_by_id[column])
    ranges = reference_ranges
    if ranges is None:
        ranges = load_reference_ranges(Path(__file__).resolve().parents[1] / "data/task1/reference_ranges.csv")
    metric_rules = load_metric_table(Path(__file__).resolve().parents[1] / "data/task1/metric_table.csv")
    screened = detect(quality, ranges, metric_rules=metric_rules)
    return {"measurements": screened, "usable": baselined, "excluded": excluded}


def analysis_to_payload(result):
    """Serialize a proposed backend-neutral JSON payload, including review alerts.

    The consuming backend has not approved this envelope; agree its shape before integration.
    """
    measurements = result["measurements"]
    records = dataframe_to_records(measurements)
    for rec, row in zip(records, measurements.itertuples(index=False)):
        rec["dq_reasons"] = str(row.dq_reasons)
        rec["data_label"] = str(row.data_label)
        for column in BASELINE_COLUMNS:
            value = getattr(row, column)
            if pd.isna(value):
                rec[column] = None
            elif column == "baseline_as_of":
                rec[column] = value.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                rec[column] = value.item() if hasattr(value, "item") else value
    alerts = []
    selected = measurements[measurements["alert_priority"].notna()]
    for row in selected.itertuples(index=False):
        alerts.append({
            "astronaut_code": str(row.astronaut_code),
            "metric_code": str(row.metric_code),
            "measured_at": row.measured_at.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "value": float(row.value),
            "unit": str(row.unit),
            "context": str(row.context),
            "priority": str(row.alert_priority),
            "findings": row.detector_findings,
            "data_label": str(row.data_label),
            "baseline_status": str(row.baseline_status) if pd.notna(row.baseline_status) else None,
            "baseline_median": float(row.baseline_median) if pd.notna(row.baseline_median) else None,
            "baseline_mad": float(row.baseline_mad) if pd.notna(row.baseline_mad) else None,
            "baseline_scale": float(row.baseline_scale) if pd.notna(row.baseline_scale) else None,
            "baseline_n": int(row.baseline_n) if pd.notna(row.baseline_n) else None,
            "baseline_span_hours": float(row.baseline_span_hours) if pd.notna(row.baseline_span_hours) else None,
            "baseline_as_of": (row.baseline_as_of.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")
                               if pd.notna(row.baseline_as_of) else None),
        })
    payload = {"schema_version": "1.0", "measurements": records, "alerts": alerts}
    payload = json.loads(json.dumps(payload, allow_nan=False))
    validate_analysis_payload(payload)
    return payload

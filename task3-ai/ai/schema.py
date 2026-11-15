"""Shared data contract: field names, allowed values and record validation.

Pure Python (no third-party dependency) so the backend developer can reuse it.
The contract is PRELIMINARY: agree changes with the backend developer.
"""
from __future__ import annotations

import math
import re
from datetime import datetime

import pandas as pd


class SchemaError(ValueError):
    """Raised when an input file or record does not follow the expected structure."""


# ---- Task 1 file (long format, version 3) ---------------------------------
TASK1_REQUIRED_COLUMNS = [
    "participant_id", "timestamp", "indicator", "value", "unit", "context",
    "quality_status", "data_origin", "collection_method", "source_note",
]

# Project labels -> contract source_type
ORIGIN_TO_SOURCE_TYPE = {
    "SIMULATED": "synthetic",
    "USER-ENTERED": "user_entered",
    "REAL NASA RESEARCH DATA": "real_nasa",
}

# ---- Contract vocabularies --------------------------------------------------
SOURCE_TYPES = ("real_nasa", "synthetic", "user_entered")
DEVICE_QUALITY_STATUSES = ("valid", "missing", "invalid")        # what a device reports
# Statuses the AI module can assign. "suspect" and "duplicate" are PROPOSED additions
# to confirm with the backend developer; "censored"/"estimated" are reserved
# (OSD-575 ceiling values, crew estimates) and not produced yet.
QUALITY_STATUSES = ("valid", "missing", "invalid", "suspect", "duplicate", "censored", "estimated")
CONTEXTS = ("awake", "asleep", "exercise", "recovery", "not_applicable")

_METRIC_RE = re.compile(r"^[A-Z0-9_]+$")
_TIME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

MEASUREMENT_REQUIRED = ["astronaut_code", "metric_code", "value", "unit",
                        "measured_at", "source_type", "quality_status"]

# JSON Schema (draft-07) of one measurement, for the backend / jsonschema.
MEASUREMENT_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Measurement (preliminary)",
    "type": "object",
    "required": MEASUREMENT_REQUIRED,
    "additionalProperties": False,
    "properties": {
        "astronaut_code": {"type": "string", "minLength": 1},
        "metric_code": {"type": "string", "pattern": "^[A-Z0-9_]+$"},
        "value": {"type": ["number", "null"]},
        "unit": {"type": "string", "minLength": 1},
        "measured_at": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$"},
        "source_type": {"enum": list(SOURCE_TYPES)},
        "quality_status": {"enum": list(QUALITY_STATUSES)},
        "context": {"enum": list(CONTEXTS)},
    },
}

_PROVENANCE_LABELS = ["SIMULATED DATA", "REAL NASA RESEARCH DATA", "USER-ENTERED DATA"]
_BASELINE_JSON_PROPERTIES = {
    "baseline_status": {"type": ["string", "null"], "enum": ["ok", "insufficient_history", "not_configured", None]},
    "baseline_median": {"type": ["number", "null"]},
    "baseline_mad": {"type": ["number", "null"]},
    "baseline_scale": {"type": ["number", "null"]},
    "baseline_n": {"type": ["integer", "null"], "minimum": 0},
    "baseline_span_hours": {"type": ["number", "null"], "minimum": 0},
    "baseline_as_of": {"type": ["string", "null"]},
}
_ANALYSIS_MEASUREMENT_PROPERTIES = {
    **MEASUREMENT_JSON_SCHEMA["properties"],
    "dq_reasons": {"type": "string"},
    "data_label": {"enum": _PROVENANCE_LABELS},
    **_BASELINE_JSON_PROPERTIES,
}

# Proposed analysis envelope for local/backend review; the consuming backend has not approved it.
ANALYSIS_RESULT_JSON_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "Astronaut health analysis result (proposed)",
    "type": "object",
    "required": ["schema_version", "measurements", "alerts"],
    "additionalProperties": False,
    "properties": {
        "schema_version": {"const": "1.0"},
        "measurements": {
            "type": "array",
            "items": {"type": "object", "required": list(_ANALYSIS_MEASUREMENT_PROPERTIES),
                      "additionalProperties": False, "properties": _ANALYSIS_MEASUREMENT_PROPERTIES},
        },
        "alerts": {
            "type": "array",
            "items": {
                "type": "object", "additionalProperties": False,
                "required": ["astronaut_code", "metric_code", "measured_at", "value", "unit", "context",
                             "priority", "findings", "data_label", "baseline_status", "baseline_median",
                             "baseline_mad", "baseline_scale", "baseline_n", "baseline_span_hours", "baseline_as_of"],
                "properties": {
                    "astronaut_code": {"type": "string", "minLength": 1},
                    "metric_code": {"type": "string", "pattern": "^[A-Z0-9_]+$"},
                    "measured_at": {"type": "string", "format": "date-time"},
                    "value": {"type": "number"}, "unit": {"type": "string"},
                    "context": {"enum": list(CONTEXTS)}, "priority": {"enum": ["LOW", "MEDIUM", "HIGH"]},
                    "findings": {"type": "array", "items": {"type": "object"}},
                    "data_label": {"enum": _PROVENANCE_LABELS},
                    **_BASELINE_JSON_PROPERTIES,
                },
            },
        },
    },
}


def validate_analysis_payload(payload: dict) -> None:
    """Raise jsonschema.ValidationError if a proposed analysis envelope is malformed."""
    try:
        import jsonschema
    except ImportError as exc:  # pragma: no cover - declared project dependency
        raise RuntimeError("jsonschema is required to validate analysis payloads") from exc
    jsonschema.validate(payload, ANALYSIS_RESULT_JSON_SCHEMA)


def validate_measurement_record(rec: dict) -> list[str]:
    """Return a list of problems with one measurement dict (empty list = OK)."""
    errors: list[str] = []
    if not isinstance(rec, dict):
        return ["record is not an object"]
    for key in MEASUREMENT_REQUIRED:
        if key not in rec:
            errors.append(f"missing field: {key}")
    extra = set(rec) - set(MEASUREMENT_JSON_SCHEMA["properties"])
    for key in sorted(extra):
        errors.append(f"unexpected field: {key}")
    if errors:
        return errors

    if not isinstance(rec["astronaut_code"], str) or not rec["astronaut_code"]:
        errors.append("astronaut_code must be a non-empty string")
    if not isinstance(rec["metric_code"], str) or not _METRIC_RE.match(rec["metric_code"]):
        errors.append("metric_code must be UPPER_CASE letters, digits or underscore")
    if not isinstance(rec["unit"], str) or not rec["unit"]:
        errors.append("unit must be a non-empty string")

    value = rec["value"]
    if value is not None:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            errors.append("value must be a finite number or null")

    ts = rec["measured_at"]
    if not isinstance(ts, str) or not _TIME_RE.match(ts):
        errors.append("measured_at must look like 2026-11-14T10:00:00Z (UTC)")
    else:
        try:
            datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError:
            errors.append("measured_at is not a real date/time")

    if rec["source_type"] not in SOURCE_TYPES:
        errors.append(f"source_type must be one of {SOURCE_TYPES}")
    if rec["quality_status"] not in QUALITY_STATUSES:
        errors.append(f"quality_status must be one of {QUALITY_STATUSES}")
    if "context" in rec and rec["context"] not in CONTEXTS:
        errors.append(f"context must be one of {CONTEXTS}")

    if value is None and rec["quality_status"] in ("valid", "suspect"):
        errors.append("value is null but quality_status says a reading exists")
    return errors


def dataframe_to_records(df: pd.DataFrame) -> list[dict]:
    """Convert a standard measurement DataFrame to contract dictionaries.

    Needs astronaut_code, metric_code, value, unit, measured_at (UTC), source_type,
    quality_status. A `context` column is included when present.
    """
    needed = ["astronaut_code", "metric_code", "value", "unit", "measured_at",
              "source_type", "quality_status"]
    missing = [c for c in needed if c not in df.columns]
    if missing:
        raise SchemaError(f"DataFrame lacks columns: {missing}")
    records = []
    has_ctx = "context" in df.columns
    for row in df.itertuples(index=False):
        rec = {
            "astronaut_code": str(row.astronaut_code),
            "metric_code": str(row.metric_code),
            "value": None if pd.isna(row.value) else float(row.value),
            "unit": str(row.unit),
            "measured_at": pd.Timestamp(row.measured_at).tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_type": str(row.source_type),
            "quality_status": str(row.quality_status),
        }
        if has_ctx:
            rec["context"] = str(row.context)
        records.append(rec)
    return records

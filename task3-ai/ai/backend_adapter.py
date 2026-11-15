"""Adapter from Task 3 review alerts to the backend README's POST /api/alerts body."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json

import pandas as pd

_SEVERITY = {"LOW": "watch", "MEDIUM": "warning", "HIGH": "critical"}
BACKEND_SEED_ASTRONAUT_IDS = {
    "CDR-01": 1,
    "DEMO-01": 2,
    "DEMO-02": 3,
    "DEMO-03": 4,
    "DEMO-04": 5,
}
# Exact values from the temporary seed.py provided by the user. Unit conversion is
# unnecessary here: degC and °C denote the same scale and magnitude.
BACKEND_SEED_INDICATORS = {
    "SLEEP_DURATION": ("sleep_hours", "hours"),
    "HEART_RATE": ("heart_rate", "bpm"),
    "BLOOD_OXYGEN_SPO2": ("spo2", "%"),
    "BODY_TEMPERATURE": ("body_temp", "°C"),
}

BACKEND_ALERT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "SapphireUSX POST /api/alerts request",
    "type": "object",
    "required": ["external_id", "astronaut_id", "severity", "title", "message", "generated_at"],
    "properties": {
        "external_id": {"type": "string", "minLength": 1},
        "astronaut_id": {"type": "integer", "minimum": 1},
        "indicator_code": {"type": "string", "minLength": 1},
        "severity": {"enum": ["info", "watch", "warning", "critical"]},
        "title": {"type": "string", "minLength": 1},
        "message": {"type": "string", "minLength": 1},
        "model_name": {"type": "string", "minLength": 1},
        "model_version": {"type": "string", "minLength": 1},
        "evidence": {"type": "object"},
        "generated_at": {"type": "string", "format": "date-time"},
    },
    "additionalProperties": False,
}


def _utc_z(value) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("generated_at must include a timezone")
    return timestamp.tz_convert("UTC").strftime("%Y-%m-%dT%H:%M:%SZ")


def build_backend_alert_requests(screened: pd.DataFrame, astronaut_ids: dict[str, int] | None = None,
                                 indicator_map: dict[str, tuple[str, str]] | None = None,
                                 generated_at=None, model_version: str = "1.0") -> list[dict]:
    """Convert alert rows into one validated request body per POST /api/alerts call.

    `astronaut_ids` defaults to the stable IDs from the supplied backend seed; pass a custom map
    when using a different database. `indicator_map` maps Task 3 codes to
    (backend indicator code, canonical unit); its default covers the four
    semantic matches found in the temporary seed.py. For other metrics the backend README/report
    permits omitting `indicator_code`; the original code and unit are retained in evidence.
    The function only builds request bodies; it does not send data or use an API key.
    """
    needed = {"astronaut_code", "metric_code", "measured_at", "value", "unit", "context",
              "alert_priority", "detector_findings", "data_label"}
    missing = sorted(needed - set(screened.columns))
    if missing:
        raise ValueError(f"build_backend_alert_requests() needs columns {missing}")
    stamp = _utc_z(generated_at if generated_at is not None else datetime.now(timezone.utc))
    if astronaut_ids is None:
        astronaut_ids = BACKEND_SEED_ASTRONAUT_IDS
    indicator_map = indicator_map or BACKEND_SEED_INDICATORS
    requests = []
    for row in screened[screened.alert_priority.notna()].itertuples(index=False):
        crew = str(row.astronaut_code)
        if crew not in astronaut_ids:
            raise ValueError(f"no backend astronaut_id mapping supplied for {crew}")
        source_metric = str(row.metric_code)
        priority = str(row.alert_priority)
        if priority not in _SEVERITY:
            raise ValueError(f"unsupported Task 3 priority: {priority}")
        mapping = indicator_map.get(source_metric)
        if mapping is not None and (len(mapping) != 2 or not mapping[0] or not mapping[1]):
            raise ValueError(f"backend indicator mapping for {source_metric} must include code and unit")
        metric, backend_unit = (str(mapping[0]), str(mapping[1])) if mapping else (None, str(row.unit))
        measured_at = _utc_z(row.measured_at)
        backend_astronaut_id = int(astronaut_ids[crew])
        identity = f"{backend_astronaut_id}|{crew}|{source_metric}|{measured_at}"
        external_id = "task3-ai:" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
        findings = row.detector_findings
        labels = [str(item.get("source_label", item.get("detector", "review finding")))
                  for item in findings]
        message = "Prototype monitoring flag for review: " + "; ".join(labels)
        evidence = {
            "data_label": str(row.data_label),
            "task3_metric_code": source_metric,
            "measured_at": measured_at,
            "value": float(row.value),
            "unit": backend_unit,
            "context": str(row.context),
            "findings": findings,
        }
        for field in ("baseline_status", "baseline_median", "baseline_mad", "baseline_scale",
                      "baseline_n", "baseline_span_hours"):
            if hasattr(row, field):
                value = getattr(row, field)
                if pd.notna(value):
                    evidence[field] = value.item() if hasattr(value, "item") else value
        if hasattr(row, "baseline_as_of") and pd.notna(row.baseline_as_of):
            evidence["baseline_as_of"] = _utc_z(row.baseline_as_of)
        body = {
            "external_id": external_id,
            "astronaut_id": backend_astronaut_id,
            "severity": _SEVERITY[priority],
            "title": f"{(metric or source_metric.lower()).replace('_', ' ').title()} monitoring alert",
            "message": message,
            "model_name": "sapphireusx-task3-rules",
            "model_version": str(model_version),
            "evidence": evidence,
            "generated_at": stamp,
        }
        if metric is not None:
            body["indicator_code"] = metric
        else:
            evidence["indicator_code_omitted_reason"] = "Task 3 metric is not present in the backend seed catalog"
        # Also ensure nested evidence contains only JSON-native values.
        body = json.loads(json.dumps(body, allow_nan=False))
        import jsonschema
        jsonschema.validate(body, BACKEND_ALERT_SCHEMA)
        requests.append(body)
    return requests

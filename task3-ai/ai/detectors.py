"""Explainable, rule-based screening for admissible vital measurements.

Published bands are Earth/general-population references, not astronaut thresholds.
The module returns review findings and never diagnoses or recommends treatment.
"""
from __future__ import annotations

import pandas as pd
import numpy as np

_CONTEXTS = {
    "heart_rate": {"awake"},
    "respiratory_rate": {"awake", "asleep"},
}
_PRIORITY = {"watch": "LOW", "review": "MEDIUM", "urgent": "HIGH"}
DEFAULT_BASELINE_Z_THRESHOLD = 3.5  # provisional robust outlier screen; not medically validated
_BASELINE_DIRECTION_OVERRIDES = {
    # Exercise time is a duration; a sustained unusually low value is the review direction.
    "EXERCISE_TIME": "low",
}


def _band_applies(metric: str, context: str, band) -> bool:
    metric = metric.lower()
    if context in {"exercise", "recovery"} and metric in _CONTEXTS:
        return False
    if metric in _CONTEXTS and context not in _CONTEXTS[metric]:
        return False
    guidance = str(getattr(band, "when_to_apply", "")).lower()
    if "context = awake" in guidance and context != "awake":
        return False
    if "context = awake or asleep" in guidance and context not in {"awake", "asleep"}:
        return False
    if "not during exercise" in guidance and context in {"exercise", "recovery"}:
        return False
    if "context only" in guidance:
        return False
    return True


def detect(validated: pd.DataFrame, reference_ranges: pd.DataFrame, metric_rules=None,
           baseline_z_threshold: float = DEFAULT_BASELINE_Z_THRESHOLD) -> pd.DataFrame:
    """Add reference-band and personal-baseline findings; excluded rows never alert."""
    needed = {"quality_status", "metric_code", "value", "context"}
    missing = sorted(needed - set(validated.columns))
    if missing:
        raise ValueError(f"detect() needs columns {missing}")
    bands = reference_ranges.copy()
    bands["metric_code"] = bands["metric_code"].astype(str).str.upper()
    grouped = {metric: tuple(group.itertuples(index=False))
               for metric, group in bands.groupby("metric_code", sort=False)}
    if baseline_z_threshold <= 0:
        raise ValueError("baseline_z_threshold must be positive")
    directions = (metric_rules.set_index("metric_code")["direction_of_concern"].to_dict()
                  if metric_rules is not None else {})
    n = len(validated)
    findings = [[] for _ in range(n)]
    priority_rank = np.zeros(n, dtype=np.int8)  # none, LOW, MEDIUM, HIGH
    priority_to_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}
    metric_values = validated["metric_code"].astype(str).to_numpy()
    context_values = validated["context"].astype(str).to_numpy()
    values = pd.to_numeric(validated["value"], errors="coerce").to_numpy(dtype=float)
    usable = (validated["quality_status"].eq("valid").to_numpy() & np.isfinite(values))

    # Work by metric and use NumPy masks; only construct Python findings for matched rows.
    for metric, positions in validated.groupby("metric_code", sort=False).indices.items():
        positions = np.asarray(positions, dtype=int)
        metric_valid = positions[usable[positions]]
        if not len(metric_valid):
            continue
        for band in grouped.get(str(metric), ()):
            flag = str(band.flag).lower()
            if flag not in _PRIORITY:
                continue
            context_ok = np.fromiter(
                (_band_applies(str(metric), context_values[p], band) for p in metric_valid),
                dtype=bool, count=len(metric_valid))
            lower = pd.to_numeric(pd.Series([band.band_low]), errors="coerce").iloc[0]
            upper = pd.to_numeric(pd.Series([band.band_high]), errors="coerce").iloc[0]
            match = context_ok.copy()
            if pd.notna(lower):
                match &= values[metric_valid] >= float(lower)
            if pd.notna(upper):
                match &= values[metric_valid] <= float(upper)
            matched = metric_valid[match]
            for p in matched:
                findings[p].append({
                    "detector": "reference_band", "flag": flag,
                    "source_label": str(band.source_label), "source": str(band.source),
                    "source_url": str(band.source_url),
                })
            priority_rank[matched] = np.maximum(priority_rank[matched], priority_to_rank[_PRIORITY[flag]])

        direction = str(directions.get(metric) or _BASELINE_DIRECTION_OVERRIDES.get(metric, "")).lower()
        if direction in {"low", "high", "both"} and {
            "baseline_status", "baseline_median", "baseline_scale", "baseline_n"
        }.issubset(validated.columns):
            subset = validated.iloc[metric_valid]
            median = pd.to_numeric(subset["baseline_median"], errors="coerce").to_numpy(dtype=float)
            scale = pd.to_numeric(subset["baseline_scale"], errors="coerce").to_numpy(dtype=float)
            baseline_ok = subset["baseline_status"].eq("ok").to_numpy() & np.isfinite(median) & np.isfinite(scale) & (scale > 0)
            if metric.lower() in _CONTEXTS:
                baseline_ok &= np.isin(context_values[metric_valid], list(_CONTEXTS[metric.lower()]))
            robust_z = np.divide(values[metric_valid] - median, scale,
                                 out=np.full(len(metric_valid), np.nan), where=scale > 0)
            concerned = (np.ones(len(metric_valid), dtype=bool) if direction == "both"
                         else (robust_z > 0 if direction == "high" else robust_z < 0))
            matched = metric_valid[baseline_ok & concerned & (np.abs(robust_z) >= baseline_z_threshold)]
            local_positions = {p: i for i, p in enumerate(metric_valid)}
            for p in matched:
                z = float(robust_z[local_positions[p]])
                findings[p].append({
                    "detector": "personal_baseline_deviation", "flag": "review",
                    "source_label": "Outside personal median/MAD baseline", "robust_z": z,
                    "threshold": float(baseline_z_threshold),
                    "baseline_n": int(validated.iloc[p].get("baseline_n", 0)),
                })
            priority_rank[matched] = np.maximum(priority_rank[matched], 1)

    symptom = np.char.startswith(metric_values.astype(str), "SYMPTOM_") & usable & (values == 1)
    for p in np.flatnonzero(symptom):
        findings[p].append({"detector": "reported_symptom", "flag": "review_needed",
                            "source_label": "Symptom reported by crew"})
    priority_rank[symptom] = np.maximum(priority_rank[symptom], 2)
    priorities = [None, "LOW", "MEDIUM", "HIGH"]
    priority_values = [priorities[int(rank)] for rank in priority_rank]
    out = validated.copy()
    out["detector_findings"] = findings
    out["alert_priority"] = priority_values
    out["data_label"] = out["source_type"].map({
        "synthetic": "SIMULATED DATA",
        "real_nasa": "REAL NASA RESEARCH DATA",
        "user_entered": "USER-ENTERED DATA",
    }) if "source_type" in out else "UNKNOWN DATA ORIGIN"
    return out

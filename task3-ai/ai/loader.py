"""Data loading: read the Task 1 files and map them to the project contract."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ai.schema import (CONTEXTS, DEVICE_QUALITY_STATUSES, ORIGIN_TO_SOURCE_TYPE,
                       SchemaError, TASK1_REQUIRED_COLUMNS)


def load_task1_vitals(path) -> pd.DataFrame:
    """Load Task 1 `simulated_vitals_long` (.csv or single-file .zip), version 3.

    Mapping: participant_id -> astronaut_code, indicator -> metric_code (UPPER CASE),
    timestamp -> measured_at (UTC), data_origin -> source_type,
    quality_status (device) -> device_quality_status. `row_id` is the 0-based
    position in the file, kept for traceability.

    Raises SchemaError when columns, timestamps, numbers or labels are not as expected.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    raw = pd.read_csv(path)

    missing = [c for c in TASK1_REQUIRED_COLUMNS if c not in raw.columns]
    if missing:
        raise SchemaError(
            f"{path.name} lacks columns {missing}. Version 3 of the Task 1 file is required "
            "(it has 'context' and 'quality_status')."
        )

    measured_at = pd.to_datetime(raw["timestamp"], utc=True, errors="coerce", format="ISO8601")
    n_bad = int(measured_at.isna().sum())
    if n_bad:
        raise SchemaError(f"{n_bad} rows have an unreadable timestamp")

    value = pd.to_numeric(raw["value"], errors="coerce")
    n_bad = int((value.isna() & raw["value"].notna()).sum())
    if n_bad:
        raise SchemaError(f"{n_bad} rows have a non-numeric value")

    origin = raw["data_origin"].astype(str).str.strip()
    unknown = sorted(set(origin) - set(ORIGIN_TO_SOURCE_TYPE))
    if unknown:
        raise SchemaError(f"unknown data_origin labels: {unknown}")

    status = raw["quality_status"].astype(str).str.strip().str.lower()
    unknown = sorted(set(status) - set(DEVICE_QUALITY_STATUSES))
    if unknown:
        raise SchemaError(f"unknown quality_status values: {unknown}")

    context = raw["context"].astype(str).str.strip().str.lower()
    unknown = sorted(set(context) - set(CONTEXTS))
    if unknown:
        raise SchemaError(f"unknown context values: {unknown}")

    return pd.DataFrame({
        "row_id": np.arange(len(raw)),
        "astronaut_code": raw["participant_id"].astype(str).str.strip(),
        "metric_code": raw["indicator"].astype(str).str.strip().str.upper(),
        "value": value.astype(float),
        "unit": raw["unit"].astype(str).str.strip(),
        "measured_at": measured_at,
        "context": context,
        "device_quality_status": status,
        "source_type": origin.map(ORIGIN_TO_SOURCE_TYPE),
        "collection_method": raw["collection_method"].astype(str).str.strip(),
        "source_note": raw["source_note"].astype(str).str.strip(),
    })


def load_metric_table(path) -> pd.DataFrame:
    """Task 1 `metric_table.csv` (sourced ranges); metric_code added in UPPER CASE."""
    df = pd.read_csv(path)
    df["metric_code"] = df["indicator"].astype(str).str.strip().str.upper()
    return df


def load_reference_ranges(path) -> pd.DataFrame:
    """Task 1 `reference_ranges.csv` (published bands); metric_code added in UPPER CASE."""
    df = pd.read_csv(path)
    df["metric_code"] = df["indicator"].astype(str).str.strip().str.upper()
    return df


def load_daily_schedule(path) -> pd.DataFrame:
    """Task 1 `daily_schedule.csv`; time columns parsed as UTC (blank = no exercise that day)."""
    df = pd.read_csv(path)
    for col in ["sleep_start", "sleep_end", "exercise_start", "exercise_end", "recovery_end"]:
        df[col] = pd.to_datetime(df[col], utc=True, errors="coerce", format="ISO8601")
    return df


def load_planted_events(path) -> pd.DataFrame:
    """Task 1 `planted_events.csv` (answer key). `metric_codes` is a list of UPPER CASE codes."""
    df = pd.read_csv(path)
    df["start"] = pd.to_datetime(df["start"], utc=True, format="ISO8601")
    df["end"] = pd.to_datetime(df["end"], utc=True, format="ISO8601")
    df["metric_codes"] = df["indicators"].astype(str).apply(
        lambda s: [x.strip().upper() for x in s.split(";") if x.strip()]
    )
    return df

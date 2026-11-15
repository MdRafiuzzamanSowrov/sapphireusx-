"""Preprocessing: decide which rows may feed the analysis, and add a mission-day label.

Decisions (documented in docs/ai_methodology.md):
- Only rows with quality_status == 'valid' are usable. Missing, invalid, suspect and duplicate
  rows are kept aside (not deleted) so they can be reported as data limitations.
- Duplicates are already marked by the validator (first occurrence kept), so nothing is dropped here.
- NO resampling or interpolation. Gaps stay gaps: filling them would invent measurements.
"""
from __future__ import annotations

import pandas as pd

_SORT = ["astronaut_code", "metric_code", "measured_at", "row_id"]


def split_usable(validated: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (usable, excluded). `usable` is sorted by astronaut, metric, time with a fresh index."""
    needed = ["quality_status", "astronaut_code", "metric_code", "measured_at"]
    missing = [c for c in needed if c not in validated.columns]
    if missing:
        raise ValueError(f"split_usable() needs columns {missing} (run ai.validator.validate first)")
    df = validated.copy()
    if "row_id" not in df.columns:
        df["row_id"] = range(len(df))
    ok = df["quality_status"] == "valid"
    usable = df[ok].sort_values(_SORT, kind="stable").reset_index(drop=True)
    excluded = df[~ok].sort_values("row_id", kind="stable").reset_index(drop=True)
    return usable, excluded


def add_mission_day(df: pd.DataFrame, mission_start=None) -> pd.DataFrame:
    """Add `mission_day` (1 = the UTC day of mission_start).

    mission_start defaults to midnight UTC of the earliest measurement in `df`.
    """
    out = df.copy()
    if mission_start is None:
        mission_start = out["measured_at"].min().floor("D")
    start = pd.Timestamp(mission_start)
    start = start.tz_localize("UTC") if start.tzinfo is None else start.tz_convert("UTC")
    start = start.floor("D")
    out["mission_day"] = ((out["measured_at"] - start) // pd.Timedelta(days=1)).astype(int) + 1
    return out

"""Data-quality layer (Layer 1). Quality problems are NOT health alerts.

validate() adds two columns to a measurement DataFrame:
  dq_reasons      ';'-joined reason codes ('' = no problem)
  quality_status  valid | missing | invalid | suspect | duplicate

Only rows with quality_status == 'valid' may feed baselines and health detectors.
Reason codes: device_missing, empty_value, device_invalid, impossible_value,
out_of_scale, non_monotonic, unit_mismatch, unknown_metric, flatline,
duplicate, duplicate_conflict.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ai.config import load_config

_KEY = ["astronaut_code", "metric_code", "measured_at"]
_INVALID_REASONS = {"device_invalid", "impossible_value", "out_of_scale",
                    "non_monotonic", "unit_mismatch", "unknown_metric"}
_MISSING_REASONS = {"device_missing", "empty_value"}
_REQUIRED = ["astronaut_code", "metric_code", "value", "unit", "measured_at", "device_quality_status"]


def _empty(n):
    return np.zeros(n, dtype=bool)


def _validity_masks(out: pd.DataFrame, metrics: dict):
    """Impossible-value, out-of-scale and unknown/unit problems (vectorised per metric)."""
    n = len(out)
    impossible, scale, unit_bad, unknown = _empty(n), _empty(n), _empty(n), _empty(n)
    known = out["metric_code"].isin(list(metrics))
    unknown |= ~known.to_numpy()
    for code, cfg in metrics.items():
        sel = (out["metric_code"] == code).to_numpy()
        if not sel.any():
            continue
        unit_bad |= sel & (out["unit"] != cfg["unit"]).to_numpy()
        v = out["value"]
        has_val = v.notna().to_numpy()
        rules = cfg.get("validity") or {}
        bad = _empty(n)
        if "min" in rules:
            bad |= (v < rules["min"]).to_numpy()
        if "min_exclusive" in rules:
            bad |= (v <= rules["min_exclusive"]).to_numpy()
        if "max" in rules:
            bad |= (v > rules["max"]).to_numpy()
        impossible |= sel & has_val & bad
        sbad = _empty(n)
        if "integer_range" in rules:
            lo, hi = rules["integer_range"]
            ok = ((v == v.round()) & (v >= lo) & (v <= hi)).to_numpy()
            sbad |= ~ok
        if "allowed_values" in rules:
            sbad |= ~v.isin(rules["allowed_values"]).to_numpy()
        scale |= sel & has_val & sbad
    return impossible, scale, unit_bad, unknown


def _monotonic_mask(out: pd.DataFrame, metrics: dict, dup: np.ndarray) -> np.ndarray:
    mask = _empty(len(out))
    for code, cfg in metrics.items():
        if (cfg.get("validity") or {}).get("monotonic") != "nondecreasing":
            continue
        sel = (out["metric_code"] == code).to_numpy() & ~dup & out["value"].notna().to_numpy()
        sub = out.loc[sel, ["astronaut_code", "measured_at", "value"]].sort_values(
            ["astronaut_code", "measured_at"], kind="stable")
        if sub.empty:
            continue
        running_max = sub.groupby("astronaut_code")["value"].cummax()
        prev_max = running_max.groupby(sub["astronaut_code"]).shift()
        bad = (sub["value"] < prev_max).to_numpy()
        mask[sub.index[bad].to_numpy()] = True
    return mask


def _flatline_mask(out: pd.DataFrame, metrics: dict, dup: np.ndarray) -> np.ndarray:
    """Flag every reading of a run of >= flatline_min_run identical consecutive values."""
    mask = _empty(len(out))
    for code, cfg in metrics.items():
        n_run = cfg.get("flatline_min_run")
        if not n_run:
            continue
        sel = (out["metric_code"] == code).to_numpy() & ~dup & out["value"].notna().to_numpy()
        sub = out.loc[sel, ["astronaut_code", "measured_at", "value"]].sort_values(
            ["astronaut_code", "measured_at"], kind="stable")
        if sub.empty:
            continue
        new_run = (sub["astronaut_code"] != sub["astronaut_code"].shift()) | (sub["value"] != sub["value"].shift())
        run_id = new_run.cumsum()
        run_len = sub.groupby(run_id)["value"].transform("size")
        mask[sub.index[(run_len >= n_run).to_numpy()].to_numpy()] = True
    return mask


def validate(df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """Return a copy of `df` (original row order) with `dq_reasons` and `quality_status`."""
    missing_cols = [c for c in _REQUIRED if c not in df.columns]
    if missing_cols:
        raise ValueError(f"validate() needs columns {missing_cols}")
    cfg = config or load_config()
    metrics = cfg["metrics"]

    out = df.copy()
    if "row_id" not in out.columns:
        out["row_id"] = np.arange(len(out))
    out = out.sort_values("row_id", kind="stable").reset_index(drop=True)
    n = len(out)

    # duplicates: the first occurrence in the file is kept, later ones are flagged
    dup = out.duplicated(_KEY, keep="first").to_numpy()
    first_val = out.groupby(_KEY)["value"].transform("first")
    same = ((out["value"] == first_val) | (out["value"].isna() & first_val.isna())).to_numpy()
    dup_conflict = dup & ~same
    dup_plain = dup & same

    dev_missing = (out["device_quality_status"] == "missing").to_numpy()
    dev_invalid = (out["device_quality_status"] == "invalid").to_numpy()
    empty_value = out["value"].isna().to_numpy() & ~dev_missing

    impossible, scale, unit_bad, unknown = _validity_masks(out, metrics)
    nonmono = _monotonic_mask(out, metrics, dup)
    flat = _flatline_mask(out, metrics, dup)

    flags = {
        "duplicate": dup_plain, "duplicate_conflict": dup_conflict,
        "device_missing": dev_missing, "empty_value": empty_value,
        "device_invalid": dev_invalid, "impossible_value": impossible,
        "out_of_scale": scale, "non_monotonic": nonmono,
        "unit_mismatch": unit_bad, "unknown_metric": unknown, "flatline": flat,
    }
    reasons = np.full(n, "", dtype=object)
    for name, m in flags.items():
        if m.any():
            reasons[m] = np.where(reasons[m] == "", name, reasons[m] + ";" + name)

    status = np.full(n, "valid", dtype=object)
    status[flat] = "suspect"
    status[nonmono | impossible | scale | unit_bad | unknown | dev_invalid] = "invalid"
    status[dev_missing | empty_value] = "missing"
    status[dup] = "duplicate"

    out["dq_reasons"] = reasons
    out["quality_status"] = status
    return out


def summarize(validated: pd.DataFrame) -> dict:
    """Counts for a data-quality report."""
    reason_counts: dict[str, int] = {}
    for text in validated["dq_reasons"]:
        for r in filter(None, text.split(";")):
            reason_counts[r] = reason_counts.get(r, 0) + 1
    return {
        "rows": int(len(validated)),
        "by_status": {k: int(v) for k, v in validated["quality_status"].value_counts().items()},
        "by_reason": dict(sorted(reason_counts.items())),
        "usable_rows": int((validated["quality_status"] == "valid").sum()),
    }


def quality_episodes(validated: pd.DataFrame, max_gap: str = "30min") -> pd.DataFrame:
    """Group flagged rows into episodes (same astronaut, metric, reason, gaps <= max_gap)."""
    flagged = validated[validated["dq_reasons"] != ""].copy()
    cols = ["astronaut_code", "metric_code", "reason", "start", "end", "n_rows"]
    if flagged.empty:
        return pd.DataFrame(columns=cols)
    flagged["reason"] = flagged["dq_reasons"].str.split(";")
    flagged = flagged.explode("reason")
    flagged = flagged.sort_values(["astronaut_code", "metric_code", "reason", "measured_at"], kind="stable")
    g = ["astronaut_code", "metric_code", "reason"]
    gap = flagged.groupby(g)["measured_at"].diff()
    new_ep = gap.isna() | (gap > pd.Timedelta(max_gap))
    flagged["episode"] = new_ep.cumsum()
    res = flagged.groupby(g + ["episode"]).agg(
        start=("measured_at", "min"), end=("measured_at", "max"), n_rows=("row_id", "size")
    ).reset_index().drop(columns="episode")
    return res[cols].sort_values(["start", "astronaut_code"]).reset_index(drop=True)

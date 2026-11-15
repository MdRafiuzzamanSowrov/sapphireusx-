"""Personal baseline (Layer 2).

For every reading, the baseline is the median and MAD of the SAME astronaut's EARLIER valid
readings of the SAME metric in the SAME context (awake / asleep / exercise / recovery).

Rules (settings in ai/config/thresholds.yaml, section `baseline`):
- No peeking: the window is [as_of - lookback, as_of) where as_of is the start of the reading's own
  time step (default 1 h). The reading itself and anything later are never used.
- The baseline is ready only when the window has >= min_points readings AND they span
  >= min_span_hours. Otherwise baseline_status = 'insufficient_history'.
- Robust scale = max(1.4826 * MAD, min_scale). The floor avoids dividing by ~0 when a rounded
  sensor repeats the same value.
- Metrics with `enabled: false` (binary reports, running totals, 2-point series) get
  baseline_status = 'not_configured'.

Known limitations (also in docs/ai_methodology.md):
- Anomalous readings already inside the window can pull the baseline (median/MAD limit, not remove, this).
  A slow drift is partly absorbed by its own baseline.
- No time-of-day (circadian) adjustment inside a context.
- Baselines of a few days are statistically weak; the output always carries baseline_n and
  baseline_span_hours so the evidence can be shown with every alert.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from ai.config import load_config

MAD_TO_SIGMA = 1.4826        # makes MAD comparable to a standard deviation for bell-shaped data
_NS_PER_HOUR = 3_600_000_000_000
_NS_PER_DAY = 24 * _NS_PER_HOUR
_NS_PER_MIN = 60_000_000_000
_REQUIRED = ["astronaut_code", "metric_code", "context", "value", "measured_at"]
BASELINE_COLUMNS = ["baseline_status", "baseline_median", "baseline_mad", "baseline_scale",
                    "baseline_n", "baseline_span_hours", "baseline_as_of"]


def attach_baselines(usable: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
    """Return a copy of `usable` (valid rows only) with the BASELINE_COLUMNS added."""
    missing = [c for c in _REQUIRED if c not in usable.columns]
    if missing:
        raise ValueError(f"attach_baselines() needs columns {missing}")
    cfg = config or load_config()
    g = cfg.get("baseline") or {}
    lookback_ns = int(float(g.get("lookback_days", 7)) * _NS_PER_DAY)
    step_ns = int(float(g.get("as_of_step_minutes", 60)) * _NS_PER_MIN)
    default_points = int(g.get("min_points", 20))
    default_span_ns = int(float(g.get("min_span_hours", 24)) * _NS_PER_HOUR)

    out = usable.reset_index(drop=True).copy()
    n = len(out)
    t_all = (out["measured_at"].dt.tz_convert("UTC").dt.tz_localize(None)
             .astype("datetime64[ns]").to_numpy().astype("int64"))
    v_all = out["value"].to_numpy(dtype=float)

    med = np.full(n, np.nan)
    mad = np.full(n, np.nan)
    scale = np.full(n, np.nan)
    cnt = np.zeros(n, dtype=int)
    span = np.full(n, np.nan)
    as_of_ns = np.zeros(n, dtype="int64")
    status = np.full(n, "not_configured", dtype=object)
    configured = np.zeros(n, dtype=bool)

    metrics = cfg["metrics"]
    for (_, metric, _), pos in out.groupby(["astronaut_code", "metric_code", "context"], sort=False).indices.items():
        if metric not in metrics:
            continue
        mcfg = metrics[metric].get("baseline") or {}
        if mcfg.get("enabled", True) is False:
            continue
        min_points = int(mcfg.get("min_points", default_points))
        min_span_ns = int(float(mcfg.get("min_span_hours", default_span_ns / _NS_PER_HOUR)) * _NS_PER_HOUR)
        min_scale = float(mcfg.get("min_scale", 0.0))

        order = pos[np.argsort(t_all[pos], kind="stable")]
        ti, vi = t_all[order], v_all[order]
        as_of = ti - (ti % step_ns)
        uniq, inv = np.unique(as_of, return_inverse=True)
        lo = np.searchsorted(ti, uniq - lookback_ns, side="left")
        hi = np.searchsorted(ti, uniq, side="left")          # strictly before as_of

        u_cnt = hi - lo
        u_med = np.full(len(uniq), np.nan)
        u_mad = np.full(len(uniq), np.nan)
        u_span = np.full(len(uniq), np.nan)
        u_ok = np.zeros(len(uniq), dtype=bool)
        for k in range(len(uniq)):
            if u_cnt[k] == 0:
                continue
            span_ns = uniq[k] - ti[lo[k]]
            u_span[k] = span_ns / _NS_PER_HOUR
            if u_cnt[k] >= min_points and span_ns >= min_span_ns:
                w = vi[lo[k]:hi[k]]
                m = np.median(w)
                u_med[k], u_mad[k], u_ok[k] = m, np.median(np.abs(w - m)), True
        u_scale = np.where(u_ok, np.maximum(MAD_TO_SIGMA * u_mad, min_scale), np.nan)

        med[order], mad[order], scale[order] = u_med[inv], u_mad[inv], u_scale[inv]
        cnt[order], span[order], as_of_ns[order] = u_cnt[inv], u_span[inv], uniq[inv]
        status[order] = np.where(u_ok[inv], "ok", "insufficient_history")
        configured[order] = True

    as_of_ts = pd.Series(pd.to_datetime(as_of_ns, unit="ns", utc=True))
    out["baseline_status"] = status
    out["baseline_median"] = med
    out["baseline_mad"] = mad
    out["baseline_scale"] = scale
    out["baseline_n"] = np.where(configured, cnt, 0)
    out["baseline_span_hours"] = span
    out["baseline_as_of"] = as_of_ts.where(configured, pd.NaT)
    return out


def baseline_coverage(with_baselines: pd.DataFrame) -> pd.DataFrame:
    """Share of readings that have a ready baseline, per metric and context."""
    df = with_baselines
    res = df.groupby(["metric_code", "context"]).agg(
        readings=("value", "size"),
        with_baseline=("baseline_status", lambda s: int((s == "ok").sum())),
        not_configured=("baseline_status", lambda s: int((s == "not_configured").sum())),
    ).reset_index()
    res["share_with_baseline"] = (res["with_baseline"] / res["readings"]).round(3)
    return res

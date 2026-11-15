"""Evaluation helpers for alert behavior on the SIMULATED planted-event key."""
from __future__ import annotations

import pandas as pd


def evaluate_planted_alerts(screened: pd.DataFrame, events: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Report event coverage and alerts without a matching expected event window.

    This is a software check against synthetic answer-key windows, not clinical performance.
    Background symptoms are expected alerts; data-quality and no-alert events are not health alerts.
    """
    needed = {"astronaut_code", "metric_code", "measured_at", "alert_priority"}
    missing = sorted(needed - set(screened.columns))
    if missing:
        raise ValueError(f"evaluate_planted_alerts() needs columns {missing}")
    positive = events[events.category.isin(["health_event", "background_symptom"])]
    rows = []
    expected_mask = pd.Series(False, index=screened.index)
    for event in positive.itertuples():
        mask = ((screened.astronaut_code == event.participant_id)
                & screened.metric_code.isin(event.metric_codes)
                & (screened.measured_at >= event.start) & (screened.measured_at < event.end))
        expected_mask |= mask
        subset = screened[mask]
        flagged = subset[subset.alert_priority.notna()]
        rows.append({
            "event_id": event.event_id,
            "category": event.category,
            "expected_alert": True,
            "matching_rows": int(len(subset)),
            "flagged_rows": int(len(flagged)),
            "event_detected": bool(len(flagged)),
            "label": "SIMULATED DATA",
        })
    alert_mask = screened.alert_priority.notna()
    unexplained = screened[alert_mask & ~expected_mask].copy()
    summary = pd.DataFrame([{
        "label": "SIMULATED DATA",
        "expected_events": int(len(positive)),
        "detected_events": int(sum(r["event_detected"] for r in rows)),
        "event_coverage": (sum(r["event_detected"] for r in rows) / len(positive)) if len(positive) else float("nan"),
        "alert_rows": int(alert_mask.sum()),
        "alert_rows_inside_expected_windows": int((alert_mask & expected_mask).sum()),
        "alert_rows_outside_expected_windows": int(len(unexplained)),
        "interpretation": "synthetic software evaluation only; outside-window rows are not confirmed clinical false positives",
    }])
    return {"summary": summary, "events": pd.DataFrame(rows), "unassociated_alerts": unexplained}

"""Optional IsolationForest comparison; outputs are experimental flags only.

Nothing from this module may enter detector severity or the alert policy.
"""
from __future__ import annotations

import pandas as pd
from sklearn.ensemble import IsolationForest

from ai.loader import load_planted_events


def isolation_forest_experiment(valid_rows: pd.DataFrame, planted_events=None,
                                contamination: float = 0.02, random_state: int = 575):
    """Score valid rows independently by metric, then compare flags with planted health events.

    Returns (row-level scores, evaluation summary). Each model sees one metric at a time to
    avoid comparing incompatible units. Experimental flags never assign or change severity.
    """
    needed = {"quality_status", "metric_code", "value", "astronaut_code", "measured_at"}
    missing = sorted(needed - set(valid_rows.columns))
    if missing:
        raise ValueError(f"isolation_forest_experiment() needs columns {missing}")
    if not 0 < contamination < 0.5:
        raise ValueError("contamination must be between 0 and 0.5")
    data = valid_rows[valid_rows.quality_status == "valid"].copy().reset_index(drop=True)
    data["experimental_anomaly"] = False
    data["experimental_score"] = float("nan")
    for metric, positions in data.groupby("metric_code", sort=True).indices.items():
        vals = data.iloc[positions][["value"]]
        if len(vals) < 20 or vals.value.nunique() < 2:
            continue
        model = IsolationForest(contamination=contamination, random_state=random_state, n_estimators=100)
        model.fit(vals)
        data.loc[positions, "experimental_anomaly"] = model.predict(vals) == -1
        data.loc[positions, "experimental_score"] = -model.score_samples(vals)
    events = planted_events
    if events is None:
        from pathlib import Path
        events = load_planted_events(Path(__file__).resolve().parents[1] / "data/task1/planted_events.csv")
    events = events[events.category == "health_event"]
    target = pd.Series(False, index=data.index)
    for event in events.itertuples():
        match = ((data.astronaut_code == event.participant_id)
                 & data.metric_code.isin(event.metric_codes)
                 & (data.measured_at >= event.start) & (data.measured_at < event.end))
        target |= match
    flagged = data.experimental_anomaly
    target_rows, flagged_target = int(target.sum()), int((target & flagged).sum())
    summary = pd.DataFrame([{
        "label": "SIMULATED DATA",
        "method": "IsolationForest experimental comparison",
        "contamination": contamination,
        "planted_health_rows": target_rows,
        "flagged_planted_rows": flagged_target,
        "planted_row_recall": flagged_target / target_rows if target_rows else float("nan"),
        "flagged_rows": int(flagged.sum()),
        "flagged_outside_planted_rows": int((flagged & ~target).sum()),
        "severity_effect": "none",
    }])
    data["experimental_label"] = "SIMULATED DATA"
    return data, summary

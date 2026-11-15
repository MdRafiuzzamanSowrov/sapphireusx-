"""Small plotting helpers; charts preserve dataset provenance labels."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_osd575(summary: pd.DataFrame, output_path) -> Path:
    """Plot the descriptive median and interquartile range for the nine lab biomarkers."""
    required = {"analyte", "unit", "median", "q1", "q3", "data_label"}
    if required - set(summary.columns):
        raise ValueError(f"plot_osd575() needs columns {sorted(required)}")
    fig, ax = plt.subplots(figsize=(12, 6))
    x = range(len(summary))
    med = summary["median"].to_numpy()
    ax.errorbar(x, med, yerr=[med - summary.q1.to_numpy(), summary.q3.to_numpy() - med], fmt="o", capsize=4)
    ax.set_xticks(list(x), [f"{a}\n({u})" for a, u in zip(summary.analyte, summary.unit)], rotation=30, ha="right")
    ax.set_title("OSD-575 cardiovascular panel — descriptive median and IQR\nREAL NASA RESEARCH DATA")
    ax.set_ylabel("Concentration (units shown per biomarker)")
    ax.grid(axis="y", alpha=.25)
    fig.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path


def plot_vital_series(rows: pd.DataFrame, astronaut: str, metric: str, output_path) -> Path:
    """Plot one crew/metric time series with context and provenance in the figure title."""
    selected = rows[(rows.astronaut_code == astronaut) & (rows.metric_code == metric)].sort_values("measured_at")
    if selected.empty:
        raise ValueError("no rows match the requested astronaut and metric")
    label = selected["data_label"].iloc[0] if "data_label" in selected else "DATA ORIGIN NOT PROVIDED"
    fig, ax = plt.subplots(figsize=(11, 4.5))
    for context, part in selected.groupby("context", sort=False):
        ax.plot(part.measured_at, part.value, marker=".", linewidth=1, label=context)
    ax.set_title(f"{metric} — {astronaut}\n{label}")
    ax.set_xlabel("Time (UTC)")
    ax.set_ylabel(str(selected.unit.iloc[0]) if "unit" in selected else "Value")
    ax.legend(title="Context")
    ax.grid(alpha=.25)
    fig.tight_layout()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return path

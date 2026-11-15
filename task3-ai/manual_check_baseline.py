"""Manual check of preprocessing + personal baseline (SIMULATED DATA). Run from the task3-ai folder."""
import pandas as pd
from ai.loader import load_task1_vitals
from ai.validator import validate
from ai.preprocess import split_usable, add_mission_day
from ai.baseline import attach_baselines, baseline_coverage

pd.set_option("display.width", 200, "display.max_columns", 30)
v = validate(load_task1_vitals("data/task1/simulated_vitals_long.zip"))
usable, excluded = split_usable(v)
b = attach_baselines(add_mission_day(usable))
print("usable:", len(usable), "| excluded:", len(excluded))
print(b["baseline_status"].value_counts().to_dict())

# 1. The planted heart-rate event of DEMO-04 (day 3, about 09:45): value vs its personal baseline
cols = ["measured_at", "value", "context", "baseline_status", "baseline_median", "baseline_scale",
        "baseline_n", "baseline_span_hours"]
row = b[(b.astronaut_code == "DEMO-04") & (b.metric_code == "HEART_RATE")
        & (b.measured_at == pd.Timestamp("2026-11-03T09:50:00Z"))]
print("\n1. DEMO-04 heart rate, planted event window"); print(row[cols].to_string(index=False, float_format=lambda x: f"{x:.2f}"))
print("   deviation in robust units:", round(float((row.value.iloc[0] - row.baseline_median.iloc[0]) / row.baseline_scale.iloc[0]), 1))

# 2. A normal reading from the same person a day earlier
row = b[(b.astronaut_code == "DEMO-04") & (b.metric_code == "HEART_RATE")
        & (b.measured_at == pd.Timestamp("2026-11-02T09:50:00Z"))]
print("\n2. DEMO-04 heart rate on day 2, normal"); print(row[cols].to_string(index=False, float_format=lambda x: f"{x:.2f}"))

# 3. Day 1: there is not enough history yet
row = b[(b.astronaut_code == "DEMO-04") & (b.metric_code == "HEART_RATE")
        & (b.measured_at == pd.Timestamp("2026-11-01T09:50:00Z"))]
print("\n3. DEMO-04 heart rate on day 1"); print(row[cols].to_string(index=False, float_format=lambda x: f"{x:.2f}"))

# 4. Coverage per metric and context
print("\n4. Coverage (share of readings with a ready baseline)")
print(baseline_coverage(b)[["metric_code", "context", "readings", "share_with_baseline"]].head(12).to_string(index=False))

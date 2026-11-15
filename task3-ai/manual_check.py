import json
import pandas as pd
from ai.loader import load_task1_vitals
from ai.validator import validate, summarize, quality_episodes
from ai.schema import dataframe_to_records, validate_measurement_record

# --- A. the real Task 1 file (SIMULATED DATA)
df = load_task1_vitals("data/task1/simulated_vitals_long.zip")
v = validate(df)
print("A. rows:", len(df)); print(json.dumps(summarize(v), indent=1))
print(quality_episodes(v)[["astronaut_code","metric_code","reason","start","n_rows"]].to_string())

# --- B. hand-made rows: do the checks catch what they should?
T0 = pd.Timestamp("2026-11-01T00:00:00Z")
def row(m, val, unit, minute=0, status="valid"):
    return dict(astronaut_code="TEST-1", metric_code=m, value=val, unit=unit,
                measured_at=T0 + pd.Timedelta(minutes=minute), context="awake",
                device_quality_status=status)
rows = [row("HEART_RATE", 62, "bpm", 0),                 # normal
        row("HEART_RATE", 0, "bpm", 1),                  # impossible
        row("BLOOD_OXYGEN_SPO2", 127, "%", 2),           # impossible
        row("STRESS_SCORE", 9, "score_1_to_5", 3),       # outside the 1-5 scale
        row("BLOOD_OXYGEN_SPO2", 84, "%", 4, "invalid"), # device says the reading is bad
        row("HEART_RATE", None, "bpm", 5, "missing")]    # dropout
rows += [row("HEART_RATE", 71, "bpm", 10 + i) for i in range(30)]   # stuck sensor, 30 identical
t = validate(pd.DataFrame(rows))
print("\nB. hand-made rows"); print(t[["metric_code","value","quality_status","dq_reasons"]].head(8).to_string())
print("stuck-sensor rows flagged:", int((t.dq_reasons == "flatline").sum()), "of 30")

# --- C. JSON for the backend
recs = dataframe_to_records(v.head(2))
print("\nC. JSON"); print(json.dumps(recs, indent=1))
print("contract errors:", [validate_measurement_record(r) for r in recs])
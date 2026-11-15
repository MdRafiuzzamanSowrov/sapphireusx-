"""Seed data. Safe to re-run: existing rows are kept, missing ones are added.
Member 1: edit INDICATORS when the final list is agreed (the list below is a temporary draft)."""
import random
from datetime import datetime, timedelta, timezone
import db

INDICATORS = [  # code, name, category, unit, min_valid, max_valid, ref_low, ref_high
    ("sleep_hours",   "Sleep duration",   "sleep",     "hours", 0, 24, 7, 9),
    ("mood_score",    "Mood (1=Low, 2=Okay, 3=Great)", "mental", "score", 1, 3, 2, 3),
    ("steps",         "Movement",         "activity",  "steps", 0, 100000, 5000, None),
    ("hydration_pct", "Hydration",        "hydration", "%",     0, 100, 70, 100),
    ("heart_rate",    "Resting heart rate","vital",    "bpm",   20, 250, 50, 90),
    ("spo2",          "Blood oxygen",     "vital",     "%",     50, 100, 94, 100),
    ("body_temp",     "Body temperature", "vital",     "°C",    30, 43, 36.1, 37.5),
]

# Stable IDs: these never change between seeds, so other members can hard-code them.
ASTRONAUTS = [  # id, code, display_name
    (1, "CDR-01",  "Commander"),
    (2, "DEMO-01", "Demo Astronaut 1"),
    (3, "DEMO-02", "Demo Astronaut 2"),
    (4, "DEMO-03", "Demo Astronaut 3"),
    (5, "DEMO-04", "Demo Astronaut 4"),
]

# Simulated profiles (ranges are inclusive). All values are SIMULATED, not real health data.
PROFILES = {
    1: dict(seed=7,  profile="baseline (original sample)", sleep=(5.5, 8.5), hr=(55, 78), spo2=(95, 99), hyd=(65, 95), steps=(3000, 9000),  temp=(36.4, 37.0)),
    2: dict(seed=21, profile="well rested, active",        sleep=(7.2, 8.6), hr=(52, 66), spo2=(97, 99), hyd=(80, 95), steps=(7000, 12000), temp=(36.4, 36.9)),
    3: dict(seed=33, profile="short sleep",                sleep=(4.8, 6.5), hr=(66, 84), spo2=(95, 98), hyd=(70, 88), steps=(3000, 7000),  temp=(36.5, 37.1)),
    4: dict(seed=45, profile="low hydration",              sleep=(6.0, 7.8), hr=(70, 92), spo2=(95, 98), hyd=(52, 72), steps=(4000, 8000),  temp=(36.6, 37.4)),
    5: dict(seed=57, profile="low activity",               sleep=(6.5, 8.0), hr=(60, 75), spo2=(93, 97), hyd=(68, 85), steps=(800, 3500),   temp=(36.3, 36.9)),
}

def seed(conn, days=14):
    for i in INDICATORS:
        conn.execute("INSERT OR IGNORE INTO indicators (code,name,category,unit,min_valid,max_valid,ref_low,ref_high) VALUES (?,?,?,?,?,?,?,?)", i)
    for a in ASTRONAUTS:
        conn.execute("INSERT OR IGNORE INTO astronauts (id,code,display_name) VALUES (?,?,?)", a)
    for name, kind in [("frontend_checkin", "self_report"), ("sim_generator_v1", "simulated"), ("wearable_demo", "sensor")]:
        conn.execute("INSERT OR IGNORE INTO data_sources (name,kind) VALUES (?,?)", (name, kind))
    conn.execute("INSERT OR IGNORE INTO nasa_datasets (id,title,url,citation) VALUES (1,'PLACEHOLDER - replace with the real NASA dataset','https://example.invalid','TODO')")
    conn.commit()

    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    sim_id = conn.execute("SELECT id FROM data_sources WHERE name='sim_generator_v1'").fetchone()["id"]
    for aid, p in PROFILES.items():
        # only generate history for astronauts that have none yet (keeps re-runs idempotent)
        if conn.execute("SELECT 1 FROM measurements WHERE astronaut_id=? AND source_id=? LIMIT 1", (aid, sim_id)).fetchone():
            continue
        rnd = random.Random(p["seed"])
        rows = []
        for d in range(days, 0, -1):
            t = (now - timedelta(days=d)).replace(hour=7).strftime("%Y-%m-%dT%H:%M:%SZ")
            rows += [
                dict(indicator_code="sleep_hours",   value=round(rnd.uniform(*p["sleep"]), 1), unit="hours", measured_at=t),
                dict(indicator_code="heart_rate",    value=rnd.randint(*p["hr"]),              unit="bpm",   measured_at=t),
                dict(indicator_code="spo2",          value=rnd.randint(*p["spo2"]),            unit="%",     measured_at=t),
                dict(indicator_code="hydration_pct", value=rnd.randint(*p["hyd"]),             unit="%",     measured_at=t),
                dict(indicator_code="steps",         value=rnd.randint(*p["steps"]),           unit="steps", measured_at=t),
                dict(indicator_code="body_temp",     value=round(rnd.uniform(*p["temp"]), 1),  unit="°C",    measured_at=t),
            ]
        db.add_measurements(conn, aid, "sim_generator_v1", rows)

if __name__ == "__main__":
    c = db.connect(); db.init(c); seed(c)
    print("seeded", db.DB_PATH)
    for a in ASTRONAUTS: print(f"  id {a[0]}: {a[1]}")

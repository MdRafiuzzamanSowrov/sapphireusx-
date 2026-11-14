"""
Simulated astronaut vital-signs generator (Task 1 sample data).

ALL VALUES ARE SIMULATED. Nothing here is measured from a real person and
nothing here comes from NASA OSD-575. The numbers are generated to look
realistic so the dashboard, backend and analysis module can be tested.

Output files (written next to this script):
  simulated_vitals_long.csv           one row per reading (long format)
  simulated_vitals_daily_summary.csv  one row per crew member per day
  planted_events.csv                  answer key: every planted case and what the app should do
  daily_schedule.csv                  exact sleep and exercise times per person per day

Version 2: adds the context column (asleep / exercise / recovery / awake) and the
quality_status column to the long file.
Version 3: quality_status is now valid / missing / invalid; adds invalid-measurement
test cases, daily_schedule.csv, and category + expected_behaviour columns in the key.
The health values and the 9 original events are unchanged from version 2.

Run:  python generate_simulated_vitals.py
"""
import numpy as np
import pandas as pd

SEED = 575
DAYS = 14
START = pd.Timestamp("2026-11-01T00:00:00")
NOTE = "sim_seed575"
rng = np.random.default_rng(SEED)

CREW = {
    "DEMO-01": dict(hr=58, hrv=46, sys=112, dia=72, mass=68.0),
    "DEMO-02": dict(hr=64, hrv=38, sys=118, dia=76, mass=81.5),
    "DEMO-03": dict(hr=61, hrv=52, sys=121, dia=78, mass=74.2),
    "DEMO-04": dict(hr=67, hrv=41, sys=115, dia=74, mass=59.8),
}
SYMPTOMS = ["headache", "nausea", "vision_change", "back_pain"]

rows, daily_rows, events, schedule = [], [], [], []

def add(pid, ts, indicator, values, unit, method, context="not_applicable", quality="valid"):
    rows.append(pd.DataFrame({
        "participant_id": pid, "timestamp": ts, "indicator": indicator,
        "value": values, "unit": unit, "context": context, "quality_status": quality,
        "data_origin": "SIMULATED", "collection_method": method, "source_note": NOTE}))

def event(pid, start, end, indicators, description,
          category="health_event", expected="alert"):
    events.append(dict(participant_id=pid, start=start, end=end, category=category,
                       expected_behaviour=expected, indicators=indicators,
                       description=description, data_origin="SIMULATED"))

def ar1(n, sigma, phi=0.9):
    e = rng.normal(0, sigma * np.sqrt(1 - phi**2), n)
    out = np.zeros(n)
    for i in range(1, n):
        out[i] = phi * out[i-1] + e[i]
    return out

for pid, p in CREW.items():
    d = np.arange(1, DAYS + 1)
    # ---------- daily values (normal) ----------
    sleep_h = np.clip(rng.normal(6.3, 0.45, DAYS), 5.2, 7.5)
    exercise = np.clip(rng.normal(120, 14, DAYS), 85, 150).round()
    water = np.clip(rng.normal(2.4, 0.25, DAYS), 1.8, 3.1)
    rad_daily = np.clip(rng.normal(0.60, 0.07, DAYS), 0.4, 0.8)
    stress = rng.choice([1, 2, 3], DAYS, p=[0.35, 0.5, 0.15]).astype(float)
    fatigue = rng.choice([1, 2, 3], DAYS, p=[0.3, 0.5, 0.2]).astype(float)
    sym = {s: (rng.random(DAYS) < 0.03).astype(int) for s in SYMPTOMS}
    bp_shift = np.zeros(DAYS)
    hr_shift_day = np.zeros(DAYS)
    hrv_shift_day = np.zeros(DAYS)

    # ---------- planted multi-day events ----------
    if pid == "DEMO-01":      # poor sleep, mission days 5-7
        sleep_h[4:7] = [4.1, 3.6, 4.4]
        fatigue[4:7] = [4, 5, 4]; stress[4:7] = [3, 4, 4]
        hr_shift_day[4:7] = 8; hrv_shift_day[4:7] = -12
        event(pid, START + pd.Timedelta(days=4), START + pd.Timedelta(days=7),
              "sleep_duration;sleep_quality;fatigue_score;heart_rate;heart_rate_variability",
              "Three nights of short sleep (about 4 h). Fatigue up, resting heart rate up, HRV down.")
    if pid == "DEMO-02":      # early-mission nausea, days 2-3
        sym["nausea"][1:3] = 1
        exercise[8] = 0          # no exercise on the fever day (mission day 9)
        event(pid, START + pd.Timedelta(days=1), START + pd.Timedelta(days=3),
              "symptom_nausea", "Nausea reported on mission days 2 and 3 (early-mission motion sickness pattern).")
    if pid == "DEMO-03":      # raised blood pressure, days 11-12
        bp_shift[10:12] = 28
        event(pid, START + pd.Timedelta(days=10), START + pd.Timedelta(days=12),
              "blood_pressure_systolic;blood_pressure_diastolic",
              "Blood pressure readings clearly above this person's baseline on mission days 11 and 12.")
    if pid == "DEMO-04":      # missed exercise days 6-8, low water + headache day 10
        exercise[5:8] = [15, 0, 20]
        water[9] = 0.9; sym["headache"][9] = 1
        event(pid, START + pd.Timedelta(days=5), START + pd.Timedelta(days=8),
              "exercise_time", "Exercise almost skipped for three days (0 to 20 min/day).")
        event(pid, START + pd.Timedelta(days=9), START + pd.Timedelta(days=10),
              "water_intake;symptom_headache", "Very low water intake (0.9 L) with a headache reported.")

    sleep_q = np.clip(np.round((sleep_h - 3.2) * 1.25 + rng.normal(0, 0.4, DAYS)), 1, 5)
    rad_cum = np.cumsum(rad_daily)

    # ---------- sleep and exercise windows ----------
    # sleep for mission day k ends on the morning of day k
    sleep_iv, ex_iv = [], []
    for k in range(DAYS):
        wake = START + pd.Timedelta(days=k, minutes=int(round((5.5 + rng.normal(0, 0.3)) * 60)))
        sleep_iv.append((wake - pd.Timedelta(minutes=int(round(sleep_h[k] * 60))), wake))
        if exercise[k] > 0:
            s = START + pd.Timedelta(days=k, minutes=int(round((14 + rng.normal(0, 0.5)) * 60)))
            ex_iv.append((s, s + pd.Timedelta(minutes=int(exercise[k]))))

    ex_by_day = {a.normalize(): (a, b) for a, b in ex_iv}
    for k in range(DAYS):
        day0 = START + pd.Timedelta(days=k)
        ex = ex_by_day.get(day0)
        schedule.append(dict(participant_id=pid, mission_day=k + 1,
                             sleep_start=sleep_iv[k][0], sleep_end=sleep_iv[k][1],
                             exercise_start=ex[0] if ex else pd.NaT,
                             exercise_end=ex[1] if ex else pd.NaT,
                             recovery_end=(ex[1] + pd.Timedelta(minutes=20)) if ex else pd.NaT))

    # ---------- minute grid ----------
    t = pd.date_range(START, periods=DAYS * 1440, freq="1min")
    n = len(t)
    day_idx = (np.arange(n) // 1440)
    asleep = np.zeros(n, bool)
    for a, b in sleep_iv:
        asleep |= np.asarray((t >= a) & (t < b))
    ex_mask = np.zeros(n, bool); rec_mask = np.zeros(n, bool)
    ex_level = np.zeros(n)                     # 0..1 effort, with ramp and recovery
    for a, b in ex_iv:
        i0, i1 = t.searchsorted(a), t.searchsorted(b)
        effort = rng.uniform(0.85, 1.0)
        ex_mask[i0:min(i1, n)] = True
        rec_mask[i1:min(i1 + 20, n)] = True
        for i in range(i0, min(i1, n)):
            ex_level[i] = effort * min(1.0, (i - i0 + 1) / 6)
        for i in range(i1, min(i1 + 45, n)):
            ex_level[i] = max(ex_level[i], effort * np.exp(-(i - i1 + 1) / 8))
    minute = np.asarray(t.minute)
    hour = np.asarray(t.hour) + minute / 60
    circ = np.sin((hour - 11) / 24 * 2 * np.pi)   # peaks around 17:00

    hr = (p["hr"] + hr_shift_day[day_idx] - 7 * asleep + 2.5 * circ
          + 68 * ex_level + ar1(n, 2.5))
    hrv = (p["hrv"] + hrv_shift_day[day_idx] + 16 * asleep - 30 * ex_level + ar1(n, 6.0, 0.8))
    spo2 = 97.6 + ar1(n, 0.7, 0.8)
    rr = 15.0 - 2.0 * asleep + 15 * ex_level + ar1(n, 1.1, 0.8)
    temp = 36.75 + 0.30 * circ + 0.5 * ex_level + ar1(n, 0.07, 0.95)

    # ---------- planted short events ----------
    if pid == "DEMO-02":      # fever-like episode, day 9
        a = START + pd.Timedelta(days=8, hours=6); b = a + pd.Timedelta(hours=20)
        m = np.asarray((t >= a) & (t < b))
        shape = np.sin(np.linspace(0, np.pi, m.sum()))
        temp[m] += 1.5 * shape; hr[m] += 16 * shape; rr[m] += 4 * shape
        sym["headache"][8] = 1; fatigue[8] = 4
        event(pid, a, b, "body_temperature;heart_rate;respiratory_rate;symptom_headache;fatigue_score;exercise_time",
              "Fever-like episode: temperature climbs to about 38.5 C, with heart rate and breathing rate also up. Headache reported, no exercise that day.")
    if pid == "DEMO-03":      # oxygen dip, day 4
        a = START + pd.Timedelta(days=3, hours=10, minutes=20); b = a + pd.Timedelta(minutes=45)
        m = np.asarray((t >= a) & (t < b))
        spo2[m] -= 6.5; rr[m] += 5
        event(pid, a, b, "blood_oxygen_spo2;respiratory_rate",
              "Blood oxygen drops to about 90-92% for 45 minutes, breathing rate up.")
    if pid == "DEMO-04":      # fast heart rate at rest, day 3
        a = START + pd.Timedelta(days=2, hours=9, minutes=40); b = a + pd.Timedelta(minutes=25)
        m = np.asarray((t >= a) & (t < b))
        hr[m] += 62; hrv[m] -= 20
        event(pid, a, b, "heart_rate;heart_rate_variability",
              "Heart rate of about 125-135 bpm for 25 minutes while not exercising.")

    hr = np.clip(np.round(hr), 38, 190)
    hrv = np.clip(np.round(hrv), 8, 120)
    spo2 = np.clip(np.round(spo2), 80, 100)
    rr = np.clip(np.round(rr), 8, 40)
    temp = np.round(temp, 1)

    keep = np.ones(n, bool)
    if pid == "DEMO-01":      # sensor gap, day 10
        a = START + pd.Timedelta(days=9, hours=15); b = a + pd.Timedelta(hours=2)
        keep &= ~np.asarray((t >= a) & (t < b))
        event(pid, a, b, "heart_rate;heart_rate_variability;blood_oxygen_spo2;respiratory_rate;body_temperature",
              "Sensor gap: no wearable readings for 2 hours (rows have an empty value and quality_status = missing).",
              category="data_quality", expected="data-quality flag")

    # context of every minute: asleep / exercise / recovery (20 min after exercise) / awake
    ctx = np.where(asleep, "asleep", np.where(ex_mask, "exercise", np.where(rec_mask, "recovery", "awake")))
    def ctx_at(ts):
        return ctx[min(int((ts - START).total_seconds() // 60), n - 1)]
    # every scheduled reading gets a row; a dropout is a row with an empty value
    # and quality_status = "missing" (so a gap is different from "never scheduled")
    for ind, arr, unit, step in (("heart_rate", hr, "bpm", 1),
                                 ("heart_rate_variability", hrv, "ms", 5),
                                 ("blood_oxygen_spo2", spo2, "%", 5),
                                 ("respiratory_rate", rr, "breaths/min", 5),
                                 ("body_temperature", temp, "degC", 15)):
        sched = (minute % step == 0)
        vals = np.where(keep, arr, np.nan)[sched]
        add(pid, t[sched], ind, vals, unit, "sensor", ctx[sched],
            np.where(keep[sched], "valid", "missing"))

    # ---------- blood pressure, twice a day ----------
    bp = {}
    for k in range(DAYS):
        for tag, hh in (("am", 7.5), ("pm", 19.5)):
            ts = START + pd.Timedelta(days=k, hours=hh)
            s = round(p["sys"] + bp_shift[k] + rng.normal(0, 4))
            di = round(p["dia"] + bp_shift[k] * 0.6 + rng.normal(0, 3))
            bp[(k, tag)] = (s, di)
            add(pid, [ts], "blood_pressure_systolic", [s], "mmHg", "sensor", ctx_at(ts))
            add(pid, [ts], "blood_pressure_diastolic", [di], "mmHg", "sensor", ctx_at(ts))

    # ---------- daily entries ----------
    morning = [START + pd.Timedelta(days=k, hours=7) for k in range(DAYS)]
    evening = [START + pd.Timedelta(days=k, hours=21) for k in range(DAYS)]
    add(pid, morning, "sleep_duration", np.round(sleep_h, 1), "hours", "sensor")
    add(pid, morning, "sleep_quality", sleep_q, "score_1_to_5", "manual")
    add(pid, evening, "exercise_time", exercise, "min/day", "sensor")
    add(pid, evening, "water_intake", np.round(water, 1), "L/day", "manual")
    add(pid, evening, "radiation_dose_cumulative", np.round(rad_cum, 2), "mSv", "sensor")
    add(pid, evening, "stress_score", stress, "score_1_to_5", "manual")
    add(pid, evening, "fatigue_score", fatigue, "score_1_to_5", "manual")
    for s in SYMPTOMS:
        add(pid, evening, f"symptom_{s}", sym[s], "yes_no", "manual")
    mass_days = [0, 7]
    mass = [round(p["mass"] - 0.3 * (k / 7) + rng.normal(0, 0.1), 1) for k in mass_days]
    add(pid, [START + pd.Timedelta(days=k, hours=6.5) for k in mass_days],
        "body_mass", mass, "kg", "manual")

    # ---------- daily summary ----------
    for k in range(DAYS):
        dm = (day_idx == k) & keep
        daily_rows.append(dict(
            participant_id=pid, mission_day=k + 1,
            date=(START + pd.Timedelta(days=k)).date().isoformat(),
            hr_mean_bpm=round(hr[dm].mean(), 1), hr_min_bpm=int(hr[dm].min()), hr_max_bpm=int(hr[dm].max()),
            hr_sleep_mean_bpm=round(hr[dm & asleep].mean(), 1),
            hrv_mean_ms=round(hrv[dm & (minute % 5 == 0)].mean(), 1),
            spo2_mean_pct=round(spo2[dm & (minute % 5 == 0)].mean(), 1),
            spo2_min_pct=int(spo2[dm & (minute % 5 == 0)].min()),
            resp_rate_mean=round(rr[dm & (minute % 5 == 0)].mean(), 1),
            temp_mean_degC=round(temp[dm & (minute % 15 == 0)].mean(), 2),
            temp_max_degC=float(temp[dm & (minute % 15 == 0)].max()),
            bp_sys_am_mmHg=bp[(k, "am")][0], bp_dia_am_mmHg=bp[(k, "am")][1],
            bp_sys_pm_mmHg=bp[(k, "pm")][0], bp_dia_pm_mmHg=bp[(k, "pm")][1],
            sleep_duration_h=round(float(sleep_h[k]), 1), sleep_quality_1to5=int(sleep_q[k]),
            exercise_min=int(exercise[k]), sensor_missing_minutes=int(((day_idx == k) & ~keep).sum()), water_intake_L=round(float(water[k]), 1),
            radiation_cumulative_mSv=round(float(rad_cum[k]), 2),
            stress_score_1to5=int(stress[k]), fatigue_score_1to5=int(fatigue[k]),
            body_mass_kg=(mass[mass_days.index(k)] if k in mass_days else ""),
            **{f"symptom_{s}": int(sym[s][k]) for s in SYMPTOMS},
            data_origin="SIMULATED"))

long = pd.concat(rows, ignore_index=True)
long["timestamp"] = pd.to_datetime(long["timestamp"])

# ---------- invalid-measurement test cases (added after generation, no random draws) ----------
# These rows keep quality_status = "valid" on purpose (except the device-reported case):
# the device did not notice the problem, so the analysis code has to.
def at(day, hh, mm=0):
    return START + pd.Timedelta(days=day - 1, hours=hh, minutes=mm)
def sel(pid, ind, a, b):
    return ((long.participant_id == pid) & (long.indicator == ind)
            & (long.timestamp >= a) & (long.timestamp < b))
DQ = dict(category="data_quality", expected="data-quality flag")

m = sel("DEMO-02", "heart_rate", at(6, 11, 10), at(6, 11, 13)); long.loc[m, "value"] = 0
event("DEMO-02", at(6, 11, 10), at(6, 11, 13), "heart_rate",
      "Impossible value: heart rate reads 0 bpm for 3 readings. quality_status says valid.", **DQ)
m = sel("DEMO-01", "blood_oxygen_spo2", at(12, 9, 35), at(12, 9, 40)); long.loc[m, "value"] = 127
event("DEMO-01", at(12, 9, 35), at(12, 9, 40), "blood_oxygen_spo2",
      "Impossible value: SpO2 reads 127% for 1 reading (a percentage cannot exceed 100). quality_status says valid.", **DQ)
m = sel("DEMO-04", "respiratory_rate", at(12, 8, 20), at(12, 8, 25)); long.loc[m, "value"] = -1
event("DEMO-04", at(12, 8, 20), at(12, 8, 25), "respiratory_rate",
      "Impossible value: breathing rate reads -1 for 1 reading. quality_status says valid.", **DQ)
m = sel("DEMO-03", "heart_rate", at(9, 8, 0), at(9, 9, 30)); long.loc[m, "value"] = 71
event("DEMO-03", at(9, 8, 0), at(9, 9, 30), "heart_rate",
      "Flat-lined sensor: heart rate stuck at exactly 71 bpm for 90 minutes. The value is in the normal band, only the zero variation gives it away. quality_status says valid.", **DQ)
m = sel("DEMO-02", "heart_rate", at(12, 10, 0), at(12, 10, 10))
long = pd.concat([long, long[m]], ignore_index=True)
event("DEMO-02", at(12, 10, 0), at(12, 10, 10), "heart_rate",
      "Duplicates: the 10 heart-rate rows in this window appear twice (same timestamp and value).", **DQ)
m = sel("DEMO-04", "blood_oxygen_spo2", at(13, 7, 0), at(13, 7, 30))
long.loc[m, "value"] = [84, 81, 86, 83, 82, 85]; long.loc[m, "quality_status"] = "invalid"
event("DEMO-04", at(13, 7, 0), at(13, 7, 30), "blood_oxygen_spo2",
      "Device-reported bad signal: 6 SpO2 readings of 81-86% with quality_status = invalid. The values look alarming but must not raise a health alert.", **DQ)
m = sel("DEMO-01", "stress_score", at(13, 21, 0), at(13, 21, 1)); long.loc[m, "value"] = 9
event("DEMO-01", at(13, 21, 0), at(13, 21, 1), "stress_score",
      "Out-of-scale manual entry: stress score of 9 on a 1-to-5 scale. quality_status says valid.", **DQ)

# ---------- cases that should NOT alert, and the background symptoms ----------
END = START + pd.Timedelta(days=DAYS)
event("ALL", START, END, "heart_rate;heart_rate_variability;respiratory_rate;body_temperature",
      "Daily exercise and recovery windows (exact times in daily_schedule.csv, context = exercise or recovery). Heart rate climbs to as much as about 142 bpm and breathing rate to about 32. Normal response to exercise.",
      category="normal_should_not_alert", expected="no alert")
event("ALL", START, END, "heart_rate",
      "Sleep periods (exact times in daily_schedule.csv, context = asleep). Heart rate can drop to 40-50 bpm while asleep, which is normal for these demo crew.",
      category="normal_should_not_alert", expected="no alert")
event("DEMO-02", at(5, 0), at(6, 0), "symptom_vision_change",
      "Isolated vision-change report on mission day 5. Random background report, not part of a planted episode.",
      category="background_symptom")
event("DEMO-03", at(8, 0), at(9, 0), "symptom_headache",
      "Isolated headache report on mission day 8. Random background report, not part of a planted episode.",
      category="background_symptom")

long["timestamp"] = long["timestamp"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
long = long.sort_values(["participant_id", "timestamp", "indicator"], kind="stable")
long.to_csv("simulated_vitals_long.csv", index=False)
pd.DataFrame(daily_rows).to_csv("simulated_vitals_daily_summary.csv", index=False)
ev = pd.DataFrame(events)
ev["_order"] = ev.category.map({"health_event": 0, "background_symptom": 1,
                                "data_quality": 2, "normal_should_not_alert": 3})
ev = ev.sort_values(["_order", "start", "participant_id"]).drop(columns="_order").reset_index(drop=True)
ev.insert(0, "event_id", [f"E{i+1:02d}" for i in range(len(ev))])
for c in ("start", "end"):
    ev[c] = pd.to_datetime(ev[c]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
ev.to_csv("planted_events.csv", index=False)
sch = pd.DataFrame(schedule)
for c in ("sleep_start", "sleep_end", "exercise_start", "exercise_end", "recovery_end"):
    sch[c] = pd.to_datetime(sch[c]).dt.strftime("%Y-%m-%dT%H:%M:%SZ")
sch.to_csv("daily_schedule.csv", index=False)
print(len(long), "readings;", len(daily_rows), "daily rows;", len(ev), "planted events")

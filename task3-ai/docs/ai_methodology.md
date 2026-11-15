# AI methodology (living document)

## 1. Scope and non-goals
Explainable monitoring of health measurements against personal baselines. No diagnosis, no treatment advice,
no claim of clinical validity or model accuracy.

## 2. Pipeline
load -> data-quality layer -> preprocessing -> personal baseline -> detectors -> alert policy -> JSON.

## 3. Data-quality layer (implemented: `ai/validator.py`)
Quality problems are **not** health alerts. Each row receives a `quality_status` and reason codes.

| Reason code | Meaning | Resulting status |
|---|---|---|
| `device_missing` / `empty_value` | scheduled reading not delivered | missing |
| `device_invalid` | device itself marked the reading bad | invalid |
| `impossible_value` | outside physically possible range (e.g. HR 0, SpO2 127) | invalid |
| `out_of_scale` | whole-number scale or yes/no violated (e.g. stress 9 on 1-5) | invalid |
| `non_monotonic` | running total decreased | invalid |
| `unit_mismatch` / `unknown_metric` | contract violation | invalid |
| `flatline` | identical heart-rate value for >= 30 consecutive readings | suspect |
| `duplicate` / `duplicate_conflict` | same astronaut, metric and timestamp already present | duplicate |

Only rows with status `valid` may feed baselines and health detectors.

Threshold origin: validity rules come from Task 1 `metric_table.csv`. The flat-line length (30) was chosen from the
simulated data (longest legitimate run 10, planted fault 90) and **must be recalibrated on real sensor data**.

## 4. Preprocessing (implemented: `ai/preprocess.py`)
- Only rows with `quality_status == valid` are usable. All other rows are **kept aside, not deleted**, so they can be
  reported as data limitations (Task 1 file: 134,946 usable, 312 excluded).
- No resampling and no interpolation: filling gaps would invent measurements.
- `add_mission_day` labels each row with the mission day (1 = first UTC day).

## 5. Personal baseline (implemented: `ai/baseline.py`, settings in `ai/config/thresholds.yaml`)
**Idea.** A reading is compared with the same astronaut's *earlier valid* readings of the *same metric* in the
*same context* (awake, asleep, exercise, recovery). Heart rate in exercise is not compared with heart rate at rest.

| Step | Rule | Default | Why |
|---|---|---|---|
| Statistic | median and MAD (median absolute deviation) | n/a | resists a few unusual readings; no normality assumed |
| Window | the 7 days before the reading's hour | `lookback_days: 7` | recent behaviour, short enough for a 14-day mission |
| No peeking | window is strictly before the start of the reading's own hour | `as_of_step_minutes: 60` | the reading itself and anything later are never used |
| Minimum evidence | at least 20 readings (6 for blood pressure, 3 for once-a-day metrics) | `min_points` | tiny baselines are unreliable |
| Minimum span | the earlier readings must cover at least 24 h | `min_span_hours: 24` | avoids a baseline learned from a few hours of one circadian phase |
| Robust scale | `max(1.4826 x MAD, min_scale)` | floor = measurement resolution | rounded sensors repeat values, so MAD can be 0 |
| Not applicable | symptoms, body mass, cumulative radiation | `enabled: false` | binary reports, 2 points, running total |

Each reading carries `baseline_status` (`ok`, `insufficient_history`, `not_configured`), `baseline_median`,
`baseline_mad`, `baseline_scale`, `baseline_n` and `baseline_span_hours`, so the evidence can be shown with every alert.

**Result on the Task 1 file (SIMULATED DATA):** 124,289 usable readings have a ready baseline, 10,369 have
insufficient history, 288 are not configured. Every health-event window of a baseline-enabled continuous metric
(E02, E03, E06, E08) has a ready baseline. These numbers describe availability only; no detection claim is made yet.

**Verification.** Unit tests cover no-peeking, window length, minimum points and span, context separation, spike
resistance, the scale floor, unordered input and time zones. An independent brute-force recalculation on 300 random
readings matches. Deliberately breaking the code (own-hour leakage, no span rule, no scale floor) makes tests fail.

## 6. Remaining sections (to be written as components are built)
Detectors, alert policy and severity table, OSD-575 descriptive module, evaluation, JSON contract, limitations.

## 7. Known limitations (so far)
- 4 simulated crew, 14 days: tests the software only.
- Reference bands (NEWS2, AHA, AASM) are not validated for astronauts.
- Flat-line detection only covers heart rate; other sensors are too coarsely rounded in the simulated data.
- All baseline settings are **provisional design choices**, not validated on real astronaut data. The scale floors
  come from the rounding resolution seen in the simulated file.
- Unusual readings already inside the window can pull the baseline. A slow drift is partly absorbed by its own baseline.
- No time-of-day adjustment inside a context.
- Some baselines are statistically weak: once-a-day metrics have a baseline only from day 4 (from 3 earlier days), and
  the first 24 h of any astronaut have none. Body temperature in the short recovery context never reaches 20 readings
  (70 readings over the whole mission), so it has no baseline.

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

## 6. Rule-based screening and alert policy (`ai/detectors.py`)
Only `valid` readings are eligible. The detector applies the Task 1 reference bands and records the source,
source label, flag, and URL. Awake/resting heart-rate bands are not applied during exercise/recovery; respiratory
rate bands are limited to awake/asleep. A reported symptom is retained as a crew report for review. A band finding
is a monitoring priority, not a diagnosis.

| Source flag | Prototype display priority |
|---|---|
| watch | LOW |
| review | MEDIUM |
| urgent | HIGH |
| symptom report | MEDIUM |

This mapping is a software convention for review, not a clinical severity scale. Published thresholds were
developed for Earth populations or hospital settings and are not validated in microgravity. In addition, a valid
reading with a ready personal baseline can receive a LOW review priority when its robust z-score crosses the
provisional absolute threshold 3.5 in the metric's direction of concern. Exercise time uses a low direction because
it measures duration; a sustained unusually low duration is review-worthy. This threshold is a software screening
choice, not a medically validated cutoff, and may create false alerts. IsolationForest runs separately and cannot
set severity.
On the full SIMULATED DATA file, exercise/recovery readings for heart rate, respiratory rate, and temperature receive
no reference-band alerts; this behavior is covered by a targeted regression test.

## 7. Orchestration and OSD-575
`ai/analysis.py` connects loading, quality validation, usable-row selection, context-specific baseline attachment,
and reference-band screening. Screened rows carry baseline evidence when available; the JSON payload also includes
the source findings and prototype review alerts. It returns all screened measurements, baselined usable measurements,
and excluded rows separately. Data provenance labels accompany screened results. `analysis_to_payload()` returns
schema version 1.0 and validates it against the local proposed JSON Schema. `ai/backend_adapter.py` follows the
provided backend integration report for `POST /api/alerts`, maps LOW/MEDIUM/HIGH to watch/warning/critical, emits
one body per request, and creates stable globally unique external IDs. It maps four seeded indicator codes/units
(`sleep_duration`→`sleep_hours`, heart rate, SpO2, body temperature). For unseeded metrics it omits optional
`indicator_code` and puts the Task 3 metric and unit in `evidence`. Based on the backend seed code supplied for
integration, stable astronaut IDs are CDR-01=1 and DEMO-01..04=2..5; the adapter uses this map by default and
accepts an override for a different database. Live API execution remains untested because the backend service
code and database are not part of this workspace, and the local endpoint is not running.

`ai/osd575.py` is a separate descriptive module for the nine concentration columns in the cardiovascular Eve panel.
It reshapes 28 periodic lab samples into long form and reports counts, median, quartiles, minimum, and maximum.
It does not create vital-sign alerts, compare lab values to vital baselines, or interpret results clinically.
The assay ceiling considerations remain limitations; no censored-value correction is applied here. `ai/plots.py`
provides provenance-labelled OSD-575 summary and vital-series plotting helpers.

## 8. Optional experiment and remaining work
`ai/experimental.py` fits a separate one-feature IsolationForest per metric on valid simulated rows, with a fixed
seed and configurable contamination (default 2%). It compares anomaly flags with rows in planted health-event
windows and reports row-level recall and out-of-window flagged counts. This is a small synthetic-data experiment,
not validation; overlapping or long events affect row counts, and the planted event key is only an evaluation aid.
Its output is explicitly experimental and has no connection to alert severity. Backend JSON contract review and
empirical validation of thresholds remain future work. WESAD and BIDMC are out of MVP scope.

**Observed experiment (SIMULATED DATA, contamination 2%, seed 575):** 339 of 6,779 rows inside planted health-event
windows were flagged (row recall 5.0%); 1,994 flagged rows were outside those windows. This run shows weak agreement
with the planted answer key and does not support using IsolationForest as the primary detector. Row recall is not
event-level sensitivity, and flagged rows outside answer-key windows are not confirmed physiological false alarms.

**Rule detector evaluation (SIMULATED DATA, baseline robust-z threshold 3.5):** heart-rate baseline alerts are gated
to awake context, and respiratory-rate baseline alerts to awake/asleep; this prevents baseline deviations during
exercise, recovery, and sleep from creating inappropriate flags. All 10 expected alert windows (E01-E10, including
the two background symptoms) had at least one alert. The run produced 950 flagged measurement rows; 747 fall inside
expected windows and 203 fall outside. These are row counts, not deduplicated alert episodes; all 203 outside-window
rows are LOW priority (162 reference-band only, 30 baseline-only, 11 both). They need review and are not confirmed
clinical false positives. This evaluation reuses a small synthetic answer key and does not establish performance on
astronaut data.

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
- Alert priorities map source bands to LOW/MEDIUM/HIGH for a prototype UI; they are not clinical severity.
- Automated regression tests now cover the detector, JSON serialization, OSD-575, optional experiment, and plotting
  helpers; full-suite status is reported in the handoff.

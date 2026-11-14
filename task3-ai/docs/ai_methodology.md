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

## 4. Remaining sections (to be written as components are built)
Preprocessing, personal baseline (median/MAD per astronaut, metric, context), detectors, alert policy and severity
table, OSD-575 descriptive module, evaluation, JSON contract, limitations.

## 5. Known limitations (so far)
- 4 simulated crew, 14 days: tests the software only.
- Reference bands (NEWS2, AHA, AASM) are not validated for astronauts.
- Flat-line detection only covers heart rate; other sensors are too coarsely rounded in the simulated data.

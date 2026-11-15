# Astronaut Health Monitoring: Task 3 (AI & Health Analysis)

NASA Space Apps Challenge 2026, "Create Health Monitoring Software for Astronauts on Space Missions".

This repository contains the AI module. It analyses health measurements, compares them with personal
baselines, flags unusual patterns and returns **explainable, structured alerts** for the backend.

> **Not a medical device.** Alerts are prototype monitoring priorities (LOW / MEDIUM / HIGH) for review.
> The system does not diagnose and does not recommend treatment. Reference bands come from general-population
> or hospital guidance and are not validated for astronauts in microgravity.

## Data labels (always shown with every value)
- `SIMULATED DATA`: Task 1 vitals (4 demo crew, 14 days). Used for end-to-end tests only.
- `REAL NASA RESEARCH DATA`: OSD-575 serum biomarkers (4 participants, 28 samples). Periodic lab data, descriptive analysis only.
- `USER-ENTERED DATA`: values typed into the running app (none in the sample files).

## Pipeline
```
load (schema + unit checks) -> data-quality layer -> preprocessing -> personal baseline
  -> detectors (rules, robust z-score, optional IsolationForest) -> alert policy -> JSON
```
No LLM is used anywhere in the analysis path.

## Status
| Component | File | State |
|---|---|---|
| Loader + contract schema | `ai/loader.py`, `ai/schema.py` | done, tested |
| Config | `ai/config/thresholds.yaml`, `ai/config.py` | data-quality and baseline settings done; source alert bands in Task 1 data |
| Data-quality validator | `ai/validator.py` | done, tested against Task 1 answer key |
| Preprocessing + personal baseline | `ai/preprocess.py`, `ai/baseline.py` | done, tested (median/MAD per astronaut, metric, context; no peeking) |
| Reference-band screening + explainable findings | `ai/detectors.py` | implemented; rule-based, provisional |
| Pipeline entry point | `ai/analysis.py` | implemented; quality, baseline, screening |
| Proposed JSON output + local schema validation | `ai/analysis.py`, `ai/schema.py` | implemented; backend adapter follows integration report |
| Backend alert request adapter | `ai/backend_adapter.py` | four seeded indicator mappings; unseeded metrics go in evidence without indicator_code |
| OSD-575 cardiovascular descriptive module | `ai/osd575.py` | implemented; separate from vitals |
| IsolationForest comparison | `ai/experimental.py` | optional, experimental; never affects severity |
| Descriptive and vital-series charts | `ai/plots.py` | implemented as plotting helpers |

The prototype maps source flags as watch → LOW, review → MEDIUM, and urgent → HIGH.
Reported symptoms receive MEDIUM for review. These are not clinical severity judgments.
Exercise and recovery are excluded from awake/resting heart-rate and respiratory-rate bands.
An enabled personal baseline may add a LOW review finding at robust z ≥ 3.5 in the metric's concern direction;
this is provisional and not medically validated.
Invalid, missing, suspect, and duplicate rows never alert.

## Setup (Windows PowerShell)
```powershell
cd astro-health-ai
python -m venv .venv
.venv\Scripts\Activate.ps1        # prompt must now start with (.venv)
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
pytest
```
If activation is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then retry.
macOS/Linux: `source .venv/bin/activate`.

## Layout
```
ai/            Python package (loader, schema, validator, ...)
ai/config/     thresholds.yaml (rules, with sources and rationale)
ai/tests/      pytest tests
ai/notebooks/  exploration only (final logic lives in ai/*.py)
data/          inputs + provenance (see data/README.md)
docs/          ai_methodology.md, ai_tools_and_models.md
outputs/       generated results (git-ignored)
```

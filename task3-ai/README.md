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
| Config | `ai/config/thresholds.yaml`, `ai/config.py` | data-quality rules done; alert rules pending |
| Data-quality validator | `ai/validator.py` | done, tested against Task 1 answer key |
| Preprocessing, baseline, detectors, alerts, OSD-575 module, plots | | planned |

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

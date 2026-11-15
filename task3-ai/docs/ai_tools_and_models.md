# AI tools, libraries and models used

> Versions were read from `pip list` in the project virtual environment (Windows, Python 3.12.10)
> where 81 automated tests pass with pytest 9.2.0, including backend-adapter contract coverage.
> The exact full list is in `requirements-lock.txt`.
> Licenses are listed from memory and are **unverified**: confirm each on its PyPI page before submission.

## Libraries
| Tool | Version | Purpose | Why chosen | License (verify) | Where used |
|---|---|---|---|---|---|
| Python | 3.12.10 | Language | Same language as the backend | PSF | everywhere |
| pandas | 3.1.1 | Tables, rolling windows | Standard time-series handling | BSD-3 | loader, validator, baseline, detectors, OSD-575 |
| NumPy | 2.5.4 | Numeric arrays | pandas dependency, robust statistics | BSD-3 | validator, baseline |
| SciPy | 1.18.1 | Robust statistics (optional) | Only if a specific analysis needs it | BSD-3 | not used yet |
| scikit-learn | 1.9.1 | Optional IsolationForest experiment | Unsupervised anomaly detection | BSD-3 | `ai/experimental.py` (optional only) |
| matplotlib / seaborn | 3.11.2 / 0.13.2 | Plots | Standard plotting | PSF-style / BSD-3 | `ai/plots.py` uses matplotlib; seaborn unused |
| PyYAML | 6.0.3 | Config files | Human-readable thresholds | MIT | `ai/config.py` (done) |
| jsonschema | 4.26.0 | Validate JSON input/output | Catch malformed payloads at the boundary | MIT | validates proposed analysis envelope in `ai/schema.py`; backend approval pending |
| pytest | 9.2.0 | Unit tests | Standard test runner | MIT | `ai/tests/` (done) |
| Jupyter (metapackage; JupyterLab 4.6.6) | 1.1.1 | Exploration notebooks only | Final logic is in tested .py files | BSD-3 | not used yet |

Compatibility note: the code was developed against pandas 3.0.x and passes all tests on pandas 3.1.1.
`requirements.txt` allows pandas >= 2.2, but pandas 2.2.x has **not** been tested.

## Models
- No trained model is used in the current version. Screening uses reference-band rules; personal baselines are
  attached as contextual evidence, with no approved anomaly threshold yet.
- IsolationForest (scikit-learn) is an **optional, labelled-experimental comparison** in `ai/experimental.py`.
  It compares metric-wise anomaly flags with planted health-event rows on SIMULATED DATA. It must never set severity,
  and its score is not a disease probability. The recorded run found 5.0% row recall on planted event windows;
  see `docs/ai_methodology.md` for the counts and interpretation limits.

## LLM use
- No LLM is part of the analysis, thresholding, severity or explanation path.
- Development assistance: parts of this code and documentation were drafted with Claude (Anthropic), as previously
  recorded, and with OpenAI Codex during continuation work. Exact model versions, dates, and file-by-file contributions
  were not recorded; the project team should review generated changes before submission.

## Data sources
See `data/README.md`. Labels: REAL NASA RESEARCH DATA, SIMULATED DATA, USER-ENTERED DATA.

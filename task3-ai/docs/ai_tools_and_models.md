# AI tools, libraries and models used

> Versions were read from `pip list` in the project virtual environment (Windows, Python 3.12.10)
> where all 34 tests passed with pytest 9.2.0. The exact full list is in `requirements-lock.txt`.
> Licenses are listed from memory and are **unverified**: confirm each on its PyPI page before submission.

## Libraries
| Tool | Version | Purpose | Why chosen | License (verify) | Where used |
|---|---|---|---|---|---|
| Python | 3.12.10 | Language | Same language as the backend | PSF | everywhere |
| pandas | 3.1.1 | Tables, rolling windows | Standard time-series handling | BSD-3 | loader, validator (done); baseline (planned) |
| NumPy | 2.5.4 | Numeric arrays | pandas dependency, robust statistics | BSD-3 | validator (done); detectors (planned) |
| SciPy | 1.18.1 | Robust statistics (optional) | Only if a specific analysis needs it | BSD-3 | not used yet |
| scikit-learn | 1.9.1 | Optional IsolationForest experiment | Unsupervised anomaly detection | BSD-3 | not used yet (experiment only, planned) |
| matplotlib / seaborn | 3.11.2 / 0.13.2 | Plots | Standard plotting | PSF-style / BSD-3 | not used yet (visualisation, planned) |
| PyYAML | 6.0.3 | Config files | Human-readable thresholds | MIT | `ai/config.py` (done) |
| jsonschema | 4.26.0 | Validate JSON input/output | Enforce the backend contract | MIT | not used yet: `ai/schema.py` validates in plain Python; planned for alert-output validation |
| pytest | 9.2.0 | Unit tests | Standard test runner | MIT | `ai/tests/` (done) |
| Jupyter (metapackage; JupyterLab 4.6.6) | 1.1.1 | Exploration notebooks only | Final logic is in tested .py files | BSD-3 | not used yet |

Compatibility note: the code was developed against pandas 3.0.x and passes all tests on pandas 3.1.1.
`requirements.txt` allows pandas >= 2.2, but pandas 2.2.x has **not** been tested.

## Models
- No trained model is used in the current version. Detection is rule-based plus personal-baseline statistics.
- IsolationForest (scikit-learn) is planned only as an **optional, labelled-experimental comparison**.
  It must never set severity, and its score is not a disease probability.

## LLM use
- No LLM is part of the analysis, thresholding, severity or explanation path.
- Development assistance: parts of this code and documentation were drafted with an AI assistant
  (Claude, Anthropic) and reviewed by the team. **Team to confirm and complete:** exact model/version,
  dates, which files, and who reviewed them.

## Data sources
See `data/README.md`. Labels: REAL NASA RESEARCH DATA, SIMULATED DATA, USER-ENTERED DATA.
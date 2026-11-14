# AI tools, libraries and models used

> Versions below were read from the developer's terminal install log. After a clean virtual-environment
> install, regenerate with `pip freeze > requirements-lock.txt` and re-check this table.
> Licenses are listed from memory and are **unverified**: confirm each on its PyPI page before submission.

## Libraries
| Tool | Version (install log) | Purpose | Why chosen | License (verify) | Where used |
|---|---|---|---|---|---|
| Python | 3.12.10 | Language | Same language as the backend | PSF | everywhere |
| pandas | 2.2.2 | Tables, rolling windows | Standard time-series handling | BSD-3 | loader, validator, baseline |
| NumPy | see lock file | Numeric arrays | pandas dependency, robust statistics | BSD-3 | validator, detectors |
| SciPy | 1.17.1 | Robust statistics (optional) | Only if a specific analysis needs it | BSD-3 | detectors (planned) |
| scikit-learn | 1.9.0 | Optional IsolationForest experiment | Unsupervised anomaly detection | BSD-3 | experiment only (planned) |
| matplotlib / seaborn | 3.11.2 / 0.13.2 | Plots | Standard plotting | PSF-style / BSD-3 | viz (planned) |
| PyYAML | 6.0.3 | Config files | Human-readable thresholds | MIT | config |
| jsonschema | 4.26.0 | Validate JSON input/output | Enforce the backend contract | MIT | schema, tests |
| pytest | 8.3.2 | Unit tests | Standard test runner | MIT | tests |
| Jupyter | 1.1.1 | Exploration notebooks only | Final logic is in tested .py files | BSD-3 | notebooks |

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

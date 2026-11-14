"""Load and sanity-check ai/config/thresholds.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "thresholds.yaml"
_RULE_KEYS = {"min", "min_exclusive", "max", "integer_range", "allowed_values", "monotonic"}


class ConfigError(ValueError):
    """Raised when the configuration file is malformed."""


def load_config(path=None) -> dict:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    with open(path, encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    if not isinstance(cfg, dict) or not isinstance(cfg.get("metrics"), dict):
        raise ConfigError("config must contain a 'metrics' mapping")
    for code, m in cfg["metrics"].items():
        if code != code.upper():
            raise ConfigError(f"metric key must be UPPER CASE: {code}")
        if not isinstance(m, dict) or not m.get("unit"):
            raise ConfigError(f"{code}: 'unit' is required")
        validity = m.get("validity") or {}
        unknown = set(validity) - _RULE_KEYS
        if unknown:
            raise ConfigError(f"{code}: unknown validity rule(s) {sorted(unknown)}")
        run = m.get("flatline_min_run")
        if run is not None and (not isinstance(run, int) or run < 2):
            raise ConfigError(f"{code}: flatline_min_run must be an integer >= 2")
    return cfg

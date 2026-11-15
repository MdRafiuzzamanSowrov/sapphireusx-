"""Load and sanity-check ai/config/thresholds.yaml."""
from __future__ import annotations

from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config" / "thresholds.yaml"
_RULE_KEYS = {"min", "min_exclusive", "max", "integer_range", "allowed_values", "monotonic"}
_BASELINE_GLOBAL_KEYS = {"lookback_days", "as_of_step_minutes", "min_points", "min_span_hours"}
_BASELINE_METRIC_KEYS = {"enabled", "min_points", "min_scale", "min_span_hours"}


def _is_number(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _check_baseline_block(where: str, block: dict, allowed: set) -> None:
    unknown = set(block) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown baseline setting(s) {sorted(unknown)}")
    if "enabled" in block and not isinstance(block["enabled"], bool):
        raise ConfigError(f"{where}: enabled must be true or false")
    if "min_points" in block and not (isinstance(block["min_points"], int) and block["min_points"] >= 3):
        raise ConfigError(f"{where}: min_points must be an integer >= 3")
    for key in ("lookback_days", "min_scale"):
        if key in block and not (_is_number(block[key]) and block[key] > 0):
            raise ConfigError(f"{where}: {key} must be a number > 0")
    if "min_span_hours" in block and not (_is_number(block["min_span_hours"]) and block["min_span_hours"] >= 0):
        raise ConfigError(f"{where}: min_span_hours must be a number >= 0")
    if "as_of_step_minutes" in block:
        step = block["as_of_step_minutes"]
        if not (isinstance(step, int) and step > 0 and 1440 % step == 0):
            raise ConfigError(f"{where}: as_of_step_minutes must be a whole number of minutes that divides 1440")


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
        if m.get("baseline") is not None:
            if not isinstance(m["baseline"], dict):
                raise ConfigError(f"{code}: baseline must be a mapping")
            _check_baseline_block(code, m["baseline"], _BASELINE_METRIC_KEYS)
        run = m.get("flatline_min_run")
        if run is not None and (not isinstance(run, int) or run < 2):
            raise ConfigError(f"{code}: flatline_min_run must be an integer >= 2")
    if cfg.get("baseline") is not None:
        if not isinstance(cfg["baseline"], dict):
            raise ConfigError("'baseline' must be a mapping")
        _check_baseline_block("baseline", cfg["baseline"], _BASELINE_GLOBAL_KEYS)
    return cfg

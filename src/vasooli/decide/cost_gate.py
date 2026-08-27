"""
Loads config/channel_costs.yaml. Both the decide layer's voice cost gate and the report
layer's cost-per-recovered-rupee metric call `assumed_cost_inr()` from here — previously
these were two separate hardcoded constants in two different files that could silently
drift apart. Now there is exactly one number per channel, in exactly one file.
"""
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).parent.parent.parent.parent / "config" / "channel_costs.yaml"

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = yaml.safe_load(CONFIG_PATH.read_text())
    return _cache


def assumed_cost_inr(channel: str) -> float:
    return _load()["assumed_cost_inr"].get(channel, 0.0)

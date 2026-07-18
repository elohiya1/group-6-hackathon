from pathlib import Path

import yaml

CONFIG_PATH = Path(__file__).parent / "config" / "thresholds.yaml"


def _load() -> dict:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def get_conviction_threshold() -> float:
    return _load()["conviction_threshold"]


def get_screen_config() -> dict:
    return _load()["screen"]

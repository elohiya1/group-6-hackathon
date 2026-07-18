from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml

CONFIG_DIR = Path(__file__).parent / "config"


@dataclass
class AttributeConfig:
    name: str
    value_type: str
    temporal_behavior: str
    numeric_tolerance: Optional[float] = None
    recency_window_days: Optional[int] = None
    half_life_days: Optional[int] = None


def _load_yaml(filename: str) -> dict:
    with open(CONFIG_DIR / filename) as f:
        return yaml.safe_load(f)


def get_source_reliability(source_name: str) -> float:
    sources = _load_yaml("sources.yaml")
    if source_name not in sources:
        raise KeyError(f"Unknown source: {source_name}")
    return sources[source_name]


def get_attribute_config(attribute_name: str) -> AttributeConfig:
    attributes = _load_yaml("attributes.yaml")
    if attribute_name not in attributes:
        raise KeyError(f"Unknown attribute: {attribute_name}")
    raw = attributes[attribute_name]
    return AttributeConfig(
        name=attribute_name,
        value_type=raw["value_type"],
        temporal_behavior=raw["temporal_behavior"],
        numeric_tolerance=raw.get("numeric_tolerance"),
        recency_window_days=raw.get("recency_window_days"),
        half_life_days=raw.get("half_life_days"),
    )

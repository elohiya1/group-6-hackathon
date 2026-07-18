from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List

import yaml

CONFIG_DIR = Path(__file__).parent / "config" / "source_mappings"


@dataclass
class IdentifierRule:
    raw_field: str
    identifier_type: str


@dataclass
class AttributeRule:
    raw_field: str
    attribute_name: str


@dataclass
class SourceMapping:
    identifiers: List[IdentifierRule] = field(default_factory=list)
    attributes: List[AttributeRule] = field(default_factory=list)


def load_source_mapping(source_name: str) -> SourceMapping:
    path = CONFIG_DIR / f"{source_name}.yaml"
    if not path.exists():
        raise KeyError(f"No source mapping config for source: {source_name}")
    with open(path) as f:
        raw = yaml.safe_load(f)
    identifiers = [IdentifierRule(**i) for i in raw.get("identifiers", [])]
    attributes = [AttributeRule(**a) for a in raw.get("attributes", [])]
    return SourceMapping(identifiers=identifiers, attributes=attributes)


def extract_field(payload: dict, dotted_path: str) -> Any:
    value: Any = payload
    for part in dotted_path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value

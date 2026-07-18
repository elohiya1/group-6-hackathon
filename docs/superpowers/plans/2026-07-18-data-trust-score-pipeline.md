# Data Ingestion, Trust Score & Founder Score Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Memory layer's data processing pipeline — ingest raw per-source blobs, resolve them to founder/company entities, normalize attributes, compute a per-claim Trust Score (with cold-start and time-decay handling), and compute a persistent per-person Founder Score — all queryable from local SQLite.

**Architecture:** A Python package (`memory_layer/`) with one file per responsibility (schema, config loading, source mapping, entity resolution, normalization, trust scoring, founder scoring, pipeline orchestration, CLI, read-only query interface). Raw JSON files dropped into `data/incoming/<source>/` are the only external input; everything else is deterministic, config-driven Python against a local SQLite file.

**Tech Stack:** Python 3.10+, stdlib `sqlite3`, PyYAML for config, pytest for tests.

**Spec:** `docs/superpowers/specs/2026-07-18-data-trust-score-pipeline-design.md`

## Global Constraints

- Storage is a local SQLite file — no network service, no Postgres/Supabase.
- Source reliability weights, agreement tolerances, canonical attribute mappings (`temporal_behavior`, `recency_window_days`, `half_life_days`), and Founder Score category weights all live in config files — never hardcoded in logic.
- Raw payloads are never discarded, even after normalization/scoring.
- Conflicting entity matches are never auto-merged — they're flagged `needs_review` and require the manual `resolve_entity()` path.
- Contradictions are never silently resolved — both conflicting values stay visible and a row is written to `contradictions`.
- A data point backed by exactly one source is tiered `insufficient_data`, distinct from `contradicted` — this is the cold-start requirement.
- Re-ingesting identical raw file content must not create duplicate `data_points` or inflate corroboration (idempotency via `content_hash`).
- Founder Score excludes signal categories with no data and renormalizes over the remainder — missing data is never scored as zero. `coverage` (e.g. `"2/5"`) is always stored alongside the score.
- `founder_score_history` is append-only — never overwritten.

---

## Task 1: Project Scaffolding & SQLite Schema

**Files:**
- Create: `pyproject.toml`
- Create: `requirements.txt`
- Create: `.gitignore` (append if it already has content)
- Create: `memory_layer/__init__.py`
- Create: `memory_layer/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Produces: `memory_layer.db.init_db(db_path: str) -> sqlite3.Connection` — creates all tables (if not present) on the given SQLite path (`":memory:"` for tests) with `PRAGMA foreign_keys = ON`, returns the open connection.

- [ ] **Step 1: Create project scaffolding files**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

`requirements.txt`:
```
pyyaml>=6.0
pytest>=7.4
```

`.gitignore` (create, or append these lines if the file exists):
```
__pycache__/
*.pyc
.pytest_cache/
data/*.db
data/incoming/*/
data/processed/*/
!data/incoming/.gitkeep
!data/processed/.gitkeep
```

`memory_layer/__init__.py` (empty file).

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`

- [ ] **Step 3: Write the failing test**

`tests/test_db.py`:
```python
import sqlite3

import pytest

from memory_layer.db import init_db


EXPECTED_TABLES = {
    "sources",
    "entities",
    "entity_identifiers",
    "entity_relationships",
    "raw_records",
    "data_points",
    "contradictions",
    "founder_scores",
    "founder_score_history",
}


def test_init_db_creates_all_tables():
    conn = init_db(":memory:")
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(tables)


def test_foreign_keys_are_enforced():
    conn = init_db(":memory:")
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO entity_identifiers (entity_id, identifier_type, identifier_value) "
            "VALUES (?, ?, ?)",
            (999, "email", "nobody@example.com"),
        )


def test_init_db_is_idempotent():
    conn = init_db(":memory:")
    # Calling the schema script again on the same connection must not raise.
    from memory_layer.db import SCHEMA_SQL

    conn.executescript(SCHEMA_SQL)
```

- [ ] **Step 4: Run test to verify it fails**

Run: `pytest tests/test_db.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.db'`

- [ ] **Step 5: Write the implementation**

`memory_layer/db.py`:
```python
import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    reliability_weight REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS entities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL CHECK (type IN ('founder', 'company')),
    canonical_name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS entity_identifiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    identifier_type TEXT NOT NULL,
    identifier_value TEXT NOT NULL,
    UNIQUE(identifier_type, identifier_value)
);

CREATE TABLE IF NOT EXISTS entity_relationships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    founder_entity_id INTEGER NOT NULL REFERENCES entities(id),
    company_entity_id INTEGER NOT NULL REFERENCES entities(id),
    relationship TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS raw_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    entity_id INTEGER REFERENCES entities(id),
    raw_payload TEXT NOT NULL,
    content_hash TEXT UNIQUE NOT NULL,
    origin_file TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    resolution_status TEXT NOT NULL CHECK (
        resolution_status IN ('resolved', 'new_entity', 'needs_review')
    )
);

CREATE TABLE IF NOT EXISTS data_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    raw_record_id INTEGER NOT NULL REFERENCES raw_records(id),
    source_id INTEGER NOT NULL REFERENCES sources(id),
    attribute_name TEXT NOT NULL,
    value TEXT NOT NULL,
    value_type TEXT NOT NULL CHECK (value_type IN ('numeric', 'categorical', 'text')),
    observed_at TEXT,
    created_at TEXT NOT NULL,
    confidence_score REAL,
    confidence_tier TEXT CHECK (
        confidence_tier IN ('insufficient_data', 'corroborated', 'contradicted')
    )
);

CREATE TABLE IF NOT EXISTS contradictions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    attribute_name TEXT NOT NULL,
    data_point_id_a INTEGER NOT NULL REFERENCES data_points(id),
    data_point_id_b INTEGER NOT NULL REFERENCES data_points(id),
    detected_at TEXT NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS founder_scores (
    entity_id INTEGER PRIMARY KEY REFERENCES entities(id),
    score REAL NOT NULL,
    coverage TEXT NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS founder_score_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    score REAL NOT NULL,
    coverage TEXT NOT NULL,
    computed_at TEXT NOT NULL
);
"""


def init_db(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
```

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/test_db.py -v`
Expected: PASS (3 passed)

- [ ] **Step 7: Create data directories**

Run:
```bash
mkdir -p data/incoming data/processed
touch data/incoming/.gitkeep data/processed/.gitkeep
```

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml requirements.txt .gitignore memory_layer/__init__.py memory_layer/db.py tests/test_db.py data/incoming/.gitkeep data/processed/.gitkeep
git commit -m "feat: add SQLite schema and project scaffolding"
```

---

## Task 2: Config Loader — Source Reliability & Canonical Attributes

**Files:**
- Create: `memory_layer/config/sources.yaml`
- Create: `memory_layer/config/attributes.yaml`
- Create: `memory_layer/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: nothing (pure config layer)
- Produces:
  - `memory_layer.config.get_source_reliability(source_name: str) -> float`
  - `memory_layer.config.AttributeConfig` dataclass with fields `name: str`, `value_type: str`, `temporal_behavior: str`, `numeric_tolerance: Optional[float]`, `recency_window_days: Optional[int]`, `half_life_days: Optional[int]`
  - `memory_layer.config.get_attribute_config(attribute_name: str) -> AttributeConfig`

- [ ] **Step 1: Create the config YAML files**

`memory_layer/config/sources.yaml`:
```yaml
github: 0.9
arxiv: 0.9
patents: 0.85
crunchbase: 0.85
devpost: 0.7
producthunt: 0.7
hackernews: 0.75
tavily: 0.6
linkedin: 0.55
twitter: 0.5
university_challenge: 0.5
```

`memory_layer/config/attributes.yaml`:
```yaml
revenue:
  value_type: numeric
  temporal_behavior: decaying
  numeric_tolerance: 0.10
  recency_window_days: 90
  half_life_days: 180

user_count:
  value_type: numeric
  temporal_behavior: decaying
  numeric_tolerance: 0.10
  recency_window_days: 90
  half_life_days: 180

employee_count:
  value_type: numeric
  temporal_behavior: decaying
  numeric_tolerance: 0.10
  recency_window_days: 90
  half_life_days: 180

funding_raised:
  value_type: numeric
  temporal_behavior: decaying
  numeric_tolerance: 0.05
  recency_window_days: 180
  half_life_days: 365

github_stars:
  value_type: numeric
  temporal_behavior: decaying
  numeric_tolerance: 0.05
  recency_window_days: 30
  half_life_days: 90

job_title:
  value_type: categorical
  temporal_behavior: static

degree:
  value_type: categorical
  temporal_behavior: static

prior_company_founded:
  value_type: categorical
  temporal_behavior: static

patents_filed:
  value_type: numeric
  temporal_behavior: static
  numeric_tolerance: 0
```

- [ ] **Step 2: Write the failing test**

`tests/test_config.py`:
```python
import pytest

from memory_layer.config import get_attribute_config, get_source_reliability


def test_get_source_reliability_known():
    assert get_source_reliability("github") == 0.9


def test_get_source_reliability_unknown_raises():
    with pytest.raises(KeyError):
        get_source_reliability("not_a_real_source")


def test_get_attribute_config_decaying():
    cfg = get_attribute_config("github_stars")
    assert cfg.value_type == "numeric"
    assert cfg.temporal_behavior == "decaying"
    assert cfg.recency_window_days == 30
    assert cfg.half_life_days == 90
    assert cfg.numeric_tolerance == 0.05


def test_get_attribute_config_static():
    cfg = get_attribute_config("job_title")
    assert cfg.temporal_behavior == "static"
    assert cfg.recency_window_days is None
    assert cfg.half_life_days is None


def test_get_attribute_config_unknown_raises():
    with pytest.raises(KeyError):
        get_attribute_config("not_a_real_attribute")
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.config'`

- [ ] **Step 4: Write the implementation**

`memory_layer/config.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add memory_layer/config.py memory_layer/config/sources.yaml memory_layer/config/attributes.yaml tests/test_config.py
git commit -m "feat: add source reliability and canonical attribute config"
```

---

## Task 3: Source Mapping Config & Loader

**Files:**
- Create: `memory_layer/config/source_mappings/github.yaml`
- Create: `memory_layer/config/source_mappings/crunchbase.yaml`
- Create: `memory_layer/config/source_mappings/tavily.yaml`
- Create: `memory_layer/source_mappings.py`
- Test: `tests/test_source_mappings.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `memory_layer.source_mappings.IdentifierRule` dataclass (`raw_field: str`, `identifier_type: str`)
  - `memory_layer.source_mappings.AttributeRule` dataclass (`raw_field: str`, `attribute_name: str`)
  - `memory_layer.source_mappings.SourceMapping` dataclass (`identifiers: list[IdentifierRule]`, `attributes: list[AttributeRule]`)
  - `memory_layer.source_mappings.load_source_mapping(source_name: str) -> SourceMapping`
  - `memory_layer.source_mappings.extract_field(payload: dict, dotted_path: str) -> Any` — reads a nested field via `"a.b.c"` dot-path, returns `None` if any segment is missing

Field names for `crunchbase` and `tavily` below are illustrative — the real fetchers for those sources aren't built yet (out of scope per the spec), so exact upstream field names aren't known. The mapping *mechanism* is what matters here; update these two files once real fetcher payloads exist. `github.yaml` uses the real, stable GitHub REST API repository response shape.

- [ ] **Step 1: Create the source mapping YAML files**

`memory_layer/config/source_mappings/github.yaml`:
```yaml
identifiers:
  - raw_field: owner.login
    identifier_type: github_username
attributes:
  - raw_field: stargazers_count
    attribute_name: github_stars
```

`memory_layer/config/source_mappings/crunchbase.yaml`:
```yaml
identifiers:
  - raw_field: company_domain
    identifier_type: company_domain
attributes:
  - raw_field: employee_count
    attribute_name: employee_count
```

`memory_layer/config/source_mappings/tavily.yaml`:
```yaml
identifiers:
  - raw_field: company_domain
    identifier_type: company_domain
  - raw_field: contact_email
    identifier_type: email
attributes:
  - raw_field: employee_count
    attribute_name: employee_count
```

- [ ] **Step 2: Write the failing test**

`tests/test_source_mappings.py`:
```python
import pytest

from memory_layer.source_mappings import extract_field, load_source_mapping


def test_load_github_mapping():
    mapping = load_source_mapping("github")
    assert mapping.identifiers[0].raw_field == "owner.login"
    assert mapping.identifiers[0].identifier_type == "github_username"
    assert mapping.attributes[0].raw_field == "stargazers_count"
    assert mapping.attributes[0].attribute_name == "github_stars"


def test_load_tavily_mapping_has_two_identifiers():
    mapping = load_source_mapping("tavily")
    identifier_types = {i.identifier_type for i in mapping.identifiers}
    assert identifier_types == {"company_domain", "email"}


def test_load_unknown_source_raises():
    with pytest.raises(KeyError):
        load_source_mapping("not_a_real_source")


def test_extract_field_nested():
    payload = {"owner": {"login": "octocat"}, "stargazers_count": 1200}
    assert extract_field(payload, "owner.login") == "octocat"
    assert extract_field(payload, "stargazers_count") == 1200


def test_extract_field_missing_returns_none():
    payload = {"owner": {}}
    assert extract_field(payload, "owner.login") is None
    assert extract_field(payload, "nonexistent") is None
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_source_mappings.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.source_mappings'`

- [ ] **Step 4: Write the implementation**

`memory_layer/source_mappings.py`:
```python
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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_source_mappings.py -v`
Expected: PASS (5 passed)

- [ ] **Step 6: Commit**

```bash
git add memory_layer/source_mappings.py memory_layer/config/source_mappings/ tests/test_source_mappings.py
git commit -m "feat: add per-source field mapping config and loader"
```

---

## Task 4: Source Repository (`get_or_create_source`)

**Files:**
- Create: `memory_layer/sources_repo.py`
- Test: `tests/test_sources_repo.py`

**Interfaces:**
- Consumes: `memory_layer.db.init_db` (Task 1), `memory_layer.config.get_source_reliability` (Task 2)
- Produces: `memory_layer.sources_repo.get_or_create_source(conn: sqlite3.Connection, source_name: str) -> int` — returns the `sources.id`, inserting a row (using the configured reliability weight) the first time a source name is seen

- [ ] **Step 1: Write the failing test**

`tests/test_sources_repo.py`:
```python
from memory_layer.db import init_db
from memory_layer.sources_repo import get_or_create_source


def test_get_or_create_source_creates_once():
    conn = init_db(":memory:")
    id1 = get_or_create_source(conn, "github")
    id2 = get_or_create_source(conn, "github")
    assert id1 == id2
    row = conn.execute("SELECT COUNT(*) FROM sources WHERE name = 'github'").fetchone()
    assert row[0] == 1


def test_get_or_create_source_uses_configured_weight():
    conn = init_db(":memory:")
    source_id = get_or_create_source(conn, "github")
    row = conn.execute(
        "SELECT reliability_weight FROM sources WHERE id = ?", (source_id,)
    ).fetchone()
    assert row[0] == 0.9
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_sources_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.sources_repo'`

- [ ] **Step 3: Write the implementation**

`memory_layer/sources_repo.py`:
```python
import sqlite3

from .config import get_source_reliability


def get_or_create_source(conn: sqlite3.Connection, source_name: str) -> int:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (source_name,)).fetchone()
    if row:
        return row[0]
    weight = get_source_reliability(source_name)
    cursor = conn.execute(
        "INSERT INTO sources (name, reliability_weight) VALUES (?, ?)",
        (source_name, weight),
    )
    conn.commit()
    return cursor.lastrowid
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_sources_repo.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/sources_repo.py tests/test_sources_repo.py
git commit -m "feat: add get_or_create_source helper"
```

---

## Task 5: Entity Repository (create, add identifier, find by identifier)

**Files:**
- Create: `memory_layer/entities_repo.py`
- Test: `tests/test_entities_repo.py`

**Interfaces:**
- Consumes: `memory_layer.db.init_db` (Task 1)
- Produces:
  - `memory_layer.entities_repo.create_entity(conn, entity_type: str, canonical_name: str) -> int`
  - `memory_layer.entities_repo.add_identifier(conn, entity_id: int, identifier_type: str, identifier_value: str) -> None` (idempotent — inserting the same identifier twice is a no-op)
  - `memory_layer.entities_repo.find_entity_by_identifier(conn, identifier_type: str, identifier_value: str) -> Optional[int]`

- [ ] **Step 1: Write the failing test**

`tests/test_entities_repo.py`:
```python
from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity, find_entity_by_identifier


def test_create_entity_and_find_by_identifier():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    assert find_entity_by_identifier(conn, "github_username", "adalovelace") == entity_id


def test_find_entity_by_identifier_no_match_returns_none():
    conn = init_db(":memory:")
    assert find_entity_by_identifier(conn, "github_username", "nobody") is None


def test_add_identifier_is_idempotent():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    row = conn.execute("SELECT COUNT(*) FROM entity_identifiers").fetchone()
    assert row[0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_entities_repo.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.entities_repo'`

- [ ] **Step 3: Write the implementation**

`memory_layer/entities_repo.py`:
```python
import sqlite3
from datetime import datetime, timezone
from typing import Optional


def create_entity(conn: sqlite3.Connection, entity_type: str, canonical_name: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO entities (type, canonical_name, created_at) VALUES (?, ?, ?)",
        (entity_type, canonical_name, now),
    )
    conn.commit()
    return cursor.lastrowid


def add_identifier(
    conn: sqlite3.Connection, entity_id: int, identifier_type: str, identifier_value: str
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO entity_identifiers (entity_id, identifier_type, identifier_value) "
        "VALUES (?, ?, ?)",
        (entity_id, identifier_type, identifier_value),
    )
    conn.commit()


def find_entity_by_identifier(
    conn: sqlite3.Connection, identifier_type: str, identifier_value: str
) -> Optional[int]:
    row = conn.execute(
        "SELECT entity_id FROM entity_identifiers WHERE identifier_type = ? AND identifier_value = ?",
        (identifier_type, identifier_value),
    ).fetchone()
    return row[0] if row else None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_entities_repo.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/entities_repo.py tests/test_entities_repo.py
git commit -m "feat: add entity creation and identifier lookup"
```

---

## Task 6: Entity Resolution (`resolve_raw_record`)

**Files:**
- Create: `memory_layer/entity_resolution.py`
- Test: `tests/test_entity_resolution.py`

**Interfaces:**
- Consumes:
  - `memory_layer.entities_repo.{create_entity, add_identifier, find_entity_by_identifier}` (Task 5)
  - `memory_layer.source_mappings.{load_source_mapping, extract_field}` (Task 3)
  - `memory_layer.sources_repo.get_or_create_source` (Task 4)
- Produces: `memory_layer.entity_resolution.resolve_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> str` — returns one of `"resolved"`, `"new_entity"`, `"needs_review"`; updates `raw_records.entity_id` and `resolution_status` accordingly

- [ ] **Step 1: Write the failing test**

`tests/test_entity_resolution.py`:
```python
import json
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity
from memory_layer.entity_resolution import resolve_raw_record
from memory_layer.sources_repo import get_or_create_source


def _insert_raw_record(conn, source_name, payload, content_hash):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, 'test.json', ?, 'needs_review')",
        (source_id, json.dumps(payload), content_hash, now),
    )
    conn.commit()
    return cursor.lastrowid


def test_resolve_raw_record_creates_new_founder_entity():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash1")

    status = resolve_raw_record(conn, rr_id)

    assert status == "new_entity"
    entity_id, resolution_status = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert entity_id is not None
    assert resolution_status == "new_entity"
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "founder"


def test_resolve_raw_record_creates_new_company_entity():
    conn = init_db(":memory:")
    payload = {"name": "Acme Corp", "company_domain": "acme.com", "employee_count": 50}
    rr_id = _insert_raw_record(conn, "crunchbase", payload, "hash2")

    status = resolve_raw_record(conn, rr_id)

    assert status == "new_entity"
    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_resolve_raw_record_matches_existing_entity():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash3")

    status = resolve_raw_record(conn, rr_id)

    assert status == "resolved"
    row = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()
    assert row[0] == entity_id


def test_resolve_raw_record_conflicting_matches_needs_review():
    conn = init_db(":memory:")
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash4")

    status = resolve_raw_record(conn, rr_id)

    assert status == "needs_review"
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (None, "needs_review")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_entity_resolution.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.entity_resolution'`

- [ ] **Step 3: Write the implementation**

`memory_layer/entity_resolution.py`:
```python
import json
import sqlite3
from typing import List, Tuple, Union

from .entities_repo import add_identifier, create_entity, find_entity_by_identifier
from .source_mappings import extract_field, load_source_mapping


def _load_payload_and_source(conn: sqlite3.Connection, raw_record_id: int) -> Tuple[dict, str]:
    row = conn.execute(
        "SELECT raw_payload, source_id FROM raw_records WHERE id = ?", (raw_record_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No raw_record with id {raw_record_id}")
    raw_payload, source_id = row
    payload = json.loads(raw_payload)
    source_name = conn.execute("SELECT name FROM sources WHERE id = ?", (source_id,)).fetchone()[0]
    return payload, source_name


def _extract_identifiers(payload: dict, source_name: str) -> List[Tuple[str, str]]:
    mapping = load_source_mapping(source_name)
    extracted = []
    for rule in mapping.identifiers:
        value = extract_field(payload, rule.raw_field)
        if value is not None:
            extracted.append((rule.identifier_type, str(value)))
    return extracted


def _infer_entity_type(identifiers: List[Tuple[str, str]]) -> str:
    identifier_types = {t for t, _ in identifiers}
    return "company" if "company_domain" in identifier_types else "founder"


def resolve_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> str:
    payload, source_name = _load_payload_and_source(conn, raw_record_id)
    extracted = _extract_identifiers(payload, source_name)

    matched_entity_ids = set()
    for identifier_type, identifier_value in extracted:
        entity_id = find_entity_by_identifier(conn, identifier_type, identifier_value)
        if entity_id is not None:
            matched_entity_ids.add(entity_id)

    if len(matched_entity_ids) > 1:
        conn.execute(
            "UPDATE raw_records SET entity_id = NULL, resolution_status = 'needs_review' WHERE id = ?",
            (raw_record_id,),
        )
        conn.commit()
        return "needs_review"

    if len(matched_entity_ids) == 1:
        entity_id = matched_entity_ids.pop()
        status = "resolved"
    else:
        entity_type = _infer_entity_type(extracted)
        canonical_name = str(payload.get("name", "unknown"))
        entity_id = create_entity(conn, entity_type, canonical_name)
        status = "new_entity"

    for identifier_type, identifier_value in extracted:
        add_identifier(conn, entity_id, identifier_type, identifier_value)

    conn.execute(
        "UPDATE raw_records SET entity_id = ?, resolution_status = ? WHERE id = ?",
        (entity_id, status, raw_record_id),
    )
    conn.commit()
    return status
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_entity_resolution.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/entity_resolution.py tests/test_entity_resolution.py
git commit -m "feat: add deterministic entity resolution for raw records"
```

---

## Task 7: Manual `needs_review` Resolver (`resolve_entity`)

**Files:**
- Modify: `memory_layer/entity_resolution.py`
- Modify: `tests/test_entity_resolution.py`

**Interfaces:**
- Consumes: everything from Task 6, plus `_load_payload_and_source`, `_extract_identifiers`, `_infer_entity_type` (private helpers already in the same file)
- Produces: `memory_layer.entity_resolution.resolve_entity(conn: sqlite3.Connection, raw_record_id: int, decision: Union[int, str]) -> int` — `decision` is either an existing `entity_id` to merge into, or the literal string `"new"`. Raises `ValueError` if the record isn't currently `needs_review`. Returns the resolved `entity_id`.

- [ ] **Step 1: Add the failing test**

Append to `tests/test_entity_resolution.py`:
```python
import pytest

from memory_layer.entities_repo import find_entity_by_identifier
from memory_layer.entity_resolution import resolve_entity


def test_resolve_entity_merges_into_existing():
    conn = init_db(":memory:")
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-merge")
    resolve_raw_record(conn, rr_id)  # lands in needs_review

    resolved_entity_id = resolve_entity(conn, rr_id, decision=company)

    assert resolved_entity_id == company
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (company, "resolved")
    # The email identifier already belonged to `founder`, a different entity
    # never part of this decision — add_identifier's INSERT OR IGNORE leaves
    # it untouched rather than silently reassigning it. Identifiers only ever
    # move between entities through an explicit, dedicated action, never as
    # a side effect of resolving an unrelated record.
    assert find_entity_by_identifier(conn, "email", "grace@acme.com") == founder


def test_resolve_entity_as_new():
    conn = init_db(":memory:")
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    payload = {
        "name": "Acme West",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-new")
    resolve_raw_record(conn, rr_id)

    resolved_entity_id = resolve_entity(conn, rr_id, decision="new")

    assert resolved_entity_id not in (company, founder)
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (resolved_entity_id, "resolved")


def test_resolve_entity_rejects_non_pending_record():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "ada"}, "stargazers_count": 1}
    rr_id = _insert_raw_record(conn, "github", payload, "hash-x")
    resolve_raw_record(conn, rr_id)  # resolves to new_entity, not needs_review

    with pytest.raises(ValueError):
        resolve_entity(conn, rr_id, decision="new")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_entity_resolution.py -v`
Expected: FAIL with `ImportError: cannot import name 'resolve_entity'`

- [ ] **Step 3: Add the implementation**

Append to `memory_layer/entity_resolution.py`:
```python
def resolve_entity(conn: sqlite3.Connection, raw_record_id: int, decision: Union[int, str]) -> int:
    """Manually resolve a needs_review raw_record.

    decision: an existing entity_id (int) to merge this record into, or the
    literal string "new" to confirm it's genuinely a different person/company.
    """
    row = conn.execute(
        "SELECT resolution_status FROM raw_records WHERE id = ?", (raw_record_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No raw_record with id {raw_record_id}")
    if row[0] != "needs_review":
        raise ValueError(f"raw_record {raw_record_id} is not pending review (status={row[0]})")

    payload, source_name = _load_payload_and_source(conn, raw_record_id)
    extracted = _extract_identifiers(payload, source_name)

    if decision == "new":
        entity_type = _infer_entity_type(extracted)
        canonical_name = str(payload.get("name", "unknown"))
        entity_id = create_entity(conn, entity_type, canonical_name)
    else:
        entity_id = int(decision)

    for identifier_type, identifier_value in extracted:
        add_identifier(conn, entity_id, identifier_type, identifier_value)

    conn.execute(
        "UPDATE raw_records SET entity_id = ?, resolution_status = 'resolved' WHERE id = ?",
        (entity_id, raw_record_id),
    )
    conn.commit()
    return entity_id
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_entity_resolution.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/entity_resolution.py tests/test_entity_resolution.py
git commit -m "feat: add manual resolve_entity for needs_review records"
```

---

## Task 8: Attribute Normalization (promote to `data_points`)

**Files:**
- Create: `memory_layer/normalize.py`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes:
  - `memory_layer.source_mappings.{load_source_mapping, extract_field}` (Task 3)
  - `memory_layer.config.get_attribute_config` (Task 2)
- Produces: `memory_layer.normalize.normalize_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> int` — creates one `data_points` row per mapped attribute found in the payload (with `confidence_score`/`confidence_tier` left `NULL`, to be filled by Trust Score computation), returns the count created. Returns `0` and creates nothing if the record isn't yet resolved to an entity.

- [ ] **Step 1: Write the failing test**

`tests/test_normalize.py`:
```python
import json
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entity_resolution import resolve_raw_record
from memory_layer.normalize import normalize_raw_record
from memory_layer.sources_repo import get_or_create_source


def _insert_raw_record(conn, source_name, payload, content_hash, status="needs_review"):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, 'test.json', ?, ?)",
        (source_id, json.dumps(payload), content_hash, now, status),
    )
    conn.commit()
    return cursor.lastrowid


def test_normalize_creates_data_points_for_resolved_record():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash-norm-1")
    resolve_raw_record(conn, rr_id)

    count = normalize_raw_record(conn, rr_id)

    assert count == 1
    row = conn.execute(
        "SELECT attribute_name, value, value_type FROM data_points WHERE raw_record_id = ?",
        (rr_id,),
    ).fetchone()
    assert row == ("github_stars", "42", "numeric")


def test_normalize_skips_unresolved_record():
    conn = init_db(":memory:")
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-norm-2", status="needs_review")

    count = normalize_raw_record(conn, rr_id)

    assert count == 0
    remaining = conn.execute(
        "SELECT COUNT(*) FROM data_points WHERE raw_record_id = ?", (rr_id,)
    ).fetchone()[0]
    assert remaining == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_normalize.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.normalize'`

- [ ] **Step 3: Write the implementation**

`memory_layer/normalize.py`:
```python
import json
import sqlite3
from datetime import datetime, timezone

from .config import get_attribute_config
from .source_mappings import extract_field, load_source_mapping


def normalize_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> int:
    row = conn.execute(
        "SELECT raw_payload, source_id, entity_id, resolution_status FROM raw_records WHERE id = ?",
        (raw_record_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No raw_record with id {raw_record_id}")
    raw_payload, source_id, entity_id, resolution_status = row
    if resolution_status not in ("resolved", "new_entity") or entity_id is None:
        return 0

    payload = json.loads(raw_payload)
    source_name = conn.execute("SELECT name FROM sources WHERE id = ?", (source_id,)).fetchone()[0]
    mapping = load_source_mapping(source_name)

    observed_at = payload.get("observed_at")
    created_at = datetime.now(timezone.utc).isoformat()

    created_count = 0
    for rule in mapping.attributes:
        value = extract_field(payload, rule.raw_field)
        if value is None:
            continue
        attribute_config = get_attribute_config(rule.attribute_name)
        conn.execute(
            "INSERT INTO data_points "
            "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
            " observed_at, created_at, confidence_score, confidence_tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
            (
                entity_id,
                raw_record_id,
                source_id,
                rule.attribute_name,
                str(value),
                attribute_config.value_type,
                observed_at,
                created_at,
            ),
        )
        created_count += 1
    conn.commit()
    return created_count
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_normalize.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/normalize.py tests/test_normalize.py
git commit -m "feat: promote resolved raw records into normalized data points"
```

---

## Task 9: Trust Score Computation (tiers, static attributes)

**Files:**
- Create: `memory_layer/trust_score.py`
- Test: `tests/test_trust_score.py`

**Interfaces:**
- Consumes: `memory_layer.config.get_attribute_config` (Task 2)
- Produces: `memory_layer.trust_score.compute_trust_scores(conn: sqlite3.Connection, entity_id: int, attribute_name: str, now: Optional[datetime] = None) -> None` — recomputes `confidence_score`/`confidence_tier` for every `data_points` row in that `(entity_id, attribute_name)` group, and rewrites the `contradictions` rows for that group. Idempotent (safe to call repeatedly). The `now` parameter is used by Task 10's decay logic — accept it here even though this task's tests don't need it, to avoid changing the function signature later.

- [ ] **Step 1: Write the failing test**

`tests/test_trust_score.py`:
```python
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.sources_repo import get_or_create_source
from memory_layer.trust_score import compute_trust_scores


def _insert_data_point(conn, entity_id, source_name, attribute_name, value, value_type, observed_at=None):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, ?, '{}', ?, 'test.json', ?, 'resolved')",
        (source_id, entity_id, f"hash-{attribute_name}-{value}-{source_name}", now),
    )
    raw_record_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
        (entity_id, raw_record_id, source_id, attribute_name, value, value_type, observed_at, now),
    )
    conn.commit()


def test_single_source_is_insufficient_data():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    row = conn.execute(
        "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == "insufficient_data"


def test_agreeing_sources_are_corroborated():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "ceo", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["corroborated", "corroborated"]


def test_conflicting_sources_are_contradicted_and_recorded():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "CTO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["contradicted", "contradicted"]
    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ? AND attribute_name = 'job_title'",
        (entity_id,),
    ).fetchone()[0]
    assert contradiction_count == 1


def test_compute_trust_scores_is_idempotent():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "CTO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")
    compute_trust_scores(conn, entity_id, "job_title")

    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ? AND attribute_name = 'job_title'",
        (entity_id,),
    ).fetchone()[0]
    assert contradiction_count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trust_score.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.trust_score'`

- [ ] **Step 3: Write the implementation**

`memory_layer/trust_score.py`:
```python
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .config import get_attribute_config


def _values_agree(value_type: str, value_a: str, value_b: str, numeric_tolerance: float) -> bool:
    if value_type == "numeric":
        a, b = float(value_a), float(value_b)
        if a == 0 and b == 0:
            return True
        denominator = max(abs(a), abs(b))
        return abs(a - b) / denominator <= numeric_tolerance
    return value_a.strip().lower() == value_b.strip().lower()


def compute_trust_scores(
    conn: sqlite3.Connection,
    entity_id: int,
    attribute_name: str,
    now: Optional[datetime] = None,
) -> None:
    attribute_config = get_attribute_config(attribute_name)
    rows = conn.execute(
        "SELECT dp.id, dp.value, dp.observed_at, dp.created_at, s.reliability_weight "
        "FROM data_points dp JOIN sources s ON dp.source_id = s.id "
        "WHERE dp.entity_id = ? AND dp.attribute_name = ?",
        (entity_id, attribute_name),
    ).fetchall()

    if not rows:
        return

    conn.execute(
        "DELETE FROM contradictions WHERE entity_id = ? AND attribute_name = ?",
        (entity_id, attribute_name),
    )

    tolerance = attribute_config.numeric_tolerance or 0.0

    for dp_id, value, _observed_at, _created_at, reliability in rows:
        comparable = [other for other in rows if other[0] != dp_id]
        agreeing = [
            o for o in comparable if _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]
        conflicting = [
            o for o in comparable if not _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]

        if agreeing:
            reliabilities = [reliability] + [o[4] for o in agreeing]
            base_score = sum(reliabilities) / len(reliabilities)
            bonus = min(0.05 * len(agreeing), 0.2)
            score = min(base_score + bonus, 1.0)
            tier = "corroborated"
        elif conflicting:
            score = min([reliability] + [o[4] for o in conflicting])
            tier = "contradicted"
        else:
            score = reliability
            tier = "insufficient_data"

        conn.execute(
            "UPDATE data_points SET confidence_score = ?, confidence_tier = ? WHERE id = ?",
            (score, tier, dp_id),
        )

        for other in conflicting:
            if other[0] > dp_id:
                conn.execute(
                    "INSERT INTO contradictions "
                    "(entity_id, attribute_name, data_point_id_a, data_point_id_b, detected_at, description) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entity_id,
                        attribute_name,
                        dp_id,
                        other[0],
                        datetime.now(timezone.utc).isoformat(),
                        f"{attribute_name}: '{value}' conflicts with '{other[1]}'",
                    ),
                )

    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trust_score.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/trust_score.py tests/test_trust_score.py
git commit -m "feat: compute per-claim Trust Score tiers with contradiction detection"
```

---

## Task 10: Time Decay for `decaying` Attributes

**Files:**
- Modify: `memory_layer/trust_score.py`
- Modify: `tests/test_trust_score.py`

**Interfaces:**
- Consumes: same as Task 9
- Produces: same public signature as Task 9 (`compute_trust_scores`), now honoring `temporal_behavior == "decaying"` from `AttributeConfig` — comparisons for agreement/contradiction are restricted to a `recency_window_days` window, and `confidence_score` is scaled by an age-based decay factor using `half_life_days`. `static` attributes are unaffected.

- [ ] **Step 1: Add the failing tests**

Append to `tests/test_trust_score.py`:
```python
from datetime import timedelta

import pytest


def test_decaying_attribute_outside_window_is_not_a_contradiction():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    two_years_ago = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
    today = datetime.now(timezone.utc).isoformat()
    _insert_data_point(conn, entity_id, "crunchbase", "employee_count", "50", "numeric", observed_at=two_years_ago)
    _insert_data_point(conn, entity_id, "tavily", "employee_count", "500", "numeric", observed_at=today)

    compute_trust_scores(conn, entity_id, "employee_count")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["insufficient_data", "insufficient_data"]
    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert contradiction_count == 0


def test_decaying_attribute_within_window_still_detects_contradiction():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    now = datetime.now(timezone.utc)
    _insert_data_point(
        conn, entity_id, "crunchbase", "employee_count", "50", "numeric", observed_at=now.isoformat()
    )
    _insert_data_point(
        conn,
        entity_id,
        "tavily",
        "employee_count",
        "500",
        "numeric",
        observed_at=(now - timedelta(days=5)).isoformat(),
    )

    compute_trust_scores(conn, entity_id, "employee_count", now=now)

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["contradicted", "contradicted"]


def test_reliability_decays_with_age():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    now = datetime.now(timezone.utc)
    one_half_life_ago = now - timedelta(days=90)  # github_stars half_life_days == 90
    _insert_data_point(
        conn, entity_id, "github", "github_stars", "100", "numeric", observed_at=one_half_life_ago.isoformat()
    )

    compute_trust_scores(conn, entity_id, "github_stars", now=now)

    row = conn.execute(
        "SELECT confidence_score FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    # github reliability weight is 0.9; one half-life => ~0.45
    assert row[0] == pytest.approx(0.45, abs=0.01)


def test_static_attribute_ignores_age():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    now = datetime.now(timezone.utc)
    long_ago = (now - timedelta(days=3650)).isoformat()
    _insert_data_point(conn, entity_id, "patents", "patents_filed", "3", "numeric", observed_at=long_ago)

    compute_trust_scores(conn, entity_id, "patents_filed", now=now)

    row = conn.execute(
        "SELECT confidence_score, confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == pytest.approx(0.85)  # patents source reliability, undecayed
    assert row[1] == "insufficient_data"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_trust_score.py -v`
Expected: FAIL — `test_decaying_attribute_outside_window_is_not_a_contradiction` and related new tests fail because comparisons aren't yet windowed and reliability isn't yet decayed (e.g. the first new test will show `contradicted` tiers instead of `insufficient_data`).

- [ ] **Step 3: Replace the implementation**

Replace the full contents of `memory_layer/trust_score.py`:
```python
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .config import get_attribute_config


def _values_agree(value_type: str, value_a: str, value_b: str, numeric_tolerance: float) -> bool:
    if value_type == "numeric":
        a, b = float(value_a), float(value_b)
        if a == 0 and b == 0:
            return True
        denominator = max(abs(a), abs(b))
        return abs(a - b) / denominator <= numeric_tolerance
    return value_a.strip().lower() == value_b.strip().lower()


def _as_of(observed_at: Optional[str], created_at: str) -> datetime:
    raw = observed_at or created_at
    return datetime.fromisoformat(raw)


def _decay_factor(age_days: float, half_life_days: Optional[float]) -> float:
    if not half_life_days or half_life_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def compute_trust_scores(
    conn: sqlite3.Connection,
    entity_id: int,
    attribute_name: str,
    now: Optional[datetime] = None,
) -> None:
    """Recomputes confidence_score/confidence_tier for every data_point
    belonging to (entity_id, attribute_name), and rewrites any detected
    contradictions. Idempotent.

    For `decaying` attributes, two data points are only compared for
    agreement/contradiction if their as-of timestamps fall within
    `recency_window_days` of each other (older observations are treated as
    separate trend snapshots, not competing claims), and reliability is
    scaled down with age using `half_life_days`. `static` attributes ignore
    both rules entirely.
    """
    now = now or datetime.now(timezone.utc)
    attribute_config = get_attribute_config(attribute_name)
    rows = conn.execute(
        "SELECT dp.id, dp.value, dp.observed_at, dp.created_at, s.reliability_weight "
        "FROM data_points dp JOIN sources s ON dp.source_id = s.id "
        "WHERE dp.entity_id = ? AND dp.attribute_name = ?",
        (entity_id, attribute_name),
    ).fetchall()

    if not rows:
        return

    conn.execute(
        "DELETE FROM contradictions WHERE entity_id = ? AND attribute_name = ?",
        (entity_id, attribute_name),
    )

    tolerance = attribute_config.numeric_tolerance or 0.0
    is_decaying = attribute_config.temporal_behavior == "decaying"

    as_of = {r[0]: _as_of(r[2], r[3]) for r in rows}
    decayed_reliability = {}
    for dp_id, _value, _observed_at, _created_at, reliability in rows:
        age_days = max((now - as_of[dp_id]).total_seconds() / 86400, 0.0)
        decayed_reliability[dp_id] = (
            reliability * _decay_factor(age_days, attribute_config.half_life_days)
            if is_decaying
            else reliability
        )

    for dp_id, value, _observed_at, _created_at, _reliability in rows:
        comparable = [other for other in rows if other[0] != dp_id]
        if is_decaying:
            window = attribute_config.recency_window_days or 0
            comparable = [
                other
                for other in comparable
                if abs((as_of[dp_id] - as_of[other[0]]).total_seconds() / 86400) <= window
            ]

        agreeing = [
            o for o in comparable if _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]
        conflicting = [
            o for o in comparable if not _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]

        this_reliability = decayed_reliability[dp_id]

        if agreeing:
            reliabilities = [this_reliability] + [decayed_reliability[o[0]] for o in agreeing]
            base_score = sum(reliabilities) / len(reliabilities)
            bonus = min(0.05 * len(agreeing), 0.2)
            score = min(base_score + bonus, 1.0)
            tier = "corroborated"
        elif conflicting:
            score = min([this_reliability] + [decayed_reliability[o[0]] for o in conflicting])
            tier = "contradicted"
        else:
            score = this_reliability
            tier = "insufficient_data"

        conn.execute(
            "UPDATE data_points SET confidence_score = ?, confidence_tier = ? WHERE id = ?",
            (score, tier, dp_id),
        )

        for other in conflicting:
            if other[0] > dp_id:
                conn.execute(
                    "INSERT INTO contradictions "
                    "(entity_id, attribute_name, data_point_id_a, data_point_id_b, detected_at, description) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entity_id,
                        attribute_name,
                        dp_id,
                        other[0],
                        datetime.now(timezone.utc).isoformat(),
                        f"{attribute_name}: '{value}' conflicts with '{other[1]}'",
                    ),
                )

    conn.commit()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_trust_score.py -v`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add memory_layer/trust_score.py tests/test_trust_score.py
git commit -m "feat: add recency window and reliability decay for decaying attributes"
```

---

## Task 11: Founder Score Computation

**Files:**
- Create: `memory_layer/config/founder_score.yaml`
- Create: `memory_layer/founder_score.py`
- Test: `tests/test_founder_score.py`

**Interfaces:**
- Consumes: reads `data_points.confidence_score` directly (populated by Task 9/10's `compute_trust_scores`)
- Produces: `memory_layer.founder_score.compute_founder_score(conn: sqlite3.Connection, entity_id: int) -> float` — upserts `founder_scores`, appends a row to `founder_score_history`, returns the computed score

- [ ] **Step 1: Create the category config**

`memory_layer/config/founder_score.yaml`:
```yaml
technical_execution:
  weight: 0.4
  attributes: [github_stars]

track_record:
  weight: 0.35
  attributes: [patents_filed, prior_company_founded]

network:
  weight: 0.25
  attributes: [job_title, degree]
```

- [ ] **Step 2: Write the failing test**

`tests/test_founder_score.py`:
```python
import json
from datetime import datetime, timezone

import pytest

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.founder_score import compute_founder_score
from memory_layer.sources_repo import get_or_create_source


def _insert_scored_data_point(conn, entity_id, source_name, attribute_name, value, value_type, confidence_score):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, ?, '{}', ?, 'test.json', ?, 'resolved')",
        (source_id, entity_id, f"hash-{attribute_name}-{source_name}", now),
    )
    raw_record_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, 'corroborated')",
        (entity_id, raw_record_id, source_id, attribute_name, value, value_type, now, confidence_score),
    )
    conn.commit()


def test_founder_score_full_coverage():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "500", "numeric", 0.9)
    _insert_scored_data_point(conn, entity_id, "patents", "patents_filed", "2", "numeric", 0.85)
    _insert_scored_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical", 0.55)

    score = compute_founder_score(conn, entity_id)

    row = conn.execute(
        "SELECT score, coverage FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == pytest.approx(score)
    assert row[1] == "3/3"
    history_count = conn.execute(
        "SELECT COUNT(*) FROM founder_score_history WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert history_count == 1


def test_founder_score_renormalizes_missing_categories():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "First-Time Founder")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "10", "numeric", 0.9)

    score = compute_founder_score(conn, entity_id)

    row = conn.execute(
        "SELECT score, coverage FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[1] == "1/3"
    assert row[0] == pytest.approx(90.0)


def test_founder_score_history_appends_not_overwrites():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "10", "numeric", 0.5)
    compute_founder_score(conn, entity_id)
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "20", "numeric", 0.9)
    compute_founder_score(conn, entity_id)

    history_count = conn.execute(
        "SELECT COUNT(*) FROM founder_score_history WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert history_count == 2
    current_rows = conn.execute(
        "SELECT COUNT(*) FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert current_rows == 1
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_founder_score.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.founder_score'`

- [ ] **Step 4: Write the implementation**

`memory_layer/founder_score.py`:
```python
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

CONFIG_PATH = Path(__file__).parent / "config" / "founder_score.yaml"


def _load_categories() -> Dict[str, dict]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def compute_founder_score(conn: sqlite3.Connection, entity_id: int) -> float:
    """Recomputes the founder's score from their current data_points,
    renormalizing over whichever signal categories actually have data
    (missing categories are excluded, not zeroed), and appends a row to
    founder_score_history. Returns the computed score (0-100)."""
    categories = _load_categories()

    category_scores: List[Tuple[float, float]] = []  # (weight, avg_confidence * 100)
    for config in categories.values():
        attribute_names = config["attributes"]
        placeholders = ",".join("?" for _ in attribute_names)
        rows = conn.execute(
            f"SELECT confidence_score FROM data_points "
            f"WHERE entity_id = ? AND attribute_name IN ({placeholders}) "
            f"AND confidence_score IS NOT NULL",
            (entity_id, *attribute_names),
        ).fetchall()
        if not rows:
            continue
        avg_confidence = sum(r[0] for r in rows) / len(rows)
        category_scores.append((config["weight"], avg_confidence * 100))

    total_categories = len(categories)
    covered_categories = len(category_scores)

    if covered_categories == 0:
        score = 0.0
    else:
        total_weight = sum(w for w, _ in category_scores)
        score = sum(w * s for w, s in category_scores) / total_weight

    coverage = f"{covered_categories}/{total_categories}"
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO founder_scores (entity_id, score, coverage, computed_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(entity_id) DO UPDATE SET "
        "score = excluded.score, coverage = excluded.coverage, computed_at = excluded.computed_at",
        (entity_id, score, coverage, now),
    )
    conn.execute(
        "INSERT INTO founder_score_history (entity_id, score, coverage, computed_at) VALUES (?, ?, ?, ?)",
        (entity_id, score, coverage, now),
    )
    conn.commit()
    return score
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_founder_score.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add memory_layer/config/founder_score.yaml memory_layer/founder_score.py tests/test_founder_score.py
git commit -m "feat: compute persistent Founder Score with coverage-aware renormalization"
```

---

## Task 12: Pipeline Orchestration & CLI

**Files:**
- Create: `memory_layer/pipeline.py`
- Create: `memory_layer/cli.py`
- Test: `tests/test_pipeline.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `sources_repo.get_or_create_source` (Task 4), `entity_resolution.{resolve_raw_record, resolve_entity}` (Tasks 6-7), `normalize.normalize_raw_record` (Task 8), `trust_score.compute_trust_scores` (Tasks 9-10), `founder_score.compute_founder_score` (Task 11), `db.init_db` (Task 1)
- Produces:
  - `memory_layer.pipeline.ingest_file(conn, source_name: str, file_path: Path) -> Optional[int]` — returns the new `raw_record.id`, or `None` if this exact content was already ingested
  - `memory_layer.pipeline.run_pipeline(conn, incoming_dir: Path, processed_dir: Path) -> list[int]` — full ingest → resolve → normalize → score cycle over every `*.json` file under `incoming_dir/<source>/`; always moves processed files out of `incoming_dir` (whether newly ingested or a dedup skip); returns the list of newly-ingested `raw_record` ids
  - `memory_layer.cli.main() -> None` — argparse entrypoint with `run` and `resolve` subcommands

- [ ] **Step 1: Write the failing pipeline test**

`tests/test_pipeline.py`:
```python
import json

from memory_layer.db import init_db
from memory_layer.pipeline import run_pipeline


def test_end_to_end_pipeline_multi_source_founder(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)

    github_payload = {
        "name": "Ada Lovelace",
        "owner": {"login": "adalovelace"},
        "stargazers_count": 250,
    }
    (incoming / "github" / "repo1.json").write_text(json.dumps(github_payload))

    conn = init_db(":memory:")
    ingested = run_pipeline(conn, incoming, processed)

    assert len(ingested) == 1
    entity = conn.execute("SELECT id, type, canonical_name FROM entities").fetchone()
    assert entity[1] == "founder"
    assert entity[2] == "Ada Lovelace"

    data_point = conn.execute(
        "SELECT attribute_name, value, confidence_tier FROM data_points WHERE entity_id = ?",
        (entity[0],),
    ).fetchone()
    assert data_point == ("github_stars", "250", "insufficient_data")

    founder_score = conn.execute(
        "SELECT coverage FROM founder_scores WHERE entity_id = ?", (entity[0],)
    ).fetchone()
    assert founder_score[0] == "1/3"

    assert not (incoming / "github" / "repo1.json").exists()
    assert (processed / "github" / "repo1.json").exists()


def test_end_to_end_pipeline_idempotent_rerun(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    first_run = run_pipeline(conn, incoming, processed)
    assert len(first_run) == 1

    (incoming / "github").mkdir(parents=True, exist_ok=True)
    (incoming / "github" / "repo1_retry.json").write_text(json.dumps(payload))
    second_run = run_pipeline(conn, incoming, processed)

    assert len(second_run) == 0
    count = conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0]
    assert count == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.pipeline'`

- [ ] **Step 3: Write `pipeline.py`**

`memory_layer/pipeline.py`:
```python
import hashlib
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .entity_resolution import resolve_raw_record
from .founder_score import compute_founder_score
from .normalize import normalize_raw_record
from .sources_repo import get_or_create_source
from .trust_score import compute_trust_scores


def _content_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def ingest_file(conn: sqlite3.Connection, source_name: str, file_path: Path) -> Optional[int]:
    raw_bytes = file_path.read_bytes()
    content_hash = _content_hash(raw_bytes)

    existing = conn.execute(
        "SELECT id FROM raw_records WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if existing:
        return None

    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, ?, ?, 'needs_review')",
        (source_id, raw_bytes.decode("utf-8"), content_hash, str(file_path), now),
    )
    conn.commit()
    return cursor.lastrowid


def run_pipeline(conn: sqlite3.Connection, incoming_dir: Path, processed_dir: Path) -> List[int]:
    ingested_ids = []
    for source_dir in sorted(p for p in incoming_dir.iterdir() if p.is_dir()):
        source_name = source_dir.name
        for file_path in sorted(source_dir.glob("*.json")):
            raw_record_id = ingest_file(conn, source_name, file_path)

            if raw_record_id is not None:
                ingested_ids.append(raw_record_id)
                status = resolve_raw_record(conn, raw_record_id)
                if status in ("resolved", "new_entity"):
                    normalize_raw_record(conn, raw_record_id)
                    entity_id = conn.execute(
                        "SELECT entity_id FROM raw_records WHERE id = ?", (raw_record_id,)
                    ).fetchone()[0]
                    attribute_names = [
                        r[0]
                        for r in conn.execute(
                            "SELECT DISTINCT attribute_name FROM data_points WHERE raw_record_id = ?",
                            (raw_record_id,),
                        ).fetchall()
                    ]
                    for attribute_name in attribute_names:
                        compute_trust_scores(conn, entity_id, attribute_name)

                    entity_type = conn.execute(
                        "SELECT type FROM entities WHERE id = ?", (entity_id,)
                    ).fetchone()[0]
                    if entity_type == "founder":
                        compute_founder_score(conn, entity_id)

            dest_dir = processed_dir / source_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(dest_dir / file_path.name))

    return ingested_ids
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_pipeline.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Write the failing CLI test**

`tests/test_cli.py`:
```python
import json
import sys

from memory_layer import cli


def test_cli_run_ingests_and_reports(tmp_path, monkeypatch, capsys):
    incoming = tmp_path / "incoming"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 5}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))
    db_path = tmp_path / "test.db"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "memory_layer",
            "run",
            "--db",
            str(db_path),
            "--incoming",
            str(incoming),
            "--processed",
            str(tmp_path / "processed"),
        ],
    )
    cli.main()

    output = capsys.readouterr().out
    assert "Ingested 1 new raw record" in output
```

- [ ] **Step 6: Run test to verify it fails**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.cli'`

- [ ] **Step 7: Write `cli.py`**

`memory_layer/cli.py`:
```python
import argparse
from pathlib import Path

from .db import init_db
from .entity_resolution import resolve_entity
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="memory_layer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Process new raw blobs from the incoming folder")
    run_parser.add_argument("--db", default="data/vc_brain.db")
    run_parser.add_argument("--incoming", default="data/incoming")
    run_parser.add_argument("--processed", default="data/processed")

    resolve_parser = subparsers.add_parser("resolve", help="Manually resolve a needs_review raw_record")
    resolve_parser.add_argument("raw_record_id", type=int)
    resolve_parser.add_argument("decision", help='An entity_id to merge into, or "new"')
    resolve_parser.add_argument("--db", default="data/vc_brain.db")

    args = parser.parse_args()

    if args.command == "run":
        conn = init_db(args.db)
        ingested = run_pipeline(conn, Path(args.incoming), Path(args.processed))
        print(f"Ingested {len(ingested)} new raw record(s).")
    elif args.command == "resolve":
        conn = init_db(args.db)
        decision = args.decision if args.decision == "new" else int(args.decision)
        entity_id = resolve_entity(conn, args.raw_record_id, decision)
        print(f"Resolved raw_record {args.raw_record_id} -> entity {entity_id}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 8: Run test to verify it passes**

Run: `pytest tests/test_cli.py -v`
Expected: PASS (1 passed)

- [ ] **Step 9: Commit**

```bash
git add memory_layer/pipeline.py memory_layer/cli.py tests/test_pipeline.py tests/test_cli.py
git commit -m "feat: add pipeline orchestration and CLI entrypoints"
```

---

## Task 13: Read-Only Query Interface & SQL Views

**Files:**
- Create: `memory_layer/query.py`
- Modify: `memory_layer/db.py`
- Test: `tests/test_query.py`

**Interfaces:**
- Consumes: nothing new (reads schema from Task 1)
- Produces:
  - `memory_layer.query.create_views(conn: sqlite3.Connection) -> None` — creates `v_founder_scores_latest`, `v_data_points_with_confidence`, `v_contradictions_open`, `v_needs_review`
  - `memory_layer.query.get_founder_score(conn, entity_id: int) -> Optional[Tuple[float, str, str]]` — `(score, coverage, computed_at)`
  - `memory_layer.query.get_data_points(conn, entity_id: int, attribute: Optional[str] = None) -> List[tuple]`
  - `memory_layer.db.init_db` now also calls `create_views` before returning the connection

- [ ] **Step 1: Write the failing test**

`tests/test_query.py`:
```python
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.founder_score import compute_founder_score
from memory_layer.query import get_data_points, get_founder_score
from memory_layer.sources_repo import get_or_create_source


def test_views_are_created():
    conn = init_db(":memory:")
    views = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    }
    assert {
        "v_founder_scores_latest",
        "v_data_points_with_confidence",
        "v_contradictions_open",
        "v_needs_review",
    }.issubset(views)


def test_get_founder_score_and_data_points():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    source_id = get_or_create_source(conn, "github")
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, ?, '{}', 'h1', 'f.json', ?, 'resolved')",
        (source_id, entity_id, now),
    )
    raw_record_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, ?, ?, 'github_stars', '10', 'numeric', NULL, ?, 0.9, 'insufficient_data')",
        (entity_id, raw_record_id, source_id, now),
    )
    conn.commit()
    compute_founder_score(conn, entity_id)

    result = get_founder_score(conn, entity_id)
    assert result is not None
    assert result[1] == "1/3"

    data_points = get_data_points(conn, entity_id, attribute="github_stars")
    assert len(data_points) == 1
    assert data_points[0][0] == "github_stars"

    assert get_data_points(conn, entity_id) == data_points
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_query.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'memory_layer.query'`

- [ ] **Step 3: Write `query.py`**

`memory_layer/query.py`:
```python
import sqlite3
from typing import List, Optional, Tuple

VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_founder_scores_latest AS
SELECT e.id AS entity_id, e.canonical_name, fs.score, fs.coverage, fs.computed_at
FROM founder_scores fs
JOIN entities e ON e.id = fs.entity_id;

CREATE VIEW IF NOT EXISTS v_data_points_with_confidence AS
SELECT dp.id, dp.entity_id, e.canonical_name, dp.attribute_name, dp.value,
       dp.confidence_score, dp.confidence_tier, dp.observed_at, s.name AS source_name
FROM data_points dp
JOIN entities e ON e.id = dp.entity_id
JOIN sources s ON s.id = dp.source_id;

CREATE VIEW IF NOT EXISTS v_contradictions_open AS
SELECT c.id, c.entity_id, e.canonical_name, c.attribute_name, c.description, c.detected_at
FROM contradictions c
JOIN entities e ON e.id = c.entity_id;

CREATE VIEW IF NOT EXISTS v_needs_review AS
SELECT rr.id AS raw_record_id, s.name AS source_name, rr.raw_payload, rr.ingested_at
FROM raw_records rr
JOIN sources s ON s.id = rr.source_id
WHERE rr.resolution_status = 'needs_review';
"""


def create_views(conn: sqlite3.Connection) -> None:
    conn.executescript(VIEWS_SQL)
    conn.commit()


def get_founder_score(conn: sqlite3.Connection, entity_id: int) -> Optional[Tuple[float, str, str]]:
    return conn.execute(
        "SELECT score, coverage, computed_at FROM founder_scores WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()


def get_data_points(
    conn: sqlite3.Connection, entity_id: int, attribute: Optional[str] = None
) -> List[tuple]:
    if attribute:
        return conn.execute(
            "SELECT attribute_name, value, confidence_score, confidence_tier, source_id "
            "FROM data_points WHERE entity_id = ? AND attribute_name = ?",
            (entity_id, attribute),
        ).fetchall()
    return conn.execute(
        "SELECT attribute_name, value, confidence_score, confidence_tier, source_id "
        "FROM data_points WHERE entity_id = ?",
        (entity_id,),
    ).fetchall()
```

- [ ] **Step 4: Wire view creation into `init_db`**

In `memory_layer/db.py`, add the import at the top:
```python
from .query import create_views
```

And change the end of `init_db` from:
```python
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn
```
to:
```python
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    create_views(conn)
    return conn
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_query.py tests/test_db.py -v`
Expected: PASS (all passed)

- [ ] **Step 6: Run the full test suite**

Run: `pytest -v`
Expected: All tests across every task pass.

- [ ] **Step 7: Commit**

```bash
git add memory_layer/query.py memory_layer/db.py tests/test_query.py
git commit -m "feat: add read-only query interface and SQL views for consumers"
```

---

## Final Verification

- [ ] Run `pytest -v` from the repo root — every test across all 13 files passes.
- [ ] Run `python -m memory_layer.cli run --db /tmp/manual_check.db --incoming data/incoming --processed data/processed` against an empty `data/incoming/` — confirm it prints `Ingested 0 new raw record(s).` without error, proving the CLI and schema wire up correctly end-to-end.

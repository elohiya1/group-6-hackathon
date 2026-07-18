import sqlite3

from .query import create_views

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
    create_views(conn)
    return conn

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

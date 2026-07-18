import sqlite3

import pytest

from memory_layer.db import init_db

from funnel.db import SCHEMA_SQL, init_funnel_schema

EXPECTED_TABLES = {"outbound_signals", "activations", "applications"}


def test_init_funnel_schema_creates_all_tables():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(tables)


def test_foreign_keys_enforced_for_applications():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO applications "
            "(origin, company_name, status, first_signal_at, submitted_at, company_entity_id) "
            "VALUES ('inbound', 'Acme', 'submitted', '2026-01-01', '2026-01-01', 999)"
        )


def test_init_funnel_schema_is_idempotent():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    conn.executescript(SCHEMA_SQL)

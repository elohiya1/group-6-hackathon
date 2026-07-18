import sqlite3

import pytest

from funnel.db import init_funnel_schema
from memory_layer.db import init_db

from intelligence.db import SCHEMA_SQL, init_intelligence_schema

EXPECTED_TABLES = {"thesis", "thesis_fit", "axis_scores", "axis_score_history", "investment_memos"}


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def test_init_intelligence_schema_creates_all_tables():
    conn = _conn()
    init_intelligence_schema(conn)
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    tables = {row[0] for row in rows}
    assert EXPECTED_TABLES.issubset(tables)


def test_foreign_keys_enforced_for_thesis_fit():
    conn = _conn()
    init_intelligence_schema(conn)
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO thesis_fit (application_id, in_thesis, rationale, computed_at) "
            "VALUES (999, 1, 'test', '2026-01-01')"
        )


def test_init_intelligence_schema_is_idempotent():
    conn = _conn()
    init_intelligence_schema(conn)
    conn.executescript(SCHEMA_SQL)

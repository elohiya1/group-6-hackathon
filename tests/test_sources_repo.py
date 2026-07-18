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

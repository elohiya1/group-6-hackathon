import pytest

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity

from funnel.activate import activate_signal
from funnel.db import init_funnel_schema


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def _make_signal(conn, entity_id, score=80.0):
    cursor = conn.execute(
        "INSERT INTO outbound_signals (entity_id, conviction_score, detected_at, status) "
        "VALUES (?, ?, '2026-01-01T00:00:00+00:00', 'identified')",
        (entity_id, score),
    )
    conn.commit()
    return cursor.lastrowid


def test_activate_signal_logs_outreach_and_updates_status():
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    signal_id = _make_signal(conn, founder)

    activation_id = activate_signal(conn, signal_id)

    activation = conn.execute(
        "SELECT entity_id, channel FROM activations WHERE id = ?", (activation_id,)
    ).fetchone()
    assert activation == (founder, "email")
    status = conn.execute(
        "SELECT status FROM outbound_signals WHERE id = ?", (signal_id,)
    ).fetchone()[0]
    assert status == "activated"


def test_activate_signal_rejects_already_activated():
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    signal_id = _make_signal(conn, founder)
    activate_signal(conn, signal_id)

    with pytest.raises(ValueError):
        activate_signal(conn, signal_id)

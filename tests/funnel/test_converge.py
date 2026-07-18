import pytest

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity

from funnel.activate import activate_signal
from funnel.applications_repo import get_application
from funnel.converge import converge_signal
from funnel.db import init_funnel_schema


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def _make_signal(conn, entity_id, detected_at="2026-01-01T00:00:00+00:00", score=80.0):
    cursor = conn.execute(
        "INSERT INTO outbound_signals (entity_id, conviction_score, detected_at, status) "
        "VALUES (?, ?, ?, 'identified')",
        (entity_id, score, detected_at),
    )
    conn.commit()
    return cursor.lastrowid


def test_converge_signal_creates_outbound_application_preserving_first_signal(tmp_path):
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    signal_id = _make_signal(conn, founder, detected_at="2026-01-01T00:00:00+00:00")
    activate_signal(conn, signal_id)
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)

    application_id = converge_signal(conn, signal_id, "Analytical Engines Inc", deck)

    app = get_application(conn, application_id)
    assert app[1] == "outbound"
    assert app[2] == "Analytical Engines Inc"
    assert app[4] == founder
    assert app[7] == "2026-01-01T00:00:00+00:00"

    signal_status = conn.execute(
        "SELECT status FROM outbound_signals WHERE id = ?", (signal_id,)
    ).fetchone()[0]
    assert signal_status == "converged"


def test_converge_signal_requires_activation_first(tmp_path):
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    signal_id = _make_signal(conn, founder)
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)

    with pytest.raises(ValueError):
        converge_signal(conn, signal_id, "Acme", deck)

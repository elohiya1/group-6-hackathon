from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity

from funnel.db import init_funnel_schema
from funnel.identify import scan_for_signals


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def _set_founder_score(conn, entity_id, score):
    conn.execute(
        "INSERT INTO founder_scores (entity_id, score, coverage, computed_at) "
        "VALUES (?, ?, '1/4', '2026-01-01')",
        (entity_id, score),
    )
    conn.commit()


def test_scan_for_signals_flags_high_scorers():
    conn = _conn()
    strong = create_entity(conn, "founder", "Ada Lovelace")
    weak = create_entity(conn, "founder", "Bob Nobody")
    _set_founder_score(conn, strong, 80.0)
    _set_founder_score(conn, weak, 20.0)

    signal_ids = scan_for_signals(conn, conviction_threshold=65.0)

    assert len(signal_ids) == 1
    signal = conn.execute(
        "SELECT entity_id, conviction_score, status FROM outbound_signals WHERE id = ?",
        (signal_ids[0],),
    ).fetchone()
    assert signal == (strong, 80.0, "identified")


def test_scan_for_signals_does_not_duplicate_existing_signal():
    conn = _conn()
    strong = create_entity(conn, "founder", "Ada Lovelace")
    _set_founder_score(conn, strong, 80.0)

    first = scan_for_signals(conn, conviction_threshold=65.0)
    second = scan_for_signals(conn, conviction_threshold=65.0)

    assert len(first) == 1
    assert len(second) == 0

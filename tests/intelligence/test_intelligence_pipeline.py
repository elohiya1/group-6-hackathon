from unittest.mock import patch

from funnel.activate import activate_signal
from funnel.applications_repo import get_application
from funnel.converge import converge_signal
from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from funnel.screen import screen_application
from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity

from intelligence.db import init_intelligence_schema
from intelligence.pipeline import run_intelligence, run_pending
from intelligence.thesis_repo import set_thesis

FAKE_THESIS_FIT = {"in_thesis": True, "rationale": "fits"}
FAKE_AXIS = {"rating": "bullish", "score": 80.0, "rationale": "solid"}
FAKE_MEMO = {
    "company_snapshot": "snapshot",
    "investment_hypotheses": ["h1"],
    "swot": {"strengths": [], "weaknesses": [], "opportunities": [], "risks": []},
    "problem_and_product": "problem",
    "traction_and_kpis": "traction",
    "gaps_flagged": [],
}


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    init_intelligence_schema(conn)
    set_thesis(
        conn,
        sectors=["AI infra"],
        stage="seed",
        geography=["US"],
        check_size_min=50000.0,
        check_size_max=150000.0,
        ownership_target_pct=5.0,
        risk_appetite="high",
    )
    return conn


def _patched():
    return (
        patch("intelligence.thesis_engine.chat_json", return_value=FAKE_THESIS_FIT),
        patch("intelligence.axis_scoring.chat_json", return_value=FAKE_AXIS),
        patch("intelligence.memo.chat_json", return_value=FAKE_MEMO),
    )


def test_run_intelligence_produces_thesis_fit_axes_and_memo(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    application_id = submit_application(conn, "Acme Inc", deck)

    p1, p2, p3 = _patched()
    with p1, p2, p3:
        result = run_intelligence(conn, application_id)

    assert result["thesis_fit"] == FAKE_THESIS_FIT
    assert set(result["axis_scores"].keys()) == {"founder", "market", "idea_vs_market"}
    assert result["memo"] == FAKE_MEMO

    memo_row = conn.execute(
        "SELECT COUNT(*) FROM investment_memos WHERE application_id = ?", (application_id,)
    ).fetchone()[0]
    assert memo_row == 1


def test_run_pending_only_processes_screened_pass_applications(tmp_path):
    conn = _conn()

    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    passing_id = submit_application(conn, "Acme Inc", deck)
    screen_application(conn, passing_id)

    thin_deck = tmp_path / "thin.txt"
    thin_deck.write_text("short")
    failing_id = submit_application(conn, "Thin Co", thin_deck)
    screen_application(conn, failing_id)

    unscreened_id = submit_application(conn, "Unscreened Co", deck)

    p1, p2, p3 = _patched()
    with p1, p2, p3:
        processed = run_pending(conn)

    assert processed == [passing_id]
    assert failing_id not in processed
    assert unscreened_id not in processed


def test_run_pending_includes_converged_outbound_applications(tmp_path):
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    signal_cursor = conn.execute(
        "INSERT INTO outbound_signals (entity_id, conviction_score, detected_at, status) "
        "VALUES (?, 80.0, '2026-01-01T00:00:00+00:00', 'identified')",
        (founder,),
    )
    conn.commit()
    signal_id = signal_cursor.lastrowid
    activate_signal(conn, signal_id)

    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    application_id = converge_signal(conn, signal_id, "Analytical Engines Inc", deck)
    screen_application(conn, application_id)

    p1, p2, p3 = _patched()
    with p1, p2, p3:
        processed = run_pending(conn)

    assert processed == [application_id]
    app = get_application(conn, application_id)
    assert app[1] == "outbound"


def test_run_pending_does_not_reprocess_already_memoed_applications(tmp_path):
    """applications.status stays 'screened_pass' forever -- Screening has no
    concept of "decided". Without excluding already-memoed applications,
    every run-pending call would silently re-run (and re-bill) every
    opportunity ever screened."""
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    application_id = submit_application(conn, "Acme Inc", deck)
    screen_application(conn, application_id)

    p1, p2, p3 = _patched()
    with p1, p2, p3:
        first_run = run_pending(conn)
        second_run = run_pending(conn)

    assert first_run == [application_id]
    assert second_run == []

    memo_count = conn.execute(
        "SELECT COUNT(*) FROM investment_memos WHERE application_id = ?", (application_id,)
    ).fetchone()[0]
    assert memo_count == 1

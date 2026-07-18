import json
from unittest.mock import patch

from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from memory_layer.db import init_db

from intelligence.db import init_intelligence_schema
from intelligence.memo import generate_memo
from intelligence.thesis_repo import set_thesis

FAKE_MEMO = {
    "company_snapshot": "Acme sells widgets to enterprises.",
    "investment_hypotheses": ["Strong technical founder", "Clear market wedge"],
    "swot": {
        "strengths": ["Fast shipping velocity"],
        "weaknesses": ["No revenue yet"],
        "opportunities": ["Expansion into EU"],
        "risks": ["Crowded market"],
    },
    "problem_and_product": "Enterprises need widgets; Acme ships them faster.",
    "traction_and_kpis": "Customer count: not disclosed.",
    "gaps_flagged": ["Cap table: not disclosed", "Customer count: not disclosed"],
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


def _application(conn, tmp_path):
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    return submit_application(conn, "Acme Inc", deck)


def test_generate_memo_persists_all_sections(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    with patch("intelligence.memo.chat_json", return_value=FAKE_MEMO):
        result = generate_memo(conn, application_id)

    assert result == FAKE_MEMO
    stored = conn.execute(
        "SELECT company_snapshot, investment_hypotheses, swot, gaps_flagged "
        "FROM investment_memos WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    assert stored[0] == FAKE_MEMO["company_snapshot"]
    assert json.loads(stored[1]) == FAKE_MEMO["investment_hypotheses"]
    assert json.loads(stored[2]) == FAKE_MEMO["swot"]
    assert json.loads(stored[3]) == FAKE_MEMO["gaps_flagged"]


def test_generate_memo_is_idempotent_on_rerun(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    with patch("intelligence.memo.chat_json", return_value=FAKE_MEMO):
        generate_memo(conn, application_id)
        generate_memo(conn, application_id)

    count = conn.execute(
        "SELECT COUNT(*) FROM investment_memos WHERE application_id = ?", (application_id,)
    ).fetchone()[0]
    assert count == 1

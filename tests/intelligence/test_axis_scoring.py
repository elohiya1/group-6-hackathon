from unittest.mock import patch

import pytest

from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from memory_layer.db import init_db

from intelligence.axis_scoring import score_all_axes, score_axis
from intelligence.db import init_intelligence_schema
from intelligence.thesis_repo import set_thesis


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


def test_score_axis_rejects_unknown_axis(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)
    with pytest.raises(ValueError):
        score_axis(conn, application_id, "traction")


def test_score_axis_first_run_trend_is_stable(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    with patch(
        "intelligence.axis_scoring.chat_json",
        return_value={"rating": "bullish", "score": 80.0, "rationale": "Strong technical founder."},
    ):
        result = score_axis(conn, application_id, "founder")

    assert result["trend"] == "stable"
    stored = conn.execute(
        "SELECT rating, score, trend FROM axis_scores WHERE application_id = ? AND axis = 'founder'",
        (application_id,),
    ).fetchone()
    assert stored == ("bullish", 80.0, "stable")


def test_score_axis_detects_improving_and_declining_trend(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    with patch(
        "intelligence.axis_scoring.chat_json",
        side_effect=[
            {"rating": "neutral", "score": 50.0, "rationale": "first pass"},
            {"rating": "bullish", "score": 70.0, "rationale": "second pass, improved"},
            {"rating": "bear", "score": 30.0, "rationale": "third pass, declined"},
        ],
    ):
        first = score_axis(conn, application_id, "market")
        second = score_axis(conn, application_id, "market")
        third = score_axis(conn, application_id, "market")

    assert first["trend"] == "stable"
    assert second["trend"] == "improving"
    assert third["trend"] == "declining"

    history_count = conn.execute(
        "SELECT COUNT(*) FROM axis_score_history WHERE application_id = ? AND axis = 'market'",
        (application_id,),
    ).fetchone()[0]
    assert history_count == 3


def test_score_all_axes_scores_all_three_independently(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    # score_all_axes iterates AXES in the fixed order (founder, market, idea_vs_market).
    responses = [
        {"rating": "bullish", "score": 85.0, "rationale": "strong founder"},
        {"rating": "bear", "score": 25.0, "rationale": "crowded market"},
        {"rating": "neutral", "score": 55.0, "rationale": "could pivot"},
    ]

    with patch("intelligence.axis_scoring.chat_json", side_effect=responses):
        results = score_all_axes(conn, application_id)

    assert set(results.keys()) == {"founder", "market", "idea_vs_market"}
    assert results["founder"]["rating"] == "bullish"
    assert results["market"]["rating"] == "bear"
    assert results["idea_vs_market"]["rating"] == "neutral"

    stored_count = conn.execute(
        "SELECT COUNT(*) FROM axis_scores WHERE application_id = ?", (application_id,)
    ).fetchone()[0]
    assert stored_count == 3

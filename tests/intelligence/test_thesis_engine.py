from unittest.mock import patch

import pytest

from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from memory_layer.db import init_db

from intelligence.db import init_intelligence_schema
from intelligence.thesis_engine import check_thesis_fit
from intelligence.thesis_repo import set_thesis


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    init_intelligence_schema(conn)
    return conn


def _application(conn, tmp_path):
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    return submit_application(conn, "Acme Inc", deck)


def _set_thesis(conn):
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


def test_check_thesis_fit_persists_result(tmp_path):
    conn = _conn()
    _set_thesis(conn)
    application_id = _application(conn, tmp_path)

    with patch(
        "intelligence.thesis_engine.chat_json",
        return_value={"in_thesis": True, "rationale": "Matches AI infra thesis at seed stage."},
    ) as mock_chat:
        result = check_thesis_fit(conn, application_id)

    assert result["in_thesis"] is True
    mock_chat.assert_called_once()
    stored = conn.execute(
        "SELECT in_thesis, rationale FROM thesis_fit WHERE application_id = ?", (application_id,)
    ).fetchone()
    assert stored == (1, "Matches AI infra thesis at seed stage.")


def test_check_thesis_fit_raises_without_configured_thesis(tmp_path):
    conn = _conn()
    application_id = _application(conn, tmp_path)

    with pytest.raises(ValueError):
        check_thesis_fit(conn, application_id)


def test_check_thesis_fit_is_idempotent_on_rerun(tmp_path):
    conn = _conn()
    _set_thesis(conn)
    application_id = _application(conn, tmp_path)

    with patch(
        "intelligence.thesis_engine.chat_json",
        side_effect=[
            {"in_thesis": True, "rationale": "first pass"},
            {"in_thesis": False, "rationale": "second pass"},
        ],
    ):
        check_thesis_fit(conn, application_id)
        check_thesis_fit(conn, application_id)

    count = conn.execute(
        "SELECT COUNT(*) FROM thesis_fit WHERE application_id = ?", (application_id,)
    ).fetchone()[0]
    assert count == 1
    stored = conn.execute(
        "SELECT in_thesis, rationale FROM thesis_fit WHERE application_id = ?", (application_id,)
    ).fetchone()
    assert stored == (0, "second pass")

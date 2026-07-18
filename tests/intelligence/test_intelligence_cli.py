import sys
from unittest.mock import patch

from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from funnel.screen import screen_application
from memory_layer.db import init_db

from intelligence import cli
from intelligence.db import init_intelligence_schema

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


def test_cli_thesis_set_then_show(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "intelligence",
            "thesis",
            "set",
            "--sectors",
            "AI infra",
            "--stage",
            "seed",
            "--geography",
            "US",
            "--check-size-min",
            "50000",
            "--check-size-max",
            "150000",
            "--ownership-target-pct",
            "5",
            "--risk-appetite",
            "high",
            "--db",
            str(db_path),
        ],
    )
    cli.main()
    assert "Thesis updated." in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["intelligence", "thesis", "show", "--db", str(db_path)])
    cli.main()
    output = capsys.readouterr().out
    assert '"stage": "seed"' in output


def test_cli_run_pending_processes_screened_pass_applications(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    conn = init_db(str(db_path))
    init_funnel_schema(conn)
    init_intelligence_schema(conn)
    conn.execute(
        "INSERT INTO thesis (id, sectors, stage, geography, check_size_min, check_size_max, "
        "ownership_target_pct, risk_appetite, updated_at) "
        "VALUES (1, '[\"AI infra\"]', 'seed', '[\"US\"]', 50000, 150000, 5.0, 'high', '2026-01-01')"
    )
    conn.commit()
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    application_id = submit_application(conn, "Acme Inc", deck)
    screen_application(conn, application_id)
    conn.close()

    monkeypatch.setattr(sys, "argv", ["intelligence", "run-pending", "--db", str(db_path)])
    with (
        patch("intelligence.thesis_engine.chat_json", return_value=FAKE_THESIS_FIT),
        patch("intelligence.axis_scoring.chat_json", return_value=FAKE_AXIS),
        patch("intelligence.memo.chat_json", return_value=FAKE_MEMO),
    ):
        cli.main()

    output = capsys.readouterr().out
    assert f"Ran Intelligence on 1 application(s): [{application_id}]" in output

import sys

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity

from funnel import cli
from funnel.db import init_funnel_schema


def test_cli_apply_submits_application(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")

    monkeypatch.setattr(
        sys,
        "argv",
        ["funnel", "apply", "--company-name", "Acme Inc", "--deck", str(deck), "--db", str(db_path)],
    )
    cli.main()

    assert "Submitted application 1" in capsys.readouterr().out


def test_cli_apply_then_screen(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)

    monkeypatch.setattr(
        sys,
        "argv",
        ["funnel", "apply", "--company-name", "Acme Inc", "--deck", str(deck), "--db", str(db_path)],
    )
    cli.main()

    monkeypatch.setattr(sys, "argv", ["funnel", "screen", "1", "--db", str(db_path)])
    cli.main()

    assert "Application 1 -> screened_pass" in capsys.readouterr().out


def test_cli_identify_activate_converge_full_lifecycle(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "test.db"
    conn = init_db(str(db_path))
    init_funnel_schema(conn)
    founder = create_entity(conn, "founder", "Ada Lovelace")
    conn.execute(
        "INSERT INTO founder_scores (entity_id, score, coverage, computed_at) "
        "VALUES (?, 80.0, '1/4', '2026-01-01')",
        (founder,),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(sys, "argv", ["funnel", "identify", "--db", str(db_path)])
    cli.main()
    assert "Identified 1 new signal(s): [1]" in capsys.readouterr().out

    monkeypatch.setattr(sys, "argv", ["funnel", "activate", "1", "--db", str(db_path)])
    cli.main()
    assert "Logged activation 1 for signal 1" in capsys.readouterr().out

    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "funnel",
            "converge",
            "1",
            "--company-name",
            "Analytical Engines Inc",
            "--deck",
            str(deck),
            "--db",
            str(db_path),
        ],
    )
    cli.main()
    assert "Converged signal 1 -> application 1" in capsys.readouterr().out

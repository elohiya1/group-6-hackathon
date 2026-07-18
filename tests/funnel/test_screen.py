import pytest

from memory_layer.db import init_db

from funnel.applications_repo import get_application
from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from funnel.screen import screen_application


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def test_screen_pass_for_healthy_application(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    application_id = submit_application(conn, "Acme Inc", deck)

    status = screen_application(conn, application_id)

    assert status == "screened_pass"
    app = get_application(conn, application_id)
    assert app[6] == "screened_pass"
    assert app[9] is not None


def test_screen_fail_for_thin_deck(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("too short")
    application_id = submit_application(conn, "Acme Inc", deck)

    status = screen_application(conn, application_id)

    assert status == "screened_fail"
    app = get_application(conn, application_id)
    assert "deck too thin" in app[10]


def test_screen_fail_for_duplicate_submission(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    first_id = submit_application(conn, "Acme Inc", deck)
    screen_application(conn, first_id)
    second_id = submit_application(conn, "Acme Inc", deck)

    status = screen_application(conn, second_id)

    assert status == "screened_fail"
    app = get_application(conn, second_id)
    assert "duplicate" in app[10]


def test_screen_rejects_already_screened_application(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("x" * 500)
    application_id = submit_application(conn, "Acme Inc", deck)
    screen_application(conn, application_id)

    with pytest.raises(ValueError):
        screen_application(conn, application_id)

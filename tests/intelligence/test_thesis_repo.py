from funnel.db import init_funnel_schema
from memory_layer.db import init_db

from intelligence.db import init_intelligence_schema
from intelligence.thesis_repo import get_thesis, set_thesis


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    init_intelligence_schema(conn)
    return conn


def test_get_thesis_returns_none_when_unset():
    conn = _conn()
    assert get_thesis(conn) is None


def test_set_and_get_thesis_round_trips():
    conn = _conn()
    set_thesis(
        conn,
        sectors=["AI infra", "devtools"],
        stage="seed",
        geography=["US", "EU"],
        check_size_min=50000.0,
        check_size_max=150000.0,
        ownership_target_pct=5.0,
        risk_appetite="high",
    )

    thesis = get_thesis(conn)

    assert thesis["sectors"] == ["AI infra", "devtools"]
    assert thesis["stage"] == "seed"
    assert thesis["check_size_max"] == 150000.0


def test_set_thesis_overwrites_previous_configuration():
    conn = _conn()
    set_thesis(
        conn,
        sectors=["AI infra"],
        stage="seed",
        geography=["US"],
        check_size_min=50000.0,
        check_size_max=100000.0,
        ownership_target_pct=5.0,
        risk_appetite="high",
    )
    set_thesis(
        conn,
        sectors=["fintech"],
        stage="series-a",
        geography=["EU"],
        check_size_min=200000.0,
        check_size_max=500000.0,
        ownership_target_pct=10.0,
        risk_appetite="low",
    )

    thesis = get_thesis(conn)

    assert thesis["sectors"] == ["fintech"]
    assert thesis["stage"] == "series-a"
    count = conn.execute("SELECT COUNT(*) FROM thesis").fetchone()[0]
    assert count == 1

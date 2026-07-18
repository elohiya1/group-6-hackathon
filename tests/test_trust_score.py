from datetime import datetime, timedelta, timezone

import pytest

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.sources_repo import get_or_create_source
from memory_layer.trust_score import compute_trust_scores


def _insert_data_point(conn, entity_id, source_name, attribute_name, value, value_type, observed_at=None):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, ?, '{}', ?, 'test.json', ?, 'resolved')",
        (source_id, entity_id, f"hash-{attribute_name}-{value}-{source_name}", now),
    )
    raw_record_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
        (entity_id, raw_record_id, source_id, attribute_name, value, value_type, observed_at, now),
    )
    conn.commit()


def test_single_source_is_insufficient_data():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    row = conn.execute(
        "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == "insufficient_data"


def test_agreeing_sources_are_corroborated():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "ceo", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["corroborated", "corroborated"]


def test_conflicting_sources_are_contradicted_and_recorded():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "CTO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["contradicted", "contradicted"]
    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ? AND attribute_name = 'job_title'",
        (entity_id,),
    ).fetchone()[0]
    assert contradiction_count == 1


def test_compute_trust_scores_is_idempotent():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Grace Hopper")
    _insert_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical")
    _insert_data_point(conn, entity_id, "tavily", "job_title", "CTO", "categorical")

    compute_trust_scores(conn, entity_id, "job_title")
    compute_trust_scores(conn, entity_id, "job_title")

    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ? AND attribute_name = 'job_title'",
        (entity_id,),
    ).fetchone()[0]
    assert contradiction_count == 1


def test_decaying_attribute_outside_window_is_not_a_contradiction():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    two_years_ago = (datetime.now(timezone.utc) - timedelta(days=730)).isoformat()
    today = datetime.now(timezone.utc).isoformat()
    _insert_data_point(conn, entity_id, "crunchbase", "employee_count", "50", "numeric", observed_at=two_years_ago)
    _insert_data_point(conn, entity_id, "tavily", "employee_count", "500", "numeric", observed_at=today)

    compute_trust_scores(conn, entity_id, "employee_count")

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["insufficient_data", "insufficient_data"]
    contradiction_count = conn.execute(
        "SELECT COUNT(*) FROM contradictions WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert contradiction_count == 0


def test_decaying_attribute_within_window_still_detects_contradiction():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    now = datetime.now(timezone.utc)
    _insert_data_point(
        conn, entity_id, "crunchbase", "employee_count", "50", "numeric", observed_at=now.isoformat()
    )
    _insert_data_point(
        conn,
        entity_id,
        "tavily",
        "employee_count",
        "500",
        "numeric",
        observed_at=(now - timedelta(days=5)).isoformat(),
    )

    compute_trust_scores(conn, entity_id, "employee_count", now=now)

    tiers = [
        r[0]
        for r in conn.execute(
            "SELECT confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
        ).fetchall()
    ]
    assert tiers == ["contradicted", "contradicted"]


def test_reliability_decays_with_age():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme")
    now = datetime.now(timezone.utc)
    one_half_life_ago = now - timedelta(days=90)  # github_stars half_life_days == 90
    _insert_data_point(
        conn, entity_id, "github", "github_stars", "100", "numeric", observed_at=one_half_life_ago.isoformat()
    )

    compute_trust_scores(conn, entity_id, "github_stars", now=now)

    row = conn.execute(
        "SELECT confidence_score FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    # github reliability weight is 0.9; one half-life => ~0.45
    assert row[0] == pytest.approx(0.45, abs=0.01)


def test_static_attribute_ignores_age():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    now = datetime.now(timezone.utc)
    long_ago = (now - timedelta(days=3650)).isoformat()
    _insert_data_point(conn, entity_id, "patents", "patents_filed", "3", "numeric", observed_at=long_ago)

    compute_trust_scores(conn, entity_id, "patents_filed", now=now)

    row = conn.execute(
        "SELECT confidence_score, confidence_tier FROM data_points WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == pytest.approx(0.85)  # patents source reliability, undecayed
    assert row[1] == "insufficient_data"

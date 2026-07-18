from datetime import datetime, timezone

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

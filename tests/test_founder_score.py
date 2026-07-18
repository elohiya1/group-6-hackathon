import json
from datetime import datetime, timezone

import pytest

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.founder_score import compute_founder_score
from memory_layer.sources_repo import get_or_create_source


def _insert_scored_data_point(conn, entity_id, source_name, attribute_name, value, value_type, confidence_score):
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
        "VALUES (?, ?, ?, ?, ?, ?, NULL, ?, ?, 'corroborated')",
        (entity_id, raw_record_id, source_id, attribute_name, value, value_type, now, confidence_score),
    )
    conn.commit()


def test_founder_score_full_coverage():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "500", "numeric", 0.9)
    _insert_scored_data_point(conn, entity_id, "patents", "patents_filed", "2", "numeric", 0.85)
    _insert_scored_data_point(conn, entity_id, "linkedin", "job_title", "CEO", "categorical", 0.55)

    score = compute_founder_score(conn, entity_id)

    row = conn.execute(
        "SELECT score, coverage FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[0] == pytest.approx(score)
    assert row[1] == "3/3"
    history_count = conn.execute(
        "SELECT COUNT(*) FROM founder_score_history WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert history_count == 1


def test_founder_score_renormalizes_missing_categories():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "First-Time Founder")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "10", "numeric", 0.9)

    score = compute_founder_score(conn, entity_id)

    row = conn.execute(
        "SELECT score, coverage FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()
    assert row[1] == "1/3"
    assert row[0] == pytest.approx(90.0)


def test_founder_score_history_appends_not_overwrites():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "10", "numeric", 0.5)
    compute_founder_score(conn, entity_id)
    _insert_scored_data_point(conn, entity_id, "github", "github_stars", "20", "numeric", 0.9)
    compute_founder_score(conn, entity_id)

    history_count = conn.execute(
        "SELECT COUNT(*) FROM founder_score_history WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert history_count == 2
    current_rows = conn.execute(
        "SELECT COUNT(*) FROM founder_scores WHERE entity_id = ?", (entity_id,)
    ).fetchone()[0]
    assert current_rows == 1

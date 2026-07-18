from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entities_repo import create_entity
from memory_layer.founder_score import compute_founder_score
from memory_layer.query import get_data_points, get_founder_score
from memory_layer.sources_repo import get_or_create_source


def test_views_are_created():
    conn = init_db(":memory:")
    views = {
        r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='view'").fetchall()
    }
    assert {
        "v_founder_scores_latest",
        "v_data_points_with_confidence",
        "v_contradictions_open",
        "v_needs_review",
    }.issubset(views)


def test_get_founder_score_and_data_points():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    source_id = get_or_create_source(conn, "github")
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, ?, '{}', 'h1', 'f.json', ?, 'resolved')",
        (source_id, entity_id, now),
    )
    raw_record_id = cursor.lastrowid
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, ?, ?, 'github_stars', '10', 'numeric', NULL, ?, 0.9, 'insufficient_data')",
        (entity_id, raw_record_id, source_id, now),
    )
    conn.commit()
    compute_founder_score(conn, entity_id)

    result = get_founder_score(conn, entity_id)
    assert result is not None
    assert result[1] == "1/4"

    data_points = get_data_points(conn, entity_id, attribute="github_stars")
    assert len(data_points) == 1
    assert data_points[0][0] == "github_stars"

    assert get_data_points(conn, entity_id) == data_points

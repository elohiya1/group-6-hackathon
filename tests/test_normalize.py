import json
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entity_resolution import resolve_raw_record
from memory_layer.normalize import normalize_raw_record
from memory_layer.sources_repo import get_or_create_source


def _insert_raw_record(conn, source_name, payload, content_hash, status="needs_review"):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, 'test.json', ?, ?)",
        (source_id, json.dumps(payload), content_hash, now, status),
    )
    conn.commit()
    return cursor.lastrowid


def test_normalize_creates_data_points_for_resolved_record():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash-norm-1")
    resolve_raw_record(conn, rr_id)

    count = normalize_raw_record(conn, rr_id)

    assert count == 1
    row = conn.execute(
        "SELECT attribute_name, value, value_type FROM data_points WHERE raw_record_id = ?",
        (rr_id,),
    ).fetchone()
    assert row == ("github_stars", "42", "numeric")


def test_normalize_skips_unresolved_record():
    conn = init_db(":memory:")
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-norm-2", status="needs_review")

    count = normalize_raw_record(conn, rr_id)

    assert count == 0
    remaining = conn.execute(
        "SELECT COUNT(*) FROM data_points WHERE raw_record_id = ?", (rr_id,)
    ).fetchone()[0]
    assert remaining == 0

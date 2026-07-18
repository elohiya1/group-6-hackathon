import json
from datetime import datetime, timezone

from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity
from memory_layer.entity_resolution import resolve_raw_record
from memory_layer.sources_repo import get_or_create_source


def _insert_raw_record(conn, source_name, payload, content_hash):
    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, 'test.json', ?, 'needs_review')",
        (source_id, json.dumps(payload), content_hash, now),
    )
    conn.commit()
    return cursor.lastrowid


def test_resolve_raw_record_creates_new_founder_entity():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash1")

    status = resolve_raw_record(conn, rr_id)

    assert status == "new_entity"
    entity_id, resolution_status = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert entity_id is not None
    assert resolution_status == "new_entity"
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "founder"


def test_resolve_raw_record_creates_new_company_entity():
    conn = init_db(":memory:")
    payload = {"name": "Acme Corp", "company_domain": "acme.com", "employee_count": 50}
    rr_id = _insert_raw_record(conn, "crunchbase", payload, "hash2")

    status = resolve_raw_record(conn, rr_id)

    assert status == "new_entity"
    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_resolve_raw_record_matches_existing_entity():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 42}
    rr_id = _insert_raw_record(conn, "github", payload, "hash3")

    status = resolve_raw_record(conn, rr_id)

    assert status == "resolved"
    row = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()
    assert row[0] == entity_id


def test_resolve_raw_record_conflicting_matches_needs_review():
    conn = init_db(":memory:")
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash4")

    status = resolve_raw_record(conn, rr_id)

    assert status == "needs_review"
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (None, "needs_review")

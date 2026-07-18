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


def test_resolve_raw_record_creates_company_for_companies_house():
    conn = init_db(":memory:")
    payload = {
        "name": "Acme AI Ltd",
        "company_number": "12345678",
        "company_status": "active",
    }
    rr_id = _insert_raw_record(conn, "companies_house", payload, "hash-ch")

    resolve_raw_record(conn, rr_id)

    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_resolve_raw_record_creates_company_for_ycombinator():
    conn = init_db(":memory:")
    payload = {"name": "Acme AI (YC W26)", "url": "https://ycombinator.com/companies/acme-ai"}
    rr_id = _insert_raw_record(conn, "ycombinator", payload, "hash-yc")

    resolve_raw_record(conn, rr_id)

    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_resolve_raw_record_creates_company_for_devpost():
    conn = init_db(":memory:")
    payload = {"name": "FounderScore", "url": "https://devpost.com/software/founderscore"}
    rr_id = _insert_raw_record(conn, "devpost", payload, "hash-devpost")

    resolve_raw_record(conn, rr_id)

    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_resolve_raw_record_still_founder_for_ambiguous_program_pages():
    conn = init_db(":memory:")
    payload = {"name": "MIT delta v cohort", "url": "https://deltav.mit.edu/cohort"}
    rr_id = _insert_raw_record(conn, "university_challenge", payload, "hash-univ")

    resolve_raw_record(conn, rr_id)

    entity_id = conn.execute("SELECT entity_id FROM raw_records WHERE id = ?", (rr_id,)).fetchone()[0]
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "founder"


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


import pytest

from memory_layer.entities_repo import find_entity_by_identifier
from memory_layer.entity_resolution import resolve_entity


def test_resolve_entity_merges_into_existing():
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
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-merge")
    resolve_raw_record(conn, rr_id)  # lands in needs_review

    resolved_entity_id = resolve_entity(conn, rr_id, decision=company)

    assert resolved_entity_id == company
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (company, "resolved")
    # The email identifier already belonged to `founder`, a different entity
    # never part of this decision — add_identifier's INSERT OR IGNORE leaves
    # it untouched rather than silently reassigning it. Identifiers only ever
    # move between entities through an explicit, dedicated action, never as
    # a side effect of resolving an unrelated record.
    assert find_entity_by_identifier(conn, "email", "grace@acme.com") == founder


def test_resolve_entity_as_new():
    conn = init_db(":memory:")
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    payload = {
        "name": "Acme West",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    rr_id = _insert_raw_record(conn, "tavily", payload, "hash-new")
    resolve_raw_record(conn, rr_id)

    resolved_entity_id = resolve_entity(conn, rr_id, decision="new")

    assert resolved_entity_id not in (company, founder)
    row = conn.execute(
        "SELECT entity_id, resolution_status FROM raw_records WHERE id = ?", (rr_id,)
    ).fetchone()
    assert row == (resolved_entity_id, "resolved")


def test_resolve_entity_rejects_non_pending_record():
    conn = init_db(":memory:")
    payload = {"name": "Ada Lovelace", "owner": {"login": "ada"}, "stargazers_count": 1}
    rr_id = _insert_raw_record(conn, "github", payload, "hash-x")
    resolve_raw_record(conn, rr_id)  # resolves to new_entity, not needs_review

    with pytest.raises(ValueError):
        resolve_entity(conn, rr_id, decision="new")

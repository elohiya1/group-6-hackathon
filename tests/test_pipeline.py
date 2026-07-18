import json

from memory_layer.db import init_db
from memory_layer.pipeline import run_pipeline


def test_end_to_end_pipeline_multi_source_founder(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)

    github_payload = {
        "name": "Ada Lovelace",
        "owner": {"login": "adalovelace"},
        "stargazers_count": 250,
    }
    (incoming / "github" / "repo1.json").write_text(json.dumps(github_payload))

    conn = init_db(":memory:")
    ingested = run_pipeline(conn, incoming, processed)

    assert len(ingested) == 1
    entity = conn.execute("SELECT id, type, canonical_name FROM entities").fetchone()
    assert entity[1] == "founder"
    assert entity[2] == "Ada Lovelace"

    data_point = conn.execute(
        "SELECT attribute_name, value, confidence_tier FROM data_points WHERE entity_id = ?",
        (entity[0],),
    ).fetchone()
    assert data_point == ("github_stars", "250", "insufficient_data")

    founder_score = conn.execute(
        "SELECT coverage FROM founder_scores WHERE entity_id = ?", (entity[0],)
    ).fetchone()
    assert founder_score[0] == "1/4"

    assert not (incoming / "github" / "repo1.json").exists()
    assert (processed / "github" / "repo1.json").exists()


def test_end_to_end_pipeline_idempotent_rerun(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    first_run = run_pipeline(conn, incoming, processed)
    assert len(first_run) == 1

    (incoming / "github").mkdir(parents=True, exist_ok=True)
    (incoming / "github" / "repo1_retry.json").write_text(json.dumps(payload))
    second_run = run_pipeline(conn, incoming, processed)

    assert len(second_run) == 0
    count = conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0]
    assert count == 1


def test_dedup_skip_still_moves_file(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    run_pipeline(conn, incoming, processed)

    (incoming / "github").mkdir(parents=True, exist_ok=True)
    (incoming / "github" / "repo1_retry.json").write_text(json.dumps(payload))
    second_run = run_pipeline(conn, incoming, processed)

    assert len(second_run) == 0
    assert not (incoming / "github" / "repo1_retry.json").exists()
    assert (processed / "github" / "repo1_retry.json").exists()


def test_needs_review_record_is_not_normalized_or_scored(tmp_path):
    from memory_layer.entities_repo import add_identifier, create_entity

    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "tavily").mkdir(parents=True)

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
    (incoming / "tavily" / "conflict.json").write_text(json.dumps(payload))

    ingested = run_pipeline(conn, incoming, processed)

    assert len(ingested) == 1
    row = conn.execute(
        "SELECT resolution_status FROM raw_records WHERE id = ?", (ingested[0],)
    ).fetchone()
    assert row[0] == "needs_review"
    data_point_count = conn.execute(
        "SELECT COUNT(*) FROM data_points WHERE raw_record_id = ?", (ingested[0],)
    ).fetchone()[0]
    assert data_point_count == 0


def test_company_entity_does_not_get_founder_score(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "crunchbase").mkdir(parents=True)
    payload = {"name": "Acme Corp", "company_domain": "acme.com", "employee_count": 50}
    (incoming / "crunchbase" / "company1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    run_pipeline(conn, incoming, processed)

    entity = conn.execute(
        "SELECT id, type FROM entities WHERE canonical_name = 'Acme Corp'"
    ).fetchone()
    assert entity is not None
    assert entity[1] == "company"
    founder_score_row = conn.execute(
        "SELECT COUNT(*) FROM founder_scores WHERE entity_id = ?", (entity[0],)
    ).fetchone()[0]
    assert founder_score_row == 0

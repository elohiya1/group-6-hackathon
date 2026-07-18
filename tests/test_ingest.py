import json

from memory_layer.db import init_db
from memory_layer.ingest import run_ingestion


def test_ingest_resolves_and_normalizes_a_new_founder(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)

    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    ingested = run_ingestion(conn, incoming, processed)

    assert len(ingested) == 1
    entity = conn.execute("SELECT id, type, canonical_name FROM entities").fetchone()
    assert entity[1] == "founder"

    data_point = conn.execute(
        "SELECT attribute_name, value FROM data_points WHERE entity_id = ?", (entity[0],)
    ).fetchone()
    assert data_point == ("github_stars", "250")

    assert not (incoming / "github" / "repo1.json").exists()
    assert (processed / "github" / "repo1.json").exists()


def test_ingest_does_not_compute_trust_or_founder_score(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    run_ingestion(conn, incoming, processed)

    data_point = conn.execute(
        "SELECT confidence_score, confidence_tier FROM data_points"
    ).fetchone()
    assert data_point == (None, None)

    founder_score_rows = conn.execute("SELECT COUNT(*) FROM founder_scores").fetchone()[0]
    assert founder_score_rows == 0


def test_ingest_is_idempotent_on_rerun(tmp_path):
    incoming = tmp_path / "incoming"
    processed = tmp_path / "processed"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 250}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))

    conn = init_db(":memory:")
    first_run = run_ingestion(conn, incoming, processed)
    assert len(first_run) == 1

    (incoming / "github").mkdir(parents=True, exist_ok=True)
    (incoming / "github" / "repo1_retry.json").write_text(json.dumps(payload))
    second_run = run_ingestion(conn, incoming, processed)

    assert len(second_run) == 0
    count = conn.execute("SELECT COUNT(*) FROM data_points").fetchone()[0]
    assert count == 1


def test_ingest_handles_missing_incoming_dir(tmp_path):
    conn = init_db(":memory:")
    ingested = run_ingestion(conn, tmp_path / "nonexistent", tmp_path / "processed")
    assert ingested == []

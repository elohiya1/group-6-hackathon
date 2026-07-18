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
    assert founder_score[0] == "1/3"

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

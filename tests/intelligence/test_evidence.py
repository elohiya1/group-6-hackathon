import pytest

from funnel.db import init_funnel_schema
from funnel.intake import submit_application
from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity

from intelligence.evidence import gather_evidence


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def test_gather_evidence_includes_founder_score_and_data_points(tmp_path):
    conn = _conn()
    founder = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, founder, "email", "ada@acme.com")
    conn.execute(
        "INSERT INTO founder_scores (entity_id, score, coverage, computed_at) "
        "VALUES (?, 72.5, '2/4', '2026-01-01')",
        (founder,),
    )
    conn.execute("INSERT INTO sources (id, name, reliability_weight) VALUES (1, 'github', 0.9)")
    conn.execute(
        "INSERT INTO raw_records "
        "(id, source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (1, 1, ?, '{}', 'test-hash', 'test.json', '2026-01-01', 'resolved')",
        (founder,),
    )
    conn.execute(
        "INSERT INTO data_points "
        "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
        " observed_at, created_at, confidence_score, confidence_tier) "
        "VALUES (?, 1, 1, 'github_stars', '250', 'numeric', '2026-01-01', '2026-01-01', 0.9, 'corroborated')",
        (founder,),
    )
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    application_id = submit_application(conn, "Acme Inc", deck, founder_email="ada@acme.com")

    evidence = gather_evidence(conn, application_id)

    assert evidence["application"]["company_name"] == "Acme Inc"
    assert evidence["deck_text"] == "pitch deck content"
    assert evidence["founder_score"] == {"score": 72.5, "coverage": "2/4", "computed_at": "2026-01-01"}
    assert evidence["founder_data_points"] == [
        {
            "attribute_name": "github_stars",
            "value": "250",
            "confidence_score": 0.9,
            "confidence_tier": "corroborated",
        }
    ]
    assert evidence["contradictions"] == []


def test_gather_evidence_handles_unresolved_founder(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    application_id = submit_application(conn, "Acme Inc", deck)

    evidence = gather_evidence(conn, application_id)

    assert evidence["founder_score"] is None
    assert evidence["founder_data_points"] == []


def test_gather_evidence_raises_for_unknown_application():
    conn = _conn()
    with pytest.raises(ValueError):
        gather_evidence(conn, 999)

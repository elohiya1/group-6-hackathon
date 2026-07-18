import json

from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity, find_entity_by_identifier
from memory_layer.pipeline import run_pipeline

from funnel.applications_repo import get_application
from funnel.db import init_funnel_schema
from funnel.intake import submit_application


def _conn():
    conn = init_db(":memory:")
    init_funnel_schema(conn)
    return conn


def test_submit_application_minimum_bar(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")

    application_id = submit_application(conn, "Acme Inc", deck)

    app = get_application(conn, application_id)
    assert app[1] == "inbound"
    assert app[2] == "Acme Inc"
    assert app[6] == "submitted"
    assert app[4] is None  # founder unresolved is fine (cold start)


def test_submit_application_links_known_founder(tmp_path):
    conn = _conn()
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")

    application_id = submit_application(conn, "Acme Inc", deck, founder_email="grace@acme.com")

    app = get_application(conn, application_id)
    assert app[4] == founder

    relationship = conn.execute(
        "SELECT relationship FROM entity_relationships WHERE founder_entity_id = ?", (founder,)
    ).fetchone()
    assert relationship == ("founder",)


def test_submit_application_reuses_existing_company_entity(tmp_path):
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")

    first_id = submit_application(conn, "Acme Inc", deck)
    second_id = submit_application(conn, "Acme Inc", deck)

    first = get_application(conn, first_id)
    second = get_application(conn, second_id)
    assert first[3] == second[3]
    assert first[3] is not None


def test_submit_application_matches_company_already_known_to_memory(tmp_path):
    """A company Person A's pipeline already discovered (e.g. via
    Crunchbase) should be reused, not duplicated, when the founder applies
    inbound under a slightly different spelling of the same name — the
    domain is the authoritative link between the two systems."""
    conn = _conn()
    incoming = tmp_path / "incoming"
    (incoming / "crunchbase").mkdir(parents=True)
    payload = {"name": "Acme Corp", "company_domain": "acme.com", "employee_count": 12}
    (incoming / "crunchbase" / "acme.json").write_text(json.dumps(payload))
    run_pipeline(conn, incoming, tmp_path / "processed")

    known_entity_id = find_entity_by_identifier(conn, "company_domain", "acme.com")
    assert known_entity_id is not None

    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    application_id = submit_application(conn, "Acme Inc.", deck, company_domain="acme.com")

    app = get_application(conn, application_id)
    assert app[2] == "Acme Inc."  # the application keeps the founder's own spelling
    assert app[3] == known_entity_id  # but it's linked to the entity Memory already knew about

    company_count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE type = 'company'"
    ).fetchone()[0]
    assert company_count == 1


def test_submit_application_registers_domain_for_future_resolution(tmp_path):
    """When Apply creates a brand-new company entity with a domain, that
    domain must be registered so a fetcher discovering the same company
    later resolves into this entity instead of creating a duplicate."""
    conn = _conn()
    deck = tmp_path / "deck.txt"
    deck.write_text("pitch deck content")
    application_id = submit_application(conn, "Acme Inc.", deck, company_domain="acme.com")
    app = get_application(conn, application_id)

    incoming = tmp_path / "incoming"
    (incoming / "crunchbase").mkdir(parents=True)
    payload = {"name": "Acme Corp", "company_domain": "acme.com", "employee_count": 12}
    (incoming / "crunchbase" / "acme.json").write_text(json.dumps(payload))
    run_pipeline(conn, incoming, tmp_path / "processed")

    company_count = conn.execute(
        "SELECT COUNT(*) FROM entities WHERE type = 'company'"
    ).fetchone()[0]
    assert company_count == 1
    assert app[3] == find_entity_by_identifier(conn, "company_domain", "acme.com")

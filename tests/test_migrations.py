from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity
from memory_layer.migrations import retype_companies


def test_retype_companies_updates_entity_with_company_identifier():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Acme AI Ltd")
    add_identifier(conn, entity_id, "companies_house_number", "12345678")

    updated = retype_companies(conn)

    assert updated == 1
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_retype_companies_leaves_genuine_founders_alone():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")

    updated = retype_companies(conn)

    assert updated == 0
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "founder"


def test_retype_companies_is_idempotent():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Acme AI Ltd")
    add_identifier(conn, entity_id, "ycombinator_company_url", "https://ycombinator.com/acme")

    first_run = retype_companies(conn)
    second_run = retype_companies(conn)

    assert first_run == 1
    assert second_run == 0
    entity_type = conn.execute("SELECT type FROM entities WHERE id = ?", (entity_id,)).fetchone()[0]
    assert entity_type == "company"


def test_retype_companies_skips_already_correct_entities():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "company", "Acme AI Ltd")
    add_identifier(conn, entity_id, "company_domain", "acme.com")

    updated = retype_companies(conn)

    assert updated == 0

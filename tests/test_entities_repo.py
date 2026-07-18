from memory_layer.db import init_db
from memory_layer.entities_repo import add_identifier, create_entity, find_entity_by_identifier


def test_create_entity_and_find_by_identifier():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    assert find_entity_by_identifier(conn, "github_username", "adalovelace") == entity_id


def test_find_entity_by_identifier_no_match_returns_none():
    conn = init_db(":memory:")
    assert find_entity_by_identifier(conn, "github_username", "nobody") is None


def test_add_identifier_is_idempotent():
    conn = init_db(":memory:")
    entity_id = create_entity(conn, "founder", "Ada Lovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    add_identifier(conn, entity_id, "github_username", "adalovelace")
    row = conn.execute("SELECT COUNT(*) FROM entity_identifiers").fetchone()
    assert row[0] == 1

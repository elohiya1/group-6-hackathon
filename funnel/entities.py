import sqlite3
from datetime import datetime, timezone
from typing import Optional

from memory_layer.entities_repo import add_identifier, create_entity, find_entity_by_identifier


def find_or_create_company(
    conn: sqlite3.Connection, company_name: str, company_domain: Optional[str] = None
) -> int:
    """Resolves a company the same way Person A's pipeline would: a domain is
    an authoritative identifier (shared with Companies House/OpenCorporates/
    Crunchbase-sourced entities), so it's checked first. Falling back to an
    exact canonical_name match only covers the case where no domain is known.
    When a new entity is created with a domain, that domain is registered so
    future fetcher-sourced data about the same company resolves here too."""
    if company_domain:
        existing_id = find_entity_by_identifier(conn, "company_domain", company_domain)
        if existing_id is not None:
            return existing_id

    row = conn.execute(
        "SELECT id FROM entities WHERE type = 'company' AND canonical_name = ?",
        (company_name,),
    ).fetchone()
    if row:
        return row[0]

    entity_id = create_entity(conn, "company", company_name)
    if company_domain:
        add_identifier(conn, entity_id, "company_domain", company_domain)
    return entity_id


def link_founder_company(
    conn: sqlite3.Connection, founder_entity_id: int, company_entity_id: int
) -> None:
    existing = conn.execute(
        "SELECT id FROM entity_relationships WHERE founder_entity_id = ? AND company_entity_id = ?",
        (founder_entity_id, company_entity_id),
    ).fetchone()
    if existing:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO entity_relationships "
        "(founder_entity_id, company_entity_id, relationship, created_at) "
        "VALUES (?, ?, 'founder', ?)",
        (founder_entity_id, company_entity_id, now),
    )
    conn.commit()

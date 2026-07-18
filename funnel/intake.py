import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from memory_layer.entities_repo import find_entity_by_identifier

from .applications_repo import create_application
from .entities import find_or_create_company, link_founder_company


def submit_application(
    conn: sqlite3.Connection,
    company_name: str,
    deck_path: Path,
    *,
    company_domain: Optional[str] = None,
    founder_email: Optional[str] = None,
    founder_github: Optional[str] = None,
) -> int:
    """Inbound Apply step. Minimum bar is deck + company name; company_domain
    and founder identifiers are optional and only used to link to entities
    Memory already knows about. An unresolved founder is fine — the
    cold-start case is what Screening/Intelligence exist to handle, not
    Apply."""
    now = datetime.now(timezone.utc).isoformat()
    company_entity_id = find_or_create_company(conn, company_name, company_domain)

    founder_entity_id = None
    if founder_email:
        founder_entity_id = find_entity_by_identifier(conn, "email", founder_email)
    elif founder_github:
        founder_entity_id = find_entity_by_identifier(conn, "github_username", founder_github)

    if founder_entity_id is not None:
        link_founder_company(conn, founder_entity_id, company_entity_id)

    return create_application(
        conn,
        origin="inbound",
        company_name=company_name,
        first_signal_at=now,
        company_entity_id=company_entity_id,
        founder_entity_id=founder_entity_id,
        deck_path=str(deck_path),
    )

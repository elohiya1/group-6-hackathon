import sqlite3
from pathlib import Path
from typing import Optional

from .applications_repo import create_application
from .entities import find_or_create_company, link_founder_company


def converge_signal(
    conn: sqlite3.Connection,
    outbound_signal_id: int,
    company_name: str,
    deck_path: Path,
    *,
    company_domain: Optional[str] = None,
) -> int:
    """An activated outbound signal turns into a real application once the
    founder responds. Preserves the signal's detected_at as first_signal_at
    so instrumentation measures from the true first signal rather than the
    reply, and routes into the same Screening step as inbound applications."""
    row = conn.execute(
        "SELECT entity_id, detected_at, status FROM outbound_signals WHERE id = ?",
        (outbound_signal_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No outbound_signal with id {outbound_signal_id}")
    entity_id, detected_at, status = row
    if status != "activated":
        raise ValueError(
            f"outbound_signal {outbound_signal_id} has not been activated (status={status})"
        )

    company_entity_id = find_or_create_company(conn, company_name, company_domain)
    link_founder_company(conn, entity_id, company_entity_id)

    application_id = create_application(
        conn,
        origin="outbound",
        company_name=company_name,
        first_signal_at=detected_at,
        company_entity_id=company_entity_id,
        founder_entity_id=entity_id,
        deck_path=str(deck_path),
        outbound_signal_id=outbound_signal_id,
    )
    conn.execute(
        "UPDATE outbound_signals SET status = 'converged' WHERE id = ?", (outbound_signal_id,)
    )
    conn.commit()
    return application_id

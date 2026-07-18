import sqlite3
from datetime import datetime, timezone
from typing import Optional


def create_application(
    conn: sqlite3.Connection,
    *,
    origin: str,
    company_name: str,
    first_signal_at: str,
    company_entity_id: Optional[int] = None,
    founder_entity_id: Optional[int] = None,
    deck_path: Optional[str] = None,
    outbound_signal_id: Optional[int] = None,
) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO applications "
        "(origin, company_name, company_entity_id, founder_entity_id, deck_path, "
        " status, first_signal_at, submitted_at, outbound_signal_id) "
        "VALUES (?, ?, ?, ?, ?, 'submitted', ?, ?, ?)",
        (
            origin,
            company_name,
            company_entity_id,
            founder_entity_id,
            deck_path,
            first_signal_at,
            now,
            outbound_signal_id,
        ),
    )
    conn.commit()
    return cursor.lastrowid


def get_application(conn: sqlite3.Connection, application_id: int) -> Optional[tuple]:
    return conn.execute(
        "SELECT id, origin, company_name, company_entity_id, founder_entity_id, deck_path, "
        "status, first_signal_at, submitted_at, screened_at, screen_reason, outbound_signal_id "
        "FROM applications WHERE id = ?",
        (application_id,),
    ).fetchone()


def set_screen_result(
    conn: sqlite3.Connection, application_id: int, status: str, reason: str
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE applications SET status = ?, screened_at = ?, screen_reason = ? WHERE id = ?",
        (status, now, reason, application_id),
    )
    conn.commit()

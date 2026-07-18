import sqlite3
from datetime import datetime, timezone
from typing import Optional


def create_entity(conn: sqlite3.Connection, entity_type: str, canonical_name: str) -> int:
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO entities (type, canonical_name, created_at) VALUES (?, ?, ?)",
        (entity_type, canonical_name, now),
    )
    conn.commit()
    return cursor.lastrowid


def add_identifier(
    conn: sqlite3.Connection, entity_id: int, identifier_type: str, identifier_value: str
) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO entity_identifiers (entity_id, identifier_type, identifier_value) "
        "VALUES (?, ?, ?)",
        (entity_id, identifier_type, identifier_value),
    )
    conn.commit()


def find_entity_by_identifier(
    conn: sqlite3.Connection, identifier_type: str, identifier_value: str
) -> Optional[int]:
    row = conn.execute(
        "SELECT entity_id FROM entity_identifiers WHERE identifier_type = ? AND identifier_value = ?",
        (identifier_type, identifier_value),
    ).fetchone()
    return row[0] if row else None

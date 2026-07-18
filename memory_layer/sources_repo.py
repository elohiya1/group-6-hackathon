import sqlite3

from .config import get_source_reliability


def get_or_create_source(conn: sqlite3.Connection, source_name: str) -> int:
    row = conn.execute("SELECT id FROM sources WHERE name = ?", (source_name,)).fetchone()
    if row:
        return row[0]
    weight = get_source_reliability(source_name)
    cursor = conn.execute(
        "INSERT INTO sources (name, reliability_weight) VALUES (?, ?)",
        (source_name, weight),
    )
    conn.commit()
    return cursor.lastrowid

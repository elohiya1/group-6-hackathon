import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from .config import get_conviction_threshold


def scan_for_signals(
    conn: sqlite3.Connection, *, conviction_threshold: Optional[float] = None
) -> List[int]:
    """Outbound Identify step. Scores every founder in Memory the same way an
    inbound application would be (via the Founder Score) and logs a new
    outbound_signal for anyone crossing the conviction threshold who doesn't
    already have one — each founder is only surfaced for outreach once."""
    threshold = (
        conviction_threshold if conviction_threshold is not None else get_conviction_threshold()
    )
    rows = conn.execute(
        "SELECT entity_id, score FROM founder_scores WHERE score >= ?", (threshold,)
    ).fetchall()

    new_signal_ids = []
    for entity_id, score in rows:
        existing = conn.execute(
            "SELECT id FROM outbound_signals WHERE entity_id = ?", (entity_id,)
        ).fetchone()
        if existing:
            continue
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            "INSERT INTO outbound_signals (entity_id, conviction_score, detected_at, status) "
            "VALUES (?, ?, ?, 'identified')",
            (entity_id, score, now),
        )
        conn.commit()
        new_signal_ids.append(cursor.lastrowid)
    return new_signal_ids

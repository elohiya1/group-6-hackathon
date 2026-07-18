import sqlite3
from datetime import datetime, timezone


def _draft_outreach_message(canonical_name: str) -> str:
    return (
        f"Hi {canonical_name} — we've been following your public work and think "
        "it could be a strong fit for our fund. Would you be open to a quick call? "
        "If so, we'd love a short application (deck + company name) so we can move fast."
    )


def activate_signal(
    conn: sqlite3.Connection, outbound_signal_id: int, *, channel: str = "email"
) -> int:
    """Outbound Activate step: cold outreach, not cold investment. Logs the
    outreach so it can be instrumented, and moves the signal to 'activated'
    so Converge knows it's eligible to become a real application."""
    row = conn.execute(
        "SELECT entity_id, status FROM outbound_signals WHERE id = ?", (outbound_signal_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No outbound_signal with id {outbound_signal_id}")
    entity_id, status = row
    if status != "identified":
        raise ValueError(
            f"outbound_signal {outbound_signal_id} is not pending activation (status={status})"
        )

    canonical_name = conn.execute(
        "SELECT canonical_name FROM entities WHERE id = ?", (entity_id,)
    ).fetchone()[0]
    message = _draft_outreach_message(canonical_name)
    now = datetime.now(timezone.utc).isoformat()

    cursor = conn.execute(
        "INSERT INTO activations (outbound_signal_id, entity_id, channel, message, activated_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (outbound_signal_id, entity_id, channel, message, now),
    )
    conn.execute(
        "UPDATE outbound_signals SET status = 'activated' WHERE id = ?", (outbound_signal_id,)
    )
    conn.commit()
    return cursor.lastrowid

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .applications_repo import get_application, set_screen_result
from .config import get_screen_config


def _find_recent_duplicate(
    conn: sqlite3.Connection, company_name: str, application_id: int, window_days: int
) -> Optional[int]:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    row = conn.execute(
        "SELECT id FROM applications WHERE company_name = ? AND id != ? AND submitted_at >= ? "
        "ORDER BY submitted_at ASC LIMIT 1",
        (company_name, application_id, cutoff),
    ).fetchone()
    return row[0] if row else None


def screen_application(conn: sqlite3.Connection, application_id: int) -> str:
    """Fast first-pass filter: removes clearly non-viable ideas before the
    Intelligence layer runs. Explicit, explainable heuristics only — this is
    a triage gate, not a scoring model."""
    app = get_application(conn, application_id)
    if app is None:
        raise ValueError(f"No application with id {application_id}")
    _, _origin, company_name, _company_id, _founder_id, deck_path, status, *_rest = app
    if status != "submitted":
        raise ValueError(f"application {application_id} already screened (status={status})")

    config = get_screen_config()
    reasons = []

    if not company_name or not company_name.strip():
        reasons.append("missing company name")

    deck_size = 0
    if deck_path and Path(deck_path).exists():
        deck_size = Path(deck_path).stat().st_size
    if deck_size < config["min_deck_bytes"]:
        reasons.append(f"deck too thin ({deck_size} bytes < {config['min_deck_bytes']})")

    duplicate_id = _find_recent_duplicate(
        conn, company_name, application_id, config["duplicate_window_days"]
    )
    if duplicate_id is not None:
        reasons.append(
            f"duplicate of application {duplicate_id} within {config['duplicate_window_days']}d"
        )

    result_status = "screened_fail" if reasons else "screened_pass"
    reason_text = "; ".join(reasons) if reasons else "passed fast screen"
    set_screen_result(conn, application_id, result_status, reason_text)
    return result_status

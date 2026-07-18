import json
import sqlite3
from datetime import datetime, timezone
from typing import List, Optional


def set_thesis(
    conn: sqlite3.Connection,
    *,
    sectors: List[str],
    stage: str,
    geography: List[str],
    check_size_min: float,
    check_size_max: float,
    ownership_target_pct: float,
    risk_appetite: str,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO thesis "
        "(id, sectors, stage, geography, check_size_min, check_size_max, "
        " ownership_target_pct, risk_appetite, updated_at) "
        "VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(id) DO UPDATE SET "
        "sectors = excluded.sectors, stage = excluded.stage, geography = excluded.geography, "
        "check_size_min = excluded.check_size_min, check_size_max = excluded.check_size_max, "
        "ownership_target_pct = excluded.ownership_target_pct, "
        "risk_appetite = excluded.risk_appetite, updated_at = excluded.updated_at",
        (
            json.dumps(sectors),
            stage,
            json.dumps(geography),
            check_size_min,
            check_size_max,
            ownership_target_pct,
            risk_appetite,
            now,
        ),
    )
    conn.commit()


def get_thesis(conn: sqlite3.Connection) -> Optional[dict]:
    row = conn.execute(
        "SELECT sectors, stage, geography, check_size_min, check_size_max, "
        "ownership_target_pct, risk_appetite, updated_at FROM thesis WHERE id = 1"
    ).fetchone()
    if row is None:
        return None
    sectors, stage, geography, check_min, check_max, ownership, risk, updated_at = row
    return {
        "sectors": json.loads(sectors),
        "stage": stage,
        "geography": json.loads(geography),
        "check_size_min": check_min,
        "check_size_max": check_max,
        "ownership_target_pct": ownership,
        "risk_appetite": risk,
        "updated_at": updated_at,
    }

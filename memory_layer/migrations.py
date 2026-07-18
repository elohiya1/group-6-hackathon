import sqlite3

from .entity_resolution import COMPANY_IDENTIFIER_TYPES


def retype_companies(conn: sqlite3.Connection) -> int:
    """Retype entities as 'company' if they carry a company-indicating
    identifier but are still typed 'founder' -- covers entities created
    before a given identifier_type was added to COMPANY_IDENTIFIER_TYPES.
    Safe to re-run; returns the number of entities updated.
    """
    placeholders = ",".join("?" for _ in COMPANY_IDENTIFIER_TYPES)
    rows = conn.execute(
        f"SELECT DISTINCT entity_id FROM entity_identifiers "
        f"WHERE identifier_type IN ({placeholders})",
        tuple(COMPANY_IDENTIFIER_TYPES),
    ).fetchall()
    entity_ids = [r[0] for r in rows]
    if not entity_ids:
        return 0

    id_placeholders = ",".join("?" for _ in entity_ids)
    cursor = conn.execute(
        f"UPDATE entities SET type = 'company' "
        f"WHERE id IN ({id_placeholders}) AND type != 'company'",
        tuple(entity_ids),
    )
    conn.commit()
    return cursor.rowcount

import sqlite3
from typing import List, Optional, Tuple

VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_founder_scores_latest AS
SELECT e.id AS entity_id, e.canonical_name, fs.score, fs.coverage, fs.computed_at
FROM founder_scores fs
JOIN entities e ON e.id = fs.entity_id;

CREATE VIEW IF NOT EXISTS v_data_points_with_confidence AS
SELECT dp.id, dp.entity_id, e.canonical_name, dp.attribute_name, dp.value,
       dp.confidence_score, dp.confidence_tier, dp.observed_at, s.name AS source_name
FROM data_points dp
JOIN entities e ON e.id = dp.entity_id
JOIN sources s ON s.id = dp.source_id;

CREATE VIEW IF NOT EXISTS v_contradictions_open AS
SELECT c.id, c.entity_id, e.canonical_name, c.attribute_name, c.description, c.detected_at
FROM contradictions c
JOIN entities e ON e.id = c.entity_id;

CREATE VIEW IF NOT EXISTS v_needs_review AS
SELECT rr.id AS raw_record_id, s.name AS source_name, rr.raw_payload, rr.ingested_at
FROM raw_records rr
JOIN sources s ON s.id = rr.source_id
WHERE rr.resolution_status = 'needs_review';
"""


def create_views(conn: sqlite3.Connection) -> None:
    conn.executescript(VIEWS_SQL)
    conn.commit()


def get_founder_score(conn: sqlite3.Connection, entity_id: int) -> Optional[Tuple[float, str, str]]:
    return conn.execute(
        "SELECT score, coverage, computed_at FROM founder_scores WHERE entity_id = ?",
        (entity_id,),
    ).fetchone()


def get_data_points(
    conn: sqlite3.Connection, entity_id: int, attribute: Optional[str] = None
) -> List[tuple]:
    if attribute:
        return conn.execute(
            "SELECT attribute_name, value, confidence_score, confidence_tier, source_id "
            "FROM data_points WHERE entity_id = ? AND attribute_name = ?",
            (entity_id, attribute),
        ).fetchall()
    return conn.execute(
        "SELECT attribute_name, value, confidence_score, confidence_tier, source_id "
        "FROM data_points WHERE entity_id = ?",
        (entity_id,),
    ).fetchall()

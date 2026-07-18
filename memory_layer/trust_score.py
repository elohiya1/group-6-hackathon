import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .config import get_attribute_config


def _values_agree(value_type: str, value_a: str, value_b: str, numeric_tolerance: float) -> bool:
    if value_type == "numeric":
        a, b = float(value_a), float(value_b)
        if a == 0 and b == 0:
            return True
        denominator = max(abs(a), abs(b))
        return abs(a - b) / denominator <= numeric_tolerance
    return value_a.strip().lower() == value_b.strip().lower()


def compute_trust_scores(
    conn: sqlite3.Connection,
    entity_id: int,
    attribute_name: str,
    now: Optional[datetime] = None,
) -> None:
    attribute_config = get_attribute_config(attribute_name)
    rows = conn.execute(
        "SELECT dp.id, dp.value, dp.observed_at, dp.created_at, s.reliability_weight "
        "FROM data_points dp JOIN sources s ON dp.source_id = s.id "
        "WHERE dp.entity_id = ? AND dp.attribute_name = ?",
        (entity_id, attribute_name),
    ).fetchall()

    if not rows:
        return

    conn.execute(
        "DELETE FROM contradictions WHERE entity_id = ? AND attribute_name = ?",
        (entity_id, attribute_name),
    )

    tolerance = attribute_config.numeric_tolerance or 0.0

    for dp_id, value, _observed_at, _created_at, reliability in rows:
        comparable = [other for other in rows if other[0] != dp_id]
        agreeing = [
            o for o in comparable if _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]
        conflicting = [
            o for o in comparable if not _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]

        if agreeing:
            reliabilities = [reliability] + [o[4] for o in agreeing]
            base_score = sum(reliabilities) / len(reliabilities)
            bonus = min(0.05 * len(agreeing), 0.2)
            score = min(base_score + bonus, 1.0)
            tier = "corroborated"
        elif conflicting:
            score = min([reliability] + [o[4] for o in conflicting])
            tier = "contradicted"
        else:
            score = reliability
            tier = "insufficient_data"

        conn.execute(
            "UPDATE data_points SET confidence_score = ?, confidence_tier = ? WHERE id = ?",
            (score, tier, dp_id),
        )

        for other in conflicting:
            if other[0] > dp_id:
                conn.execute(
                    "INSERT INTO contradictions "
                    "(entity_id, attribute_name, data_point_id_a, data_point_id_b, detected_at, description) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entity_id,
                        attribute_name,
                        dp_id,
                        other[0],
                        datetime.now(timezone.utc).isoformat(),
                        f"{attribute_name}: '{value}' conflicts with '{other[1]}'",
                    ),
                )

    conn.commit()

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


def _as_of(observed_at: Optional[str], created_at: str) -> datetime:
    raw = observed_at or created_at
    return datetime.fromisoformat(raw)


def _decay_factor(age_days: float, half_life_days: Optional[float]) -> float:
    if not half_life_days or half_life_days <= 0:
        return 1.0
    return 0.5 ** (age_days / half_life_days)


def compute_trust_scores(
    conn: sqlite3.Connection,
    entity_id: int,
    attribute_name: str,
    now: Optional[datetime] = None,
) -> None:
    """Recomputes confidence_score/confidence_tier for every data_point
    belonging to (entity_id, attribute_name), and rewrites any detected
    contradictions. Idempotent.

    For `decaying` attributes, two data points are only compared for
    agreement/contradiction if their as-of timestamps fall within
    `recency_window_days` of each other (older observations are treated as
    separate trend snapshots, not competing claims), and reliability is
    scaled down with age using `half_life_days`. `static` attributes ignore
    both rules entirely.
    """
    now = now or datetime.now(timezone.utc)
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
    is_decaying = attribute_config.temporal_behavior == "decaying"

    as_of = {r[0]: _as_of(r[2], r[3]) for r in rows}
    decayed_reliability = {}
    for dp_id, _value, _observed_at, _created_at, reliability in rows:
        age_days = max((now - as_of[dp_id]).total_seconds() / 86400, 0.0)
        decayed_reliability[dp_id] = (
            reliability * _decay_factor(age_days, attribute_config.half_life_days)
            if is_decaying
            else reliability
        )

    for dp_id, value, _observed_at, _created_at, _reliability in rows:
        comparable = [other for other in rows if other[0] != dp_id]
        if is_decaying:
            window = attribute_config.recency_window_days or 0
            comparable = [
                other
                for other in comparable
                if abs((as_of[dp_id] - as_of[other[0]]).total_seconds() / 86400) <= window
            ]

        agreeing = [
            o for o in comparable if _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]
        conflicting = [
            o for o in comparable if not _values_agree(attribute_config.value_type, value, o[1], tolerance)
        ]

        this_reliability = decayed_reliability[dp_id]

        if agreeing:
            reliabilities = [this_reliability] + [decayed_reliability[o[0]] for o in agreeing]
            base_score = sum(reliabilities) / len(reliabilities)
            bonus = min(0.05 * len(agreeing), 0.2)
            score = min(base_score + bonus, 1.0)
            tier = "corroborated"
        elif conflicting:
            score = min([this_reliability] + [decayed_reliability[o[0]] for o in conflicting])
            tier = "contradicted"
        else:
            score = this_reliability
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

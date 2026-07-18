import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

CONFIG_PATH = Path(__file__).parent / "config" / "founder_score.yaml"


def _load_categories() -> Dict[str, dict]:
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def compute_founder_score(conn: sqlite3.Connection, entity_id: int) -> float:
    """Recomputes the founder's score from their current data_points,
    renormalizing over whichever signal categories actually have data
    (missing categories are excluded, not zeroed), and appends a row to
    founder_score_history. Returns the computed score (0-100)."""
    categories = _load_categories()

    category_scores: List[Tuple[float, float]] = []  # (weight, avg_confidence * 100)
    for config in categories.values():
        attribute_names = config["attributes"]
        placeholders = ",".join("?" for _ in attribute_names)
        rows = conn.execute(
            f"SELECT confidence_score FROM data_points "
            f"WHERE entity_id = ? AND attribute_name IN ({placeholders}) "
            f"AND confidence_score IS NOT NULL",
            (entity_id, *attribute_names),
        ).fetchall()
        if not rows:
            continue
        avg_confidence = sum(r[0] for r in rows) / len(rows)
        category_scores.append((config["weight"], avg_confidence * 100))

    total_categories = len(categories)
    covered_categories = len(category_scores)

    if covered_categories == 0:
        score = 0.0
    else:
        total_weight = sum(w for w, _ in category_scores)
        score = sum(w * s for w, s in category_scores) / total_weight

    coverage = f"{covered_categories}/{total_categories}"
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO founder_scores (entity_id, score, coverage, computed_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(entity_id) DO UPDATE SET "
        "score = excluded.score, coverage = excluded.coverage, computed_at = excluded.computed_at",
        (entity_id, score, coverage, now),
    )
    conn.execute(
        "INSERT INTO founder_score_history (entity_id, score, coverage, computed_at) VALUES (?, ?, ?, ?)",
        (entity_id, score, coverage, now),
    )
    conn.commit()
    return score

import json
import sqlite3
from datetime import datetime
from typing import Optional

from funnel.applications_repo import get_application
from memory_layer.founder_score import _load_categories
from memory_layer.query import get_founder_score

# --- shared helpers -----------------------------------------------------


def _hours_between(start_iso: Optional[str], end_iso: Optional[str]) -> Optional[int]:
    if not start_iso or not end_iso:
        return None
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso)
    return round((end - start).total_seconds() / 3600.0)


def get_identifiers(conn: sqlite3.Connection, entity_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT identifier_type, identifier_value FROM entity_identifiers WHERE entity_id = ?",
        (entity_id,),
    ).fetchall()
    return [{"type": r[0], "value": r[1]} for r in rows]


def get_data_points_full(conn: sqlite3.Connection, entity_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT dp.id, dp.attribute_name, dp.value, dp.confidence_score, dp.confidence_tier, "
        "s.name, s.reliability_weight, dp.observed_at "
        "FROM data_points dp JOIN sources s ON s.id = dp.source_id "
        "WHERE dp.entity_id = ? ORDER BY dp.id",
        (entity_id,),
    ).fetchall()
    return [
        {
            "id": r[0],
            "attribute_name": r[1],
            "value": r[2],
            "confidence_score": r[3],
            "confidence_tier": r[4],
            "source_name": r[5],
            "source_reliability": r[6],
            "observed_at": r[7],
        }
        for r in rows
    ]


def get_contradictions_full(conn: sqlite3.Connection, entity_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT c.id, c.attribute_name, "
        "da.value, sa.name, db_.value, sb.name, c.description, c.detected_at "
        "FROM contradictions c "
        "JOIN data_points da ON da.id = c.data_point_id_a "
        "JOIN sources sa ON sa.id = da.source_id "
        "JOIN data_points db_ ON db_.id = c.data_point_id_b "
        "JOIN sources sb ON sb.id = db_.source_id "
        "WHERE c.entity_id = ? ORDER BY c.id",
        (entity_id,),
    ).fetchall()
    return [
        {
            "id": r[0],
            "attribute_name": r[1],
            "value_a": r[2],
            "source_a": r[3],
            "value_b": r[4],
            "source_b": r[5],
            "description": r[6],
            "detected_at": r[7],
        }
        for r in rows
    ]


def get_score_history(conn: sqlite3.Connection, entity_id: int) -> list[dict]:
    rows = conn.execute(
        "SELECT score, coverage, computed_at FROM founder_score_history "
        "WHERE entity_id = ? ORDER BY computed_at ASC",
        (entity_id,),
    ).fetchall()
    return [{"score": r[0], "coverage": r[1], "computed_at": r[2]} for r in rows]


def get_category_coverage(conn: sqlite3.Connection, entity_id: int) -> list[dict]:
    categories = _load_categories()
    out = []
    for category_name, config in categories.items():
        attribute_names = config["attributes"]
        placeholders = ",".join("?" for _ in attribute_names)
        rows = conn.execute(
            f"SELECT DISTINCT attribute_name FROM data_points "
            f"WHERE entity_id = ? AND attribute_name IN ({placeholders}) "
            f"AND confidence_score IS NOT NULL",
            (entity_id, *attribute_names),
        ).fetchall()
        covered = [r[0] for r in rows]
        out.append(
            {
                "category": category_name,
                "weight": config["weight"],
                "has_data": len(covered) > 0,
                "attribute_names": covered,
            }
        )
    return out


def build_founder(conn: sqlite3.Connection, entity_id: int, canonical_name: str) -> dict:
    score_row = get_founder_score(conn, entity_id)
    founder_score = (
        {"score": score_row[0], "coverage": score_row[1], "computed_at": score_row[2]}
        if score_row is not None
        else None
    )
    return {
        "entity_id": entity_id,
        "canonical_name": canonical_name,
        "founder_score": founder_score,
        "score_history": get_score_history(conn, entity_id),
        "category_coverage": get_category_coverage(conn, entity_id),
        "data_points": get_data_points_full(conn, entity_id),
        "contradictions": get_contradictions_full(conn, entity_id),
        "identifiers": get_identifiers(conn, entity_id),
    }


def build_company(conn: sqlite3.Connection, entity_id: int, canonical_name: str) -> dict:
    return {
        "entity_id": entity_id,
        "canonical_name": canonical_name,
        "type": "company",
        "data_points": get_data_points_full(conn, entity_id),
        "identifiers": get_identifiers(conn, entity_id),
    }


def compute_recommendation(
    thesis_fit: Optional[dict], axes: Optional[list[dict]], trust_flags_open: int
) -> Optional[dict]:
    """Ports the exact deterministic rule the frontend used to compute this
    client-side, so investor and founder views keep agreeing now that both
    read it from the server instead."""
    if thesis_fit is None or axes is None:
        return None
    has_bear = any(a["rating"] == "bear" for a in axes)
    has_bullish = any(a["rating"] == "bullish" for a in axes)
    derivation = (
        "invest = thesis_fit.in_thesis AND no axis bear AND trust_flags_open = 0; "
        "needs_review = axes disagree (bullish AND bear) OR trust_flags_open > 0; else pass."
    )
    if thesis_fit["in_thesis"] and not has_bear and trust_flags_open == 0:
        return {
            "verdict": "invest",
            "rationale": "In thesis, no axis rated bear, no open trust flags. Deterministic invest.",
            "derivation": derivation,
        }
    if (has_bullish and has_bear) or trust_flags_open > 0:
        rationale = (
            f"{trust_flags_open} open trust flag(s) block a clean call."
            if trust_flags_open > 0
            else "Axes disagree — at least one bullish and one bear signal."
        )
        return {"verdict": "needs_review", "rationale": rationale, "derivation": derivation}
    rationale = (
        "In thesis but a bear axis without offsetting bullish evidence."
        if thesis_fit["in_thesis"]
        else "Out of thesis and no bullish/bear conflict to warrant review."
    )
    return {"verdict": "pass", "rationale": rationale, "derivation": derivation}


def get_axis_scores(conn: sqlite3.Connection, application_id: int) -> Optional[list[dict]]:
    rows = conn.execute(
        "SELECT axis, rating, score, rationale, trend, computed_at FROM axis_scores "
        "WHERE application_id = ? ORDER BY "
        "CASE axis WHEN 'founder' THEN 0 WHEN 'market' THEN 1 ELSE 2 END",
        (application_id,),
    ).fetchall()
    if not rows:
        return None
    return [
        {
            "axis": r[0],
            "rating": r[1],
            "score": r[2],
            "rationale": r[3],
            "trend": r[4],
            "computed_at": r[5],
        }
        for r in rows
    ]


def get_thesis_fit(conn: sqlite3.Connection, application_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT in_thesis, rationale, computed_at FROM thesis_fit WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    if row is None:
        return None
    return {"in_thesis": bool(row[0]), "rationale": row[1], "computed_at": row[2]}


def get_memo(conn: sqlite3.Connection, application_id: int) -> Optional[dict]:
    row = conn.execute(
        "SELECT company_snapshot, investment_hypotheses, swot, problem_and_product, "
        "traction_and_kpis, gaps_flagged, model_used, generated_at "
        "FROM investment_memos WHERE application_id = ?",
        (application_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "company_snapshot": row[0],
        "investment_hypotheses": json.loads(row[1]),
        "swot": json.loads(row[2]),
        "problem_and_product": row[3],
        "traction_and_kpis": row[4],
        "gaps_flagged": json.loads(row[5]),
        "model_used": row[6],
        "generated_at": row[7],
    }


def count_open_trust_flags(conn: sqlite3.Connection, entity_ids: list[Optional[int]]) -> int:
    total = 0
    for entity_id in entity_ids:
        if entity_id is None:
            continue
        row = conn.execute(
            "SELECT COUNT(*) FROM contradictions WHERE entity_id = ?", (entity_id,)
        ).fetchone()
        total += row[0]
    return total


def build_opportunity(conn: sqlite3.Connection, application_id: int) -> Optional[dict]:
    app = get_application(conn, application_id)
    if app is None:
        return None
    (
        app_id,
        origin,
        company_name,
        company_entity_id,
        founder_entity_id,
        _deck_path,
        status,
        first_signal_at,
        submitted_at,
        screened_at,
        screen_reason,
        _outbound_signal_id,
    ) = app

    founder = None
    if founder_entity_id is not None:
        canonical_name = conn.execute(
            "SELECT canonical_name FROM entities WHERE id = ?", (founder_entity_id,)
        ).fetchone()[0]
        founder = build_founder(conn, founder_entity_id, canonical_name)

    thesis_fit = get_thesis_fit(conn, app_id)
    axes = get_axis_scores(conn, app_id)
    memo = get_memo(conn, app_id)
    memo_generated_at = memo["generated_at"] if memo else None
    trust_flags_open = count_open_trust_flags(conn, [founder_entity_id, company_entity_id])
    recommendation = compute_recommendation(thesis_fit, axes, trust_flags_open)

    return {
        "application_id": app_id,
        "origin": origin,
        "company_name": company_name,
        "founder": founder,
        "status": status,
        "screen_reason": screen_reason,
        "first_signal_at": first_signal_at,
        "submitted_at": submitted_at,
        "screened_at": screened_at,
        "hours_to_screen": _hours_between(first_signal_at, screened_at),
        "memo_generated_at": memo_generated_at,
        "hours_to_decision": _hours_between(first_signal_at, memo_generated_at),
        "thesis_fit": thesis_fit,
        "axes": axes,
        "memo": memo,
        "recommendation": recommendation,
        "trust_flags_open": trust_flags_open,
    }


def list_application_ids(conn: sqlite3.Connection) -> list[int]:
    rows = conn.execute("SELECT id FROM applications ORDER BY id DESC").fetchall()
    return [r[0] for r in rows]

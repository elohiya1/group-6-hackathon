import sqlite3
from pathlib import Path
from typing import List, Optional

from funnel.applications_repo import get_application
from memory_layer.query import get_data_points, get_founder_score


def _read_deck_text(deck_path: Optional[str], max_chars: int = 8000) -> Optional[str]:
    if not deck_path:
        return None
    path = Path(deck_path)
    if not path.exists():
        return None
    try:
        text = path.read_text(errors="ignore")
    except OSError:
        return None
    return text[:max_chars]


def _open_contradictions(conn: sqlite3.Connection, entity_id: Optional[int]) -> List[dict]:
    if entity_id is None:
        return []
    rows = conn.execute(
        "SELECT attribute_name, description, detected_at FROM contradictions WHERE entity_id = ?",
        (entity_id,),
    ).fetchall()
    return [{"attribute_name": r[0], "description": r[1], "detected_at": r[2]} for r in rows]


def _points(conn: sqlite3.Connection, entity_id: Optional[int]) -> List[dict]:
    if entity_id is None:
        return []
    return [
        {
            "attribute_name": p[0],
            "value": p[1],
            "confidence_score": p[2],
            "confidence_tier": p[3],
        }
        for p in get_data_points(conn, entity_id)
    ]


def gather_evidence(conn: sqlite3.Connection, application_id: int) -> dict:
    """Assembles everything the Intelligence layer needs to reason about an
    opportunity: the application itself, deck text, the founder's persistent
    Founder Score, and every data_point for both founder and company entities
    with its Trust Score confidence tier and any open contradictions -- so
    the model reasons over evidence already flagged as corroborated,
    contradicted, or thin, rather than treating every claim as equally
    solid."""
    app = get_application(conn, application_id)
    if app is None:
        raise ValueError(f"No application with id {application_id}")
    (
        _id,
        origin,
        company_name,
        company_entity_id,
        founder_entity_id,
        deck_path,
        status,
        first_signal_at,
        submitted_at,
        _screened_at,
        _screen_reason,
        _outbound_signal_id,
    ) = app

    founder_score = None
    if founder_entity_id is not None:
        row = get_founder_score(conn, founder_entity_id)
        if row is not None:
            founder_score = {"score": row[0], "coverage": row[1], "computed_at": row[2]}

    return {
        "application": {
            "id": application_id,
            "origin": origin,
            "company_name": company_name,
            "status": status,
            "first_signal_at": first_signal_at,
            "submitted_at": submitted_at,
        },
        "deck_text": _read_deck_text(deck_path),
        "founder_score": founder_score,
        "founder_data_points": _points(conn, founder_entity_id),
        "company_data_points": _points(conn, company_entity_id),
        "contradictions": (
            _open_contradictions(conn, founder_entity_id)
            + _open_contradictions(conn, company_entity_id)
        ),
    }

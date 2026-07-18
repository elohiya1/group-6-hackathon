import json
import sqlite3
from datetime import datetime, timezone
from typing import Dict, Optional

from .evidence import gather_evidence
from .openai_client import chat_json
from .thesis_repo import get_thesis

AXES = ("founder", "market", "idea_vs_market")

TREND_THRESHOLD = 5.0

AXIS_SYSTEM_PROMPTS = {
    "founder": (
        "You are a venture capital analyst scoring the FOUNDER axis: who they "
        "are, their traits, and their track record. The Founder Score in the "
        "evidence is one input, not a substitute for your own judgment -- "
        "weigh it alongside the founder's data points and any contradictions. "
    ),
    "market": (
        "You are a venture capital analyst scoring the MARKET axis: market "
        "sizing, competitors, and a SWOT-style read on the market this "
        "company operates in. "
    ),
    "idea_vs_market": (
        "You are a venture capital analyst scoring the IDEA-VS-MARKET axis: "
        "does the idea, as it stands today, survive scrutiny against this "
        "market -- or is the team strong enough to pivot if it doesn't? "
    ),
}

JSON_INSTRUCTION = (
    "This axis must be judged independently of the other two axes -- do not "
    "let it drift toward an overall average. Do not fabricate facts not "
    "present in the evidence; name what's missing instead of guessing. "
    'Respond with strict JSON: {"rating": "bullish"|"neutral"|"bear", '
    '"score": number from 0 to 100, "rationale": string}.'
)


def _compute_trend(conn: sqlite3.Connection, application_id: int, axis: str, new_score: float) -> str:
    row = conn.execute(
        "SELECT score FROM axis_score_history WHERE application_id = ? AND axis = ? "
        "ORDER BY computed_at DESC LIMIT 1",
        (application_id, axis),
    ).fetchone()
    if row is None:
        return "stable"
    previous_score = row[0]
    if new_score - previous_score >= TREND_THRESHOLD:
        return "improving"
    if previous_score - new_score >= TREND_THRESHOLD:
        return "declining"
    return "stable"


def score_axis(
    conn: sqlite3.Connection,
    application_id: int,
    axis: str,
    *,
    thesis: Optional[dict] = None,
    evidence: Optional[dict] = None,
) -> dict:
    if axis not in AXES:
        raise ValueError(f"Unknown axis: {axis}")
    thesis = thesis if thesis is not None else get_thesis(conn)
    evidence = evidence if evidence is not None else gather_evidence(conn, application_id)

    system_prompt = AXIS_SYSTEM_PROMPTS[axis] + JSON_INSTRUCTION
    user_prompt = json.dumps({"thesis": thesis, "evidence": evidence})
    result = chat_json(system_prompt, user_prompt)

    trend = _compute_trend(conn, application_id, axis, result["score"])
    now = datetime.now(timezone.utc).isoformat()

    conn.execute(
        "INSERT INTO axis_scores "
        "(application_id, axis, rating, score, rationale, trend, computed_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(application_id, axis) DO UPDATE SET "
        "rating = excluded.rating, score = excluded.score, rationale = excluded.rationale, "
        "trend = excluded.trend, computed_at = excluded.computed_at",
        (application_id, axis, result["rating"], result["score"], result["rationale"], trend, now),
    )
    conn.execute(
        "INSERT INTO axis_score_history (application_id, axis, rating, score, computed_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (application_id, axis, result["rating"], result["score"], now),
    )
    conn.commit()

    return {**result, "trend": trend}


def score_all_axes(
    conn: sqlite3.Connection, application_id: int, *, thesis: Optional[dict] = None
) -> Dict[str, dict]:
    """Scores all three axes independently -- never averaged into one
    number, so an investor can see exactly where the axes disagree."""
    thesis = thesis if thesis is not None else get_thesis(conn)
    evidence = gather_evidence(conn, application_id)
    return {
        axis: score_axis(conn, application_id, axis, thesis=thesis, evidence=evidence)
        for axis in AXES
    }

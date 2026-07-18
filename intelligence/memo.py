import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .evidence import gather_evidence
from .openai_client import DEFAULT_MODEL, chat_json
from .thesis_repo import get_thesis

SYSTEM_PROMPT = (
    "You are a venture capital analyst writing an investment memo to support "
    "a $100K check decision that a human investor must be able to act on "
    "within 24 hours. Be as detailed as the decision requires and as brief "
    "as clarity allows -- padding counts against you. Never fabricate "
    "missing data: if something is not disclosed or not evidenced, name it "
    "explicitly (e.g. 'Cap table: not disclosed') instead of guessing or "
    "silently omitting it. "
    "Respond with strict JSON using exactly these keys: "
    '"company_snapshot" (string: one paragraph -- market size, structural '
    "problem, urgency, how the product solves it), "
    '"investment_hypotheses" (array of strings: explicit why-we-want-to-invest '
    "bullets -- team quality, market wedge, stickiness/retention, traction "
    "signal, defensibility, expansion path), "
    '"swot" (object with "strengths", "weaknesses", "opportunities", "risks" '
    "arrays of short evidence-backed strings), "
    '"problem_and_product" (string: the core problem in plain language, then '
    "the product/process solving it), "
    '"traction_and_kpis" (string: customer count, revenue, growth, unit '
    "economics, usage metrics -- or explicit gaps where unavailable), "
    '"gaps_flagged" (array of strings naming each piece of missing or '
    "undisclosed data referenced above)."
)


def generate_memo(
    conn: sqlite3.Connection,
    application_id: int,
    *,
    thesis: Optional[dict] = None,
    axis_scores: Optional[dict] = None,
) -> dict:
    thesis = thesis if thesis is not None else get_thesis(conn)
    evidence = gather_evidence(conn, application_id)
    if axis_scores is None:
        rows = conn.execute(
            "SELECT axis, rating, score, rationale, trend FROM axis_scores WHERE application_id = ?",
            (application_id,),
        ).fetchall()
        axis_scores = {
            r[0]: {"rating": r[1], "score": r[2], "rationale": r[3], "trend": r[4]} for r in rows
        }

    user_prompt = json.dumps({"thesis": thesis, "evidence": evidence, "axis_scores": axis_scores})
    result = chat_json(SYSTEM_PROMPT, user_prompt, model=DEFAULT_MODEL)

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO investment_memos "
        "(application_id, company_snapshot, investment_hypotheses, swot, "
        " problem_and_product, traction_and_kpis, gaps_flagged, model_used, generated_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(application_id) DO UPDATE SET "
        "company_snapshot = excluded.company_snapshot, "
        "investment_hypotheses = excluded.investment_hypotheses, "
        "swot = excluded.swot, problem_and_product = excluded.problem_and_product, "
        "traction_and_kpis = excluded.traction_and_kpis, gaps_flagged = excluded.gaps_flagged, "
        "model_used = excluded.model_used, generated_at = excluded.generated_at",
        (
            application_id,
            result["company_snapshot"],
            json.dumps(result["investment_hypotheses"]),
            json.dumps(result["swot"]),
            result["problem_and_product"],
            result["traction_and_kpis"],
            json.dumps(result["gaps_flagged"]),
            DEFAULT_MODEL,
            now,
        ),
    )
    conn.commit()
    return result

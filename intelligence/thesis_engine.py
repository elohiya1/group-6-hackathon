import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from .evidence import gather_evidence
from .openai_client import chat_json
from .thesis_repo import get_thesis

SYSTEM_PROMPT = (
    "You are a venture capital thesis-fit screener. Given a fund's investment "
    "thesis and the evidence gathered on one opportunity, decide whether it "
    "fits the thesis. Do not fabricate facts not present in the evidence; if "
    "evidence needed to judge fit is missing, say so in the rationale rather "
    "than assuming. Respond with strict JSON: "
    '{"in_thesis": boolean, "rationale": string}.'
)


def check_thesis_fit(
    conn: sqlite3.Connection,
    application_id: int,
    *,
    thesis: Optional[dict] = None,
    evidence: Optional[dict] = None,
) -> dict:
    thesis = thesis if thesis is not None else get_thesis(conn)
    if thesis is None:
        raise ValueError("No thesis configured -- call thesis_repo.set_thesis first")
    evidence = evidence if evidence is not None else gather_evidence(conn, application_id)

    user_prompt = json.dumps({"thesis": thesis, "evidence": evidence})
    result = chat_json(SYSTEM_PROMPT, user_prompt)

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO thesis_fit (application_id, in_thesis, rationale, computed_at) "
        "VALUES (?, ?, ?, ?) "
        "ON CONFLICT(application_id) DO UPDATE SET "
        "in_thesis = excluded.in_thesis, rationale = excluded.rationale, "
        "computed_at = excluded.computed_at",
        (application_id, 1 if result["in_thesis"] else 0, result["rationale"], now),
    )
    conn.commit()
    return result

import sqlite3
from typing import List

from .axis_scoring import score_all_axes
from .memo import generate_memo
from .thesis_engine import check_thesis_fit
from .thesis_repo import get_thesis


def run_intelligence(conn: sqlite3.Connection, application_id: int) -> dict:
    """The full Intelligence pass for one opportunity that has cleared
    Screening: Thesis fit, all three axes (never averaged), then the memo.
    Out-of-thesis opportunities still get scored and memoed -- the Thesis
    Engine informs the analysis, it doesn't silently hide opportunities from
    the investor."""
    thesis = get_thesis(conn)
    thesis_fit = check_thesis_fit(conn, application_id, thesis=thesis)
    axis_scores = score_all_axes(conn, application_id, thesis=thesis)
    memo = generate_memo(conn, application_id, thesis=thesis, axis_scores=axis_scores)
    return {"thesis_fit": thesis_fit, "axis_scores": axis_scores, "memo": memo}


def run_pending(conn: sqlite3.Connection) -> List[int]:
    """Consumes v_intelligence_pending -- every screened_pass application
    that doesn't already have a memo, whether it arrived inbound or
    converged from an outbound signal. Excluding already-memoed
    applications matters because applications.status stays 'screened_pass'
    forever (Screening has no concept of "decided"); without this filter,
    re-running this on a schedule would silently reprocess -- and re-bill --
    every opportunity every time."""
    rows = conn.execute("SELECT application_id FROM v_intelligence_pending").fetchall()
    processed = []
    for (application_id,) in rows:
        run_intelligence(conn, application_id)
        processed.append(application_id)
    return processed

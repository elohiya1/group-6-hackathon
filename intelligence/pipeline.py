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
    """Consumes the funnel's v_intelligence_queue view -- every screened_pass
    application is this layer's trigger condition, whether it arrived
    inbound or converged from an outbound signal."""
    rows = conn.execute("SELECT application_id FROM v_intelligence_queue").fetchall()
    processed = []
    for (application_id,) in rows:
        run_intelligence(conn, application_id)
        processed.append(application_id)
    return processed

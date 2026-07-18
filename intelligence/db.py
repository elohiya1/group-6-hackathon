import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS thesis (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    sectors TEXT NOT NULL,
    stage TEXT NOT NULL,
    geography TEXT NOT NULL,
    check_size_min REAL NOT NULL,
    check_size_max REAL NOT NULL,
    ownership_target_pct REAL NOT NULL,
    risk_appetite TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS thesis_fit (
    application_id INTEGER PRIMARY KEY REFERENCES applications(id),
    in_thesis INTEGER NOT NULL CHECK (in_thesis IN (0, 1)),
    rationale TEXT NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS axis_scores (
    application_id INTEGER NOT NULL REFERENCES applications(id),
    axis TEXT NOT NULL CHECK (axis IN ('founder', 'market', 'idea_vs_market')),
    rating TEXT NOT NULL CHECK (rating IN ('bullish', 'neutral', 'bear')),
    score REAL NOT NULL,
    rationale TEXT NOT NULL,
    trend TEXT NOT NULL CHECK (trend IN ('improving', 'declining', 'stable')),
    computed_at TEXT NOT NULL,
    PRIMARY KEY (application_id, axis)
);

CREATE TABLE IF NOT EXISTS axis_score_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    application_id INTEGER NOT NULL REFERENCES applications(id),
    axis TEXT NOT NULL,
    rating TEXT NOT NULL,
    score REAL NOT NULL,
    computed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS investment_memos (
    application_id INTEGER PRIMARY KEY REFERENCES applications(id),
    company_snapshot TEXT NOT NULL,
    investment_hypotheses TEXT NOT NULL,
    swot TEXT NOT NULL,
    problem_and_product TEXT NOT NULL,
    traction_and_kpis TEXT NOT NULL,
    gaps_flagged TEXT NOT NULL,
    model_used TEXT NOT NULL,
    generated_at TEXT NOT NULL
);
"""

VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_decision_ready AS
SELECT m.application_id, a.company_name, a.origin, tf.in_thesis, m.generated_at
FROM investment_memos m
JOIN applications a ON a.id = m.application_id
LEFT JOIN thesis_fit tf ON tf.application_id = m.application_id;

CREATE VIEW IF NOT EXISTS v_decision_latency AS
SELECT a.id AS application_id, a.origin, a.first_signal_at, m.generated_at AS decided_at,
       (julianday(m.generated_at) - julianday(a.first_signal_at)) * 24.0 AS hours_to_decision
FROM applications a
JOIN investment_memos m ON m.application_id = a.id;

CREATE VIEW IF NOT EXISTS v_intelligence_pending AS
SELECT q.application_id, q.origin, q.company_name, q.founder_entity_id, q.company_entity_id,
       q.deck_path, q.first_signal_at, q.submitted_at
FROM v_intelligence_queue q
LEFT JOIN investment_memos m ON m.application_id = q.application_id
WHERE m.application_id IS NULL;
"""


def init_intelligence_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.executescript(VIEWS_SQL)
    conn.commit()

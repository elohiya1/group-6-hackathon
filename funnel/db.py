import sqlite3

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS outbound_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    conviction_score REAL NOT NULL,
    detected_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('identified', 'activated', 'converged')
    ) DEFAULT 'identified'
);

CREATE TABLE IF NOT EXISTS activations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    outbound_signal_id INTEGER NOT NULL REFERENCES outbound_signals(id),
    entity_id INTEGER NOT NULL REFERENCES entities(id),
    channel TEXT NOT NULL,
    message TEXT NOT NULL,
    activated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    origin TEXT NOT NULL CHECK (origin IN ('inbound', 'outbound')),
    company_name TEXT NOT NULL,
    company_entity_id INTEGER REFERENCES entities(id),
    founder_entity_id INTEGER REFERENCES entities(id),
    deck_path TEXT,
    status TEXT NOT NULL CHECK (
        status IN ('submitted', 'screened_pass', 'screened_fail')
    ),
    first_signal_at TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    screened_at TEXT,
    screen_reason TEXT,
    outbound_signal_id INTEGER REFERENCES outbound_signals(id)
);
"""

VIEWS_SQL = """
CREATE VIEW IF NOT EXISTS v_pending_screen AS
SELECT id AS application_id, origin, company_name, first_signal_at, submitted_at
FROM applications
WHERE status = 'submitted';

CREATE VIEW IF NOT EXISTS v_intelligence_queue AS
SELECT id AS application_id, origin, company_name, founder_entity_id, company_entity_id,
       deck_path, first_signal_at, submitted_at
FROM applications
WHERE status = 'screened_pass';

CREATE VIEW IF NOT EXISTS v_funnel_latency AS
SELECT id AS application_id, origin, status, first_signal_at, screened_at,
       (julianday(screened_at) - julianday(first_signal_at)) * 24.0 AS hours_to_screen
FROM applications
WHERE screened_at IS NOT NULL;
"""


def init_funnel_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_SQL)
    conn.executescript(VIEWS_SQL)
    conn.commit()

import os
import sqlite3
import threading
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

from funnel.db import init_funnel_schema
from intelligence.db import init_intelligence_schema
from memory_layer.db import SCHEMA_SQL
from memory_layer.query import create_views

load_dotenv()

DB_PATH = os.environ.get("VC_BRAIN_DB_PATH", "data/vc_brain.db")

# FastAPI runs sync route handlers in a threadpool, so a single sqlite3
# connection needs check_same_thread=False plus this lock serializing access
# -- fine for a local single-user demo, and avoids interleaved-cursor bugs
# that plain check_same_thread=False doesn't protect against.
db_lock = threading.Lock()

_conn: Optional[sqlite3.Connection] = None


def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        create_views(conn)
        init_funnel_schema(conn)
        init_intelligence_schema(conn)
        _conn = conn
    return _conn

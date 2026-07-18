import hashlib
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from .entity_resolution import resolve_raw_record
from .normalize import normalize_raw_record
from .sources_repo import get_or_create_source


def _content_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def ingest_file(conn: sqlite3.Connection, source_name: str, file_path: Path) -> Optional[int]:
    raw_bytes = file_path.read_bytes()
    content_hash = _content_hash(raw_bytes)

    existing = conn.execute(
        "SELECT id FROM raw_records WHERE content_hash = ?", (content_hash,)
    ).fetchone()
    if existing:
        return None

    source_id = get_or_create_source(conn, source_name)
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, ?, ?, 'needs_review')",
        (source_id, raw_bytes.decode("utf-8"), content_hash, str(file_path), now),
    )
    conn.commit()
    return cursor.lastrowid


def run_ingestion(conn: sqlite3.Connection, incoming_dir: Path, processed_dir: Path) -> List[int]:
    """Ingest -> resolve -> normalize every *.json file under incoming_dir/<source>/.

    Stops at normalization (structured, deduplicated, source-tagged data_points).
    Trust Score and Founder Score computation are a downstream concern, owned
    elsewhere, and are not run here.
    """
    ingested_ids: List[int] = []
    if not incoming_dir.exists():
        return ingested_ids

    for source_dir in sorted(p for p in incoming_dir.iterdir() if p.is_dir()):
        source_name = source_dir.name
        for file_path in sorted(source_dir.glob("*.json")):
            raw_record_id = ingest_file(conn, source_name, file_path)

            if raw_record_id is not None:
                ingested_ids.append(raw_record_id)
                status = resolve_raw_record(conn, raw_record_id)
                if status in ("resolved", "new_entity"):
                    normalize_raw_record(conn, raw_record_id)

            dest_dir = processed_dir / source_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            shutil.move(str(file_path), str(dest_dir / file_path.name))

    return ingested_ids

import json
import sqlite3
from datetime import datetime, timezone

from .config import get_attribute_config
from .source_mappings import extract_field, load_source_mapping


def normalize_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> int:
    row = conn.execute(
        "SELECT raw_payload, source_id, entity_id, resolution_status FROM raw_records WHERE id = ?",
        (raw_record_id,),
    ).fetchone()
    if row is None:
        raise ValueError(f"No raw_record with id {raw_record_id}")
    raw_payload, source_id, entity_id, resolution_status = row
    if resolution_status not in ("resolved", "new_entity") or entity_id is None:
        return 0

    payload = json.loads(raw_payload)
    source_name = conn.execute("SELECT name FROM sources WHERE id = ?", (source_id,)).fetchone()[0]
    mapping = load_source_mapping(source_name)

    observed_at = payload.get("observed_at")
    created_at = datetime.now(timezone.utc).isoformat()

    created_count = 0
    for rule in mapping.attributes:
        value = extract_field(payload, rule.raw_field)
        if value is None:
            continue
        attribute_config = get_attribute_config(rule.attribute_name)
        conn.execute(
            "INSERT INTO data_points "
            "(entity_id, raw_record_id, source_id, attribute_name, value, value_type, "
            " observed_at, created_at, confidence_score, confidence_tier) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL)",
            (
                entity_id,
                raw_record_id,
                source_id,
                rule.attribute_name,
                str(value),
                attribute_config.value_type,
                observed_at,
                created_at,
            ),
        )
        created_count += 1
    conn.commit()
    return created_count

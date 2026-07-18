import json
import sqlite3
from typing import List, Tuple, Union

from .entities_repo import add_identifier, create_entity, find_entity_by_identifier
from .source_mappings import extract_field, load_source_mapping


def _load_payload_and_source(conn: sqlite3.Connection, raw_record_id: int) -> Tuple[dict, str]:
    row = conn.execute(
        "SELECT raw_payload, source_id FROM raw_records WHERE id = ?", (raw_record_id,)
    ).fetchone()
    if row is None:
        raise ValueError(f"No raw_record with id {raw_record_id}")
    raw_payload, source_id = row
    payload = json.loads(raw_payload)
    source_name = conn.execute("SELECT name FROM sources WHERE id = ?", (source_id,)).fetchone()[0]
    return payload, source_name


def _extract_identifiers(payload: dict, source_name: str) -> List[Tuple[str, str]]:
    mapping = load_source_mapping(source_name)
    extracted = []
    for rule in mapping.identifiers:
        value = extract_field(payload, rule.raw_field)
        if value is not None:
            extracted.append((rule.identifier_type, str(value)))
    return extracted


def _infer_entity_type(identifiers: List[Tuple[str, str]]) -> str:
    identifier_types = {t for t, _ in identifiers}
    return "company" if "company_domain" in identifier_types else "founder"


def resolve_raw_record(conn: sqlite3.Connection, raw_record_id: int) -> str:
    payload, source_name = _load_payload_and_source(conn, raw_record_id)
    extracted = _extract_identifiers(payload, source_name)

    matched_entity_ids = set()
    for identifier_type, identifier_value in extracted:
        entity_id = find_entity_by_identifier(conn, identifier_type, identifier_value)
        if entity_id is not None:
            matched_entity_ids.add(entity_id)

    if len(matched_entity_ids) > 1:
        conn.execute(
            "UPDATE raw_records SET entity_id = NULL, resolution_status = 'needs_review' WHERE id = ?",
            (raw_record_id,),
        )
        conn.commit()
        return "needs_review"

    if len(matched_entity_ids) == 1:
        entity_id = matched_entity_ids.pop()
        status = "resolved"
    else:
        entity_type = _infer_entity_type(extracted)
        canonical_name = str(payload.get("name", "unknown"))
        entity_id = create_entity(conn, entity_type, canonical_name)
        status = "new_entity"

    for identifier_type, identifier_value in extracted:
        add_identifier(conn, entity_id, identifier_type, identifier_value)

    conn.execute(
        "UPDATE raw_records SET entity_id = ?, resolution_status = ? WHERE id = ?",
        (entity_id, status, raw_record_id),
    )
    conn.commit()
    return status

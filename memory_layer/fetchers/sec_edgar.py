from pathlib import Path
from typing import List

from .common import get_json, write_incoming

SEC_EDGAR_FULL_TEXT_SEARCH_API = "https://efts.sec.gov/LATEST/search-index"


def fetch_sec_form_d(
    incoming_dir: Path, query: str = "", limit: int = 25, contact_email: str = ""
) -> List[Path]:
    headers = {"User-Agent": f"VC-Brain-Hackathon {contact_email}".strip()}
    data = get_json(
        SEC_EDGAR_FULL_TEXT_SEARCH_API,
        params={"q": query, "forms": "D"},
        headers=headers,
    )

    written: List[Path] = []
    hits = data.get("hits", {}).get("hits", [])
    for hit in hits[:limit]:
        source = hit.get("_source", {})
        ciks = source.get("ciks") or ([source["cik"]] if source.get("cik") else [])
        display_names = source.get("display_names") or []
        payload = {
            "name": display_names[0] if display_names else None,
            "cik": ciks[0] if ciks else None,
            "display_names": display_names,
            "file_date": source.get("file_date"),
            "form_type": source.get("form") or source.get("form_type"),
        }
        if not payload["cik"]:
            continue
        slug = hit.get("_id") or payload["cik"]
        path = write_incoming(incoming_dir, "sec_edgar", slug, payload)
        written.append(path)
    return written

import json
from pathlib import Path
from typing import List

from .common import get_json, get_patentsview_api_key, write_incoming

PATENTSVIEW_API = "https://search.patentsview.org/api/v1/patent/"


def fetch_patents(incoming_dir: Path, query: dict, limit: int = 25) -> List[Path]:
    api_key = get_patentsview_api_key()
    if not api_key:
        raise RuntimeError(
            "PATENTSVIEW_API_KEY is not set — PatentsView requires a free registered API key"
        )

    data = get_json(
        PATENTSVIEW_API,
        params={
            "q": json.dumps(query),
            "f": json.dumps(["patent_id", "patent_title", "patent_date", "inventors"]),
        },
        headers={"X-Api-Key": api_key},
    )

    written: List[Path] = []
    for patent in data.get("patents", []):
        if len(written) >= limit:
            break
        inventors = patent.get("inventors") or []
        for inventor in inventors:
            if len(written) >= limit:
                break
            inventor_name = " ".join(
                part
                for part in [inventor.get("inventor_name_first"), inventor.get("inventor_name_last")]
                if part
            )
            if not inventor_name:
                continue
            payload = {
                "name": inventor_name,
                "inventor_name": inventor_name,
                "patent_id": patent.get("patent_id"),
                "patent_title": patent.get("patent_title"),
                "patent_date": patent.get("patent_date"),
                "patents_filed": "1",
            }
            slug = f"{patent.get('patent_id')}_{inventor_name}"
            path = write_incoming(incoming_dir, "patents", slug, payload)
            written.append(path)
    return written

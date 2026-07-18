from pathlib import Path
from typing import List

from .common import get_json, write_incoming

OPENALEX_API = "https://api.openalex.org/works"


def fetch_openalex(incoming_dir: Path, search: str, max_results: int = 25) -> List[Path]:
    data = get_json(
        OPENALEX_API,
        params={"search": search, "sort": "publication_date:desc", "per-page": max_results},
    )

    written: List[Path] = []
    for work in data.get("results", [])[:max_results]:
        authorships = work.get("authorships") or []
        if not authorships:
            continue
        first_author = authorships[0].get("author") or {}
        author_id = first_author.get("id")
        author_name = first_author.get("display_name")
        if not author_id:
            continue

        payload = {
            "name": author_name,
            "work_id": work.get("id"),
            "title": work.get("title"),
            "publication_date": work.get("publication_date"),
            "first_author_id": author_id,
            "first_author_name": author_name,
        }
        slug = work.get("id") or work.get("title") or "work"
        path = write_incoming(incoming_dir, "openalex", slug, payload)
        written.append(path)
    return written

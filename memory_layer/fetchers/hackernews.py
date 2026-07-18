from pathlib import Path
from typing import List

from .common import get_json, write_incoming

HN_ALGOLIA_API = "https://hn.algolia.com/api/v1/search"


def fetch_show_hn(incoming_dir: Path, query: str = "Show HN", limit: int = 50) -> List[Path]:
    data = get_json(
        HN_ALGOLIA_API,
        params={"query": query, "tags": "show_hn", "hitsPerPage": limit},
    )

    written: List[Path] = []
    for hit in data.get("hits", [])[:limit]:
        payload = {"name": hit.get("author"), **hit}
        slug = hit.get("objectID") or hit.get("title", "item")
        path = write_incoming(incoming_dir, "hackernews", slug, payload)
        written.append(path)
    return written

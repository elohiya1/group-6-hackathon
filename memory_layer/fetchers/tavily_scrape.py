from pathlib import Path
from typing import List

from .common import get_tavily_api_key, post_json, write_incoming

TAVILY_SEARCH_API = "https://api.tavily.com/search"


def fetch_via_tavily(
    incoming_dir: Path, source_name: str, queries: List[str], max_results: int = 5
) -> List[Path]:
    api_key = get_tavily_api_key()

    written: List[Path] = []
    for query in queries:
        data = post_json(
            TAVILY_SEARCH_API,
            payload={"api_key": api_key, "query": query, "max_results": max_results},
        )
        for result in data.get("results", [])[:max_results]:
            payload = {
                "name": result.get("title"),
                "query": query,
                "url": result.get("url"),
                "title": result.get("title"),
                "content": result.get("content"),
                "score": result.get("score"),
            }
            slug = payload["url"] or payload["title"] or "result"
            path = write_incoming(incoming_dir, source_name, slug, payload)
            written.append(path)
    return written

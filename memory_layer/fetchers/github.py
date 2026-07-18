from pathlib import Path
from typing import List

from .common import get_github_token, get_json, write_incoming

GITHUB_API = "https://api.github.com"


def fetch_github(incoming_dir: Path, topics: List[str], per_topic_limit: int = 10) -> List[Path]:
    token = get_github_token()
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    written: List[Path] = []
    for topic in topics:
        data = get_json(
            f"{GITHUB_API}/search/repositories",
            params={
                "q": f"topic:{topic}",
                "sort": "stars",
                "order": "desc",
                "per_page": per_topic_limit,
            },
            headers=headers,
        )
        for repo in data.get("items", [])[:per_topic_limit]:
            path = write_incoming(incoming_dir, "github", repo["full_name"], repo)
            written.append(path)
    return written

from pathlib import Path
from typing import List

from .common import get_json, write_incoming

REDDIT_USER_AGENT = "vc-brain-hackathon-sourcing/1.0"


def fetch_reddit(
    incoming_dir: Path, subreddits: List[str], query: str, limit: int = 25
) -> List[Path]:
    headers = {"User-Agent": REDDIT_USER_AGENT}

    written: List[Path] = []
    for subreddit in subreddits:
        data = get_json(
            f"https://www.reddit.com/r/{subreddit}/search.json",
            params={"q": query, "restrict_sr": 1, "sort": "new", "limit": limit},
            headers=headers,
        )
        children = data.get("data", {}).get("children", [])
        for child in children[:limit]:
            post = child.get("data", {})
            author = post.get("author")
            if not author or author == "[deleted]":
                continue
            payload = {
                "name": author,
                "author": author,
                "title": post.get("title"),
                "score": post.get("score"),
                "num_comments": post.get("num_comments"),
                "url": post.get("url"),
                "subreddit": post.get("subreddit"),
                "created_utc": post.get("created_utc"),
            }
            slug = post.get("id") or post.get("title", "post")
            path = write_incoming(incoming_dir, "reddit", slug, payload)
            written.append(path)
    return written

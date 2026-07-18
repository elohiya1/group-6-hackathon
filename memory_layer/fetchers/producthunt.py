from pathlib import Path
from typing import List

from .common import get_producthunt_token, post_json, write_incoming

PRODUCTHUNT_API = "https://api.producthunt.com/v2/api/graphql"

POSTS_QUERY = """
query ($first: Int!) {
  posts(first: $first, order: VOTES) {
    edges {
      node {
        id
        name
        tagline
        votesCount
        website
        makers {
          username
          name
        }
      }
    }
  }
}
"""


def fetch_producthunt(incoming_dir: Path, limit: int = 50) -> List[Path]:
    token = get_producthunt_token()
    if not token:
        raise RuntimeError(
            "PRODUCTHUNT_TOKEN is not set — Product Hunt fetcher requires a developer token"
        )

    data = post_json(
        PRODUCTHUNT_API,
        payload={"query": POSTS_QUERY, "variables": {"first": limit}},
        headers={"Authorization": f"Bearer {token}"},
    )

    written: List[Path] = []
    edges = data.get("data", {}).get("posts", {}).get("edges", [])
    for edge in edges[:limit]:
        node = edge["node"]
        makers = node.get("makers") or []
        if not makers:
            continue
        maker = makers[0]
        payload = {
            "post_id": node["id"],
            "name": node.get("name"),
            "tagline": node.get("tagline"),
            "votes_count": node.get("votesCount"),
            "website": node.get("website"),
            "maker_username": maker.get("username"),
            "maker_name": maker.get("name"),
        }
        path = write_incoming(incoming_dir, "producthunt", node["id"], payload)
        written.append(path)
    return written

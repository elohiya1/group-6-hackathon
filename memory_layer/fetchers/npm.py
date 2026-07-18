from pathlib import Path
from typing import List

from .common import get_json, write_incoming

NPM_SEARCH_API = "https://registry.npmjs.org/-/v1/search"


def fetch_npm(incoming_dir: Path, query: str, limit: int = 20) -> List[Path]:
    data = get_json(NPM_SEARCH_API, params={"text": query, "size": limit})

    written: List[Path] = []
    for obj in data.get("objects", [])[:limit]:
        package = obj.get("package", {})
        author = package.get("author") or {}
        maintainers = package.get("maintainers") or []
        first_maintainer = maintainers[0] if maintainers else {}

        email = author.get("email") or first_maintainer.get("email")
        if not email:
            continue

        name = author.get("name") or first_maintainer.get("username")
        popularity = obj.get("score", {}).get("detail", {}).get("popularity")

        payload = {
            "name": name,
            "package_name": package.get("name"),
            "description": package.get("description"),
            "maintainer_email": email,
            "popularity_score": popularity,
            "links": package.get("links"),
        }
        path = write_incoming(incoming_dir, "npm", package.get("name", "package"), payload)
        written.append(path)
    return written

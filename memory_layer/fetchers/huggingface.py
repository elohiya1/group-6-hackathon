from pathlib import Path
from typing import List

from .common import get_json, write_incoming

HUGGINGFACE_API = "https://huggingface.co/api/models"


def fetch_huggingface(incoming_dir: Path, search: str, limit: int = 20) -> List[Path]:
    items = get_json(
        HUGGINGFACE_API,
        params={"search": search, "sort": "downloads", "direction": -1, "limit": limit},
    )

    written: List[Path] = []
    for item in items[:limit]:
        model_id = item.get("id", "")
        author = item.get("author") or (model_id.split("/")[0] if "/" in model_id else None)
        if not author:
            continue
        payload = {
            "name": author,
            "author": author,
            "model_id": model_id,
            "downloads": item.get("downloads"),
            "likes": item.get("likes"),
            "tags": item.get("tags"),
            "created_at": item.get("createdAt"),
        }
        path = write_incoming(incoming_dir, "huggingface", model_id, payload)
        written.append(path)
    return written

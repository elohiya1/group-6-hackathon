import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, Optional

import requests
from dotenv import load_dotenv

_env_loaded = False


def _ensure_env_loaded() -> None:
    global _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True


def get_tavily_api_key() -> str:
    _ensure_env_loaded()
    key = os.environ.get("TAVILY_API_KEY")
    if not key:
        raise RuntimeError("TAVILY_API_KEY is not set (expected in .env)")
    return key


def get_github_token() -> Optional[str]:
    _ensure_env_loaded()
    return os.environ.get("GITHUB_TOKEN")


def get_producthunt_token() -> Optional[str]:
    _ensure_env_loaded()
    return os.environ.get("PRODUCTHUNT_TOKEN")


def get_patentsview_api_key() -> Optional[str]:
    _ensure_env_loaded()
    return os.environ.get("PATENTSVIEW_API_KEY")


def get_companies_house_api_key() -> Optional[str]:
    _ensure_env_loaded()
    return os.environ.get("COMPANIES_HOUSE_API_KEY")


def get_opencorporates_api_key() -> Optional[str]:
    _ensure_env_loaded()
    return os.environ.get("OPENCORPORATES_API_KEY")


def get_json(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    auth: Optional[tuple] = None,
    timeout: int = 15,
    retries: int = 2,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(
                url, params=params, headers=headers, auth=auth, timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise last_error


def get_text(
    url: str,
    params: Optional[dict] = None,
    headers: Optional[dict] = None,
    timeout: int = 15,
    retries: int = 2,
) -> str:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise last_error


def post_json(
    url: str,
    payload: dict,
    headers: Optional[dict] = None,
    timeout: int = 30,
    retries: int = 2,
) -> Dict[str, Any]:
    last_error: Optional[Exception] = None
    for attempt in range(retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))
    raise last_error


def safe_slug(raw: str, max_length: int = 80) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", raw).strip("_")
    return (slug or "item")[:max_length]


def write_incoming(incoming_dir: Path, source_name: str, slug: str, payload: dict) -> Path:
    source_dir = Path(incoming_dir) / source_name
    source_dir.mkdir(parents=True, exist_ok=True)
    file_path = source_dir / f"{safe_slug(slug)}.json"
    file_path.write_text(json.dumps(payload, indent=2))
    return file_path

import json
import os
from typing import Optional

from dotenv import load_dotenv
from openai import OpenAI

DEFAULT_MODEL = "gpt-4.1-mini"

_env_loaded = False
_client: Optional[OpenAI] = None


def _ensure_env_loaded() -> None:
    global _env_loaded
    if not _env_loaded:
        load_dotenv()
        _env_loaded = True


def get_openai_api_key() -> str:
    _ensure_env_loaded()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set (expected in .env)")
    return key


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=get_openai_api_key())
    return _client


def chat_json(system_prompt: str, user_prompt: str, *, model: Optional[str] = None) -> dict:
    """Single call-site for every OpenAI request in the Intelligence layer, so
    tests can mock exactly one function instead of the SDK internals."""
    client = _get_client()
    response = client.chat.completions.create(
        model=model or os.environ.get("OPENAI_MODEL", DEFAULT_MODEL),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return json.loads(response.choices[0].message.content)

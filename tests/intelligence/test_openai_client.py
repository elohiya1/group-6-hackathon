import json
from unittest.mock import MagicMock, patch

import pytest

from intelligence.openai_client import chat_json, get_openai_api_key


def test_get_openai_api_key_raises_without_key(monkeypatch):
    import intelligence.openai_client as openai_client_module

    # Force-skip the real dotenv load so this test doesn't depend on whether
    # a local .env happens to define OPENAI_API_KEY on this machine.
    monkeypatch.setattr(openai_client_module, "_env_loaded", True)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        get_openai_api_key()


def test_chat_json_parses_response_content(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    import intelligence.openai_client as openai_client_module

    openai_client_module._client = None

    fake_response = MagicMock()
    fake_response.choices = [MagicMock(message=MagicMock(content=json.dumps({"ok": True})))]

    with patch("intelligence.openai_client.OpenAI") as MockOpenAI:
        MockOpenAI.return_value.chat.completions.create.return_value = fake_response
        result = chat_json("system prompt", "user prompt")

    assert result == {"ok": True}
    openai_client_module._client = None

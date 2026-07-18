import json
from unittest.mock import Mock, patch

import pytest
import requests

from memory_layer.fetchers.common import (
    get_companies_house_api_key,
    get_github_token,
    get_json,
    get_opencorporates_api_key,
    get_patentsview_api_key,
    get_producthunt_token,
    get_tavily_api_key,
    get_text,
    safe_slug,
    write_incoming,
)


def test_write_incoming_creates_file_with_json_payload(tmp_path):
    path = write_incoming(tmp_path, "github", "octocat/hello-world", {"a": 1})
    assert path.exists()
    assert path.parent.name == "github"
    assert json.loads(path.read_text()) == {"a": 1}


def test_safe_slug_strips_unsafe_characters():
    assert safe_slug("octocat/hello-world!") == "octocat_hello-world"


def test_safe_slug_empty_falls_back():
    assert safe_slug("///") == "item"


def test_get_tavily_api_key_present(monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-123")
    assert get_tavily_api_key() == "tvly-test-123"


def test_get_tavily_api_key_missing_raises(monkeypatch):
    monkeypatch.delenv("TAVILY_API_KEY", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        with pytest.raises(RuntimeError):
            get_tavily_api_key()


def test_get_github_token_optional(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        assert get_github_token() is None


def test_get_producthunt_token_optional(monkeypatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        assert get_producthunt_token() is None


def test_get_patentsview_api_key_optional(monkeypatch):
    monkeypatch.delenv("PATENTSVIEW_API_KEY", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        assert get_patentsview_api_key() is None


def test_get_companies_house_api_key_optional(monkeypatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        assert get_companies_house_api_key() is None


def test_get_opencorporates_api_key_optional(monkeypatch):
    monkeypatch.delenv("OPENCORPORATES_API_KEY", raising=False)
    with patch("memory_layer.fetchers.common.load_dotenv"):
        assert get_opencorporates_api_key() is None


def test_get_json_returns_parsed_body():
    mock_response = Mock()
    mock_response.json.return_value = {"ok": True}
    mock_response.raise_for_status.return_value = None
    with patch("requests.get", return_value=mock_response) as mock_get:
        result = get_json("https://example.com/api", params={"q": "x"})
    assert result == {"ok": True}
    mock_get.assert_called_once()


def test_get_json_retries_then_raises():
    with patch("requests.get", side_effect=requests.exceptions.ConnectionError("down")):
        with patch("time.sleep"):
            with pytest.raises(requests.exceptions.ConnectionError):
                get_json("https://example.com/api", retries=1)


def test_get_text_returns_response_body():
    mock_response = Mock()
    mock_response.text = "<xml>ok</xml>"
    mock_response.raise_for_status.return_value = None
    with patch("requests.get", return_value=mock_response):
        result = get_text("https://example.com/feed")
    assert result == "<xml>ok</xml>"

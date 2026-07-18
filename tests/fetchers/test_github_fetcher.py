import json
from unittest.mock import patch

from memory_layer.fetchers.github import fetch_github

FAKE_SEARCH_RESPONSE = {
    "items": [
        {
            "full_name": "adalovelace/analytical-engine",
            "name": "analytical-engine",
            "owner": {"login": "adalovelace"},
            "stargazers_count": 500,
        },
        {
            "full_name": "gracehopper/compiler",
            "name": "compiler",
            "owner": {"login": "gracehopper"},
            "stargazers_count": 300,
        },
    ]
}


def test_fetch_github_writes_one_file_per_repo(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with patch(
        "memory_layer.fetchers.github.get_json", return_value=FAKE_SEARCH_RESPONSE
    ) as mock_get_json:
        paths = fetch_github(tmp_path, topics=["ai"], per_topic_limit=10)

    assert len(paths) == 2
    for path in paths:
        assert path.parent.name == "github"
        assert path.exists()

    written = json.loads(paths[0].read_text())
    assert written["owner"]["login"] == "adalovelace"
    assert written["stargazers_count"] == 500

    called_headers = mock_get_json.call_args.kwargs["headers"]
    assert "Authorization" not in called_headers


def test_fetch_github_respects_per_topic_limit(tmp_path):
    with patch("memory_layer.fetchers.github.get_json", return_value=FAKE_SEARCH_RESPONSE):
        paths = fetch_github(tmp_path, topics=["ai"], per_topic_limit=1)
    assert len(paths) == 1


def test_fetch_github_adds_auth_header_when_token_present(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test123")
    with patch(
        "memory_layer.fetchers.github.get_json", return_value=FAKE_SEARCH_RESPONSE
    ) as mock_get_json:
        fetch_github(tmp_path, topics=["ai"], per_topic_limit=10)

    called_headers = mock_get_json.call_args.kwargs["headers"]
    assert called_headers["Authorization"] == "Bearer ghp_test123"


def test_fetch_github_queries_each_topic(tmp_path):
    with patch(
        "memory_layer.fetchers.github.get_json", return_value={"items": []}
    ) as mock_get_json:
        fetch_github(tmp_path, topics=["ai", "hackathon"], per_topic_limit=5)
    assert mock_get_json.call_count == 2

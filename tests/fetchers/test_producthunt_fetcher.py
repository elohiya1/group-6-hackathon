import json
from unittest.mock import patch

import pytest

from memory_layer.fetchers.producthunt import fetch_producthunt

FAKE_GRAPHQL_RESPONSE = {
    "data": {
        "posts": {
            "edges": [
                {
                    "node": {
                        "id": "post-1",
                        "name": "FounderScore",
                        "tagline": "Credit score for founders",
                        "votesCount": 240,
                        "website": "https://example.com",
                        "makers": [{"username": "adalovelace", "name": "Ada Lovelace"}],
                    }
                },
                {
                    "node": {
                        "id": "post-2",
                        "name": "No Maker Listed",
                        "tagline": "Edge case",
                        "votesCount": 5,
                        "website": "https://example2.com",
                        "makers": [],
                    }
                },
            ]
        }
    }
}


def test_fetch_producthunt_raises_without_token(tmp_path, monkeypatch):
    monkeypatch.delenv("PRODUCTHUNT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        fetch_producthunt(tmp_path, limit=10)


def test_fetch_producthunt_writes_one_file_per_post_with_maker(tmp_path, monkeypatch):
    monkeypatch.setenv("PRODUCTHUNT_TOKEN", "ph-test-token")
    with patch(
        "memory_layer.fetchers.producthunt.post_json", return_value=FAKE_GRAPHQL_RESPONSE
    ) as mock_post_json:
        paths = fetch_producthunt(tmp_path, limit=10)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["maker_username"] == "adalovelace"
    assert written["votes_count"] == 240

    called_headers = mock_post_json.call_args.kwargs["headers"]
    assert called_headers["Authorization"] == "Bearer ph-test-token"

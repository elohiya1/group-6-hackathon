import json
from unittest.mock import patch

from memory_layer.fetchers.npm import fetch_npm

FAKE_NPM_RESPONSE = {
    "objects": [
        {
            "package": {
                "name": "founder-score-sdk",
                "description": "SDK for FounderScore",
                "author": {"name": "Ada Lovelace", "email": "ada@example.com"},
                "maintainers": [{"username": "adalovelace", "email": "ada@example.com"}],
                "links": {"npm": "https://npmjs.com/package/founder-score-sdk"},
            },
            "score": {"final": 0.8, "detail": {"popularity": 0.65}},
        },
        {
            "package": {
                "name": "no-author-pkg",
                "description": "No identifiable author",
                "maintainers": [],
            },
            "score": {"final": 0.1, "detail": {"popularity": 0.05}},
        },
    ]
}


def test_fetch_npm_writes_one_file_per_identifiable_package(tmp_path):
    with patch(
        "memory_layer.fetchers.npm.get_json", return_value=FAKE_NPM_RESPONSE
    ) as mock_get_json:
        paths = fetch_npm(tmp_path, query="ai", limit=20)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["maintainer_email"] == "ada@example.com"
    assert written["popularity_score"] == 0.65
    assert written["name"] == "Ada Lovelace"

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["text"] == "ai"


def test_fetch_npm_skips_packages_without_email(tmp_path):
    with patch(
        "memory_layer.fetchers.npm.get_json",
        return_value={"objects": [FAKE_NPM_RESPONSE["objects"][1]]},
    ):
        paths = fetch_npm(tmp_path, query="ai", limit=20)
    assert paths == []

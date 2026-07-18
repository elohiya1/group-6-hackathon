import json
from unittest.mock import patch

from memory_layer.fetchers.hackernews import fetch_show_hn

FAKE_HN_RESPONSE = {
    "hits": [
        {
            "objectID": "12345",
            "author": "adalovelace",
            "title": "Show HN: My AI startup",
            "url": "https://example.com",
            "points": 120,
            "num_comments": 34,
            "created_at": "2026-07-01T00:00:00.000Z",
        },
        {
            "objectID": "67890",
            "author": "gracehopper",
            "title": "Show HN: A compiler for humans",
            "url": "https://example2.com",
            "points": 80,
            "num_comments": 10,
            "created_at": "2026-07-02T00:00:00.000Z",
        },
    ]
}


def test_fetch_show_hn_writes_one_file_per_hit(tmp_path):
    with patch(
        "memory_layer.fetchers.hackernews.get_json", return_value=FAKE_HN_RESPONSE
    ) as mock_get_json:
        paths = fetch_show_hn(tmp_path, limit=50)

    assert len(paths) == 2
    for path in paths:
        assert path.parent.name == "hackernews"

    written = json.loads(paths[0].read_text())
    assert written["author"] == "adalovelace"
    assert written["points"] == 120
    assert written["name"] == "adalovelace"

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["tags"] == "show_hn"


def test_fetch_show_hn_respects_limit(tmp_path):
    with patch("memory_layer.fetchers.hackernews.get_json", return_value=FAKE_HN_RESPONSE):
        paths = fetch_show_hn(tmp_path, limit=1)
    assert len(paths) == 1

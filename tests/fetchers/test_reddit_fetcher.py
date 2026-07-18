import json
from unittest.mock import patch

from memory_layer.fetchers.reddit import fetch_reddit

FAKE_REDDIT_RESPONSE = {
    "data": {
        "children": [
            {
                "data": {
                    "id": "abc123",
                    "author": "adalovelace",
                    "title": "Launched my AI startup after 6 months of building",
                    "score": 245,
                    "num_comments": 40,
                    "url": "https://example.com",
                    "subreddit": "startups",
                    "created_utc": 1751328000,
                }
            },
            {
                "data": {
                    "id": "def456",
                    "author": "[deleted]",
                    "title": "Deleted post",
                    "score": 5,
                    "num_comments": 1,
                }
            },
        ]
    }
}


def test_fetch_reddit_writes_one_file_per_post_with_author(tmp_path):
    with patch(
        "memory_layer.fetchers.reddit.get_json", return_value=FAKE_REDDIT_RESPONSE
    ) as mock_get_json:
        paths = fetch_reddit(tmp_path, subreddits=["startups"], query="launched", limit=25)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["author"] == "adalovelace"
    assert written["score"] == 245
    assert written["name"] == "adalovelace"

    called_headers = mock_get_json.call_args.kwargs["headers"]
    assert "User-Agent" in called_headers


def test_fetch_reddit_skips_deleted_authors(tmp_path):
    with patch(
        "memory_layer.fetchers.reddit.get_json",
        return_value={"data": {"children": [FAKE_REDDIT_RESPONSE["data"]["children"][1]]}},
    ):
        paths = fetch_reddit(tmp_path, subreddits=["startups"], query="x", limit=25)
    assert paths == []


def test_fetch_reddit_queries_each_subreddit(tmp_path):
    with patch(
        "memory_layer.fetchers.reddit.get_json", return_value={"data": {"children": []}}
    ) as mock_get_json:
        fetch_reddit(tmp_path, subreddits=["startups", "SideProject"], query="ai", limit=10)
    assert mock_get_json.call_count == 2

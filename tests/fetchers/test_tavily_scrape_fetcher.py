import json
from unittest.mock import patch

from memory_layer.fetchers.tavily_scrape import fetch_via_tavily

FAKE_TAVILY_RESPONSE = {
    "query": "site:devpost.com AI hackathon winner 2026",
    "results": [
        {
            "url": "https://devpost.com/software/founderscore",
            "title": "FounderScore wins Best Use of AI",
            "content": "A team from MIT built FounderScore...",
            "score": 0.92,
        },
        {
            "url": "https://devpost.com/software/trustlayer",
            "title": "TrustLayer - Runner Up",
            "content": "TrustLayer helps investors...",
            "score": 0.81,
        },
    ],
}


def test_fetch_via_tavily_writes_one_file_per_result_tagged_with_source(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    with patch(
        "memory_layer.fetchers.tavily_scrape.post_json", return_value=FAKE_TAVILY_RESPONSE
    ) as mock_post_json:
        paths = fetch_via_tavily(
            tmp_path, "devpost", queries=["site:devpost.com AI hackathon winner 2026"], max_results=5
        )

    assert len(paths) == 2
    for path in paths:
        assert path.parent.name == "devpost"

    written = json.loads(paths[0].read_text())
    assert written["url"] == "https://devpost.com/software/founderscore"
    assert written["title"] == "FounderScore wins Best Use of AI"
    assert written["name"] == "FounderScore wins Best Use of AI"

    sent_payload = mock_post_json.call_args.kwargs["payload"]
    assert sent_payload["api_key"] == "tvly-test-key"
    assert sent_payload["query"] == "site:devpost.com AI hackathon winner 2026"


def test_fetch_via_tavily_respects_max_results(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    with patch(
        "memory_layer.fetchers.tavily_scrape.post_json", return_value=FAKE_TAVILY_RESPONSE
    ):
        paths = fetch_via_tavily(tmp_path, "devpost", queries=["query"], max_results=1)
    assert len(paths) == 1


def test_fetch_via_tavily_queries_multiple_times_for_multiple_sources(tmp_path, monkeypatch):
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    with patch(
        "memory_layer.fetchers.tavily_scrape.post_json", return_value=FAKE_TAVILY_RESPONSE
    ) as mock_post_json:
        fetch_via_tavily(
            tmp_path,
            "university_challenge",
            queries=["MIT delta v cohort", "StartX cohort"],
            max_results=5,
        )
    assert mock_post_json.call_count == 2

import json
from unittest.mock import patch

from memory_layer.fetchers.arxiv import fetch_arxiv

FAKE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2607.00001v1</id>
    <title>A Novel Approach to Founder Scoring</title>
    <published>2026-07-01T00:00:00Z</published>
    <author><name>Ada Lovelace</name></author>
    <author><name>Grace Hopper</name></author>
    <category term="cs.AI" />
    <category term="cs.LG" />
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2607.00002v1</id>
    <title>Trust Scores for Everyone</title>
    <published>2026-07-02T00:00:00Z</published>
    <author><name>Katherine Johnson</name></author>
    <category term="cs.AI" />
  </entry>
</feed>
"""


def test_fetch_arxiv_writes_one_file_per_entry(tmp_path):
    with patch(
        "memory_layer.fetchers.arxiv.get_text", return_value=FAKE_ATOM_FEED
    ) as mock_get_text:
        paths = fetch_arxiv(tmp_path, categories=["cs.AI", "cs.LG"], max_results=50)

    assert len(paths) == 2
    for path in paths:
        assert path.parent.name == "arxiv"

    written = json.loads(paths[0].read_text())
    assert written["title"] == "A Novel Approach to Founder Scoring"
    assert written["first_author"] == "Ada Lovelace"
    assert written["name"] == "Ada Lovelace"
    assert written["authors"] == ["Ada Lovelace", "Grace Hopper"]
    assert written["categories"] == ["cs.AI", "cs.LG"]

    call_params = mock_get_text.call_args.kwargs["params"]
    assert call_params["search_query"] == "cat:cs.AI OR cat:cs.LG"


def test_fetch_arxiv_respects_max_results(tmp_path):
    with patch("memory_layer.fetchers.arxiv.get_text", return_value=FAKE_ATOM_FEED):
        paths = fetch_arxiv(tmp_path, categories=["cs.AI"], max_results=1)
    assert len(paths) == 1


def test_fetch_arxiv_skips_entries_without_authors(tmp_path):
    feed_no_author = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <id>http://arxiv.org/abs/2607.00003v1</id>
    <title>Anonymous Paper</title>
    <published>2026-07-03T00:00:00Z</published>
  </entry>
</feed>
"""
    with patch("memory_layer.fetchers.arxiv.get_text", return_value=feed_no_author):
        paths = fetch_arxiv(tmp_path, categories=["cs.AI"], max_results=50)
    assert paths == []

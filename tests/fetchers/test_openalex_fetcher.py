import json
from unittest.mock import patch

from memory_layer.fetchers.openalex import fetch_openalex

FAKE_OPENALEX_RESPONSE = {
    "results": [
        {
            "id": "https://openalex.org/W111",
            "title": "Founder Scoring at Scale",
            "publication_date": "2026-07-01",
            "authorships": [
                {"author": {"id": "https://openalex.org/A111", "display_name": "Ada Lovelace"}}
            ],
        },
        {
            "id": "https://openalex.org/W222",
            "title": "Anonymous Preprint",
            "publication_date": "2026-07-02",
            "authorships": [],
        },
    ]
}


def test_fetch_openalex_writes_one_file_per_authored_work(tmp_path):
    with patch(
        "memory_layer.fetchers.openalex.get_json", return_value=FAKE_OPENALEX_RESPONSE
    ) as mock_get_json:
        paths = fetch_openalex(tmp_path, search="ai", max_results=25)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["first_author_id"] == "https://openalex.org/A111"
    assert written["name"] == "Ada Lovelace"
    assert written["title"] == "Founder Scoring at Scale"

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["search"] == "ai"


def test_fetch_openalex_skips_works_without_authors(tmp_path):
    with patch(
        "memory_layer.fetchers.openalex.get_json",
        return_value={"results": [FAKE_OPENALEX_RESPONSE["results"][1]]},
    ):
        paths = fetch_openalex(tmp_path, search="ai", max_results=25)
    assert paths == []

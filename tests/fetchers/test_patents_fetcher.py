import json
from unittest.mock import patch

import pytest

from memory_layer.fetchers.patents import fetch_patents

FAKE_PATENTSVIEW_RESPONSE = {
    "patents": [
        {
            "patent_id": "US1234567",
            "patent_title": "Method for Founder Scoring",
            "patent_date": "2026-01-01",
            "inventors": [
                {"inventor_name_first": "Ada", "inventor_name_last": "Lovelace"},
                {"inventor_name_first": "Grace", "inventor_name_last": "Hopper"},
            ],
        }
    ]
}


def test_fetch_patents_raises_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("PATENTSVIEW_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        fetch_patents(tmp_path, query={"_gte": {"patent_date": "2025-01-01"}}, limit=10)


def test_fetch_patents_writes_one_file_per_inventor(tmp_path, monkeypatch):
    monkeypatch.setenv("PATENTSVIEW_API_KEY", "pv-test-key")
    with patch(
        "memory_layer.fetchers.patents.get_json", return_value=FAKE_PATENTSVIEW_RESPONSE
    ) as mock_get_json:
        paths = fetch_patents(tmp_path, query={"_gte": {"patent_date": "2025-01-01"}}, limit=10)

    assert len(paths) == 2
    written = json.loads(paths[0].read_text())
    assert written["inventor_name"] == "Ada Lovelace"
    assert written["patents_filed"] == "1"

    called_headers = mock_get_json.call_args.kwargs["headers"]
    assert called_headers["X-Api-Key"] == "pv-test-key"


def test_fetch_patents_respects_limit(tmp_path, monkeypatch):
    monkeypatch.setenv("PATENTSVIEW_API_KEY", "pv-test-key")
    with patch(
        "memory_layer.fetchers.patents.get_json", return_value=FAKE_PATENTSVIEW_RESPONSE
    ):
        paths = fetch_patents(tmp_path, query={}, limit=1)
    assert len(paths) == 1

import json
from unittest.mock import patch

import pytest

from memory_layer.fetchers.opencorporates import fetch_opencorporates

FAKE_OC_RESPONSE = {
    "results": {
        "companies": [
            {
                "company": {
                    "name": "Acme AI Inc",
                    "company_number": "C7654321",
                    "jurisdiction_code": "us_de",
                    "current_status": "Active",
                    "incorporation_date": "2026-02-01",
                }
            }
        ]
    }
}


def test_fetch_opencorporates_raises_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENCORPORATES_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        fetch_opencorporates(tmp_path, query="Acme", limit=10)


def test_fetch_opencorporates_writes_one_file_per_company(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENCORPORATES_API_KEY", "oc-test-key")
    with patch(
        "memory_layer.fetchers.opencorporates.get_json", return_value=FAKE_OC_RESPONSE
    ) as mock_get_json:
        paths = fetch_opencorporates(tmp_path, query="Acme", limit=10)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["company_number"] == "C7654321"
    assert written["current_status"] == "Active"

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["api_token"] == "oc-test-key"

import json
from unittest.mock import patch

import pytest

from memory_layer.fetchers.companies_house import fetch_companies_house

FAKE_CH_RESPONSE = {
    "items": [
        {
            "company_number": "12345678",
            "title": "ACME AI LTD",
            "company_status": "active",
            "date_of_creation": "2026-01-15",
            "address_snippet": "London, UK",
        }
    ]
}


def test_fetch_companies_house_raises_without_key(tmp_path, monkeypatch):
    monkeypatch.delenv("COMPANIES_HOUSE_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        fetch_companies_house(tmp_path, query="AI", limit=10)


def test_fetch_companies_house_writes_one_file_per_company(tmp_path, monkeypatch):
    monkeypatch.setenv("COMPANIES_HOUSE_API_KEY", "ch-test-key")
    with patch(
        "memory_layer.fetchers.companies_house.get_json", return_value=FAKE_CH_RESPONSE
    ) as mock_get_json:
        paths = fetch_companies_house(tmp_path, query="AI", limit=10)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["company_number"] == "12345678"
    assert written["company_status"] == "active"

    called_auth = mock_get_json.call_args.kwargs["auth"]
    assert called_auth == ("ch-test-key", "")

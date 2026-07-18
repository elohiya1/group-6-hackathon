import json
from unittest.mock import patch

from memory_layer.fetchers.sec_edgar import fetch_sec_form_d

FAKE_EDGAR_RESPONSE = {
    "hits": {
        "total": {"value": 2},
        "hits": [
            {
                "_id": "0001234567-26-000123:primary_doc.xml",
                "_source": {
                    "ciks": ["0001234567"],
                    "display_names": ["ACME AI INC (CIK 0001234567)"],
                    "file_date": "2026-07-01",
                    "form": "D",
                },
            },
            {
                "_id": "0007654321-26-000001:primary_doc.xml",
                "_source": {
                    "ciks": [],
                    "display_names": [],
                    "file_date": "2026-07-02",
                    "form": "D",
                },
            },
        ],
    }
}


def test_fetch_sec_form_d_writes_one_file_per_filing_with_cik(tmp_path):
    with patch(
        "memory_layer.fetchers.sec_edgar.get_json", return_value=FAKE_EDGAR_RESPONSE
    ) as mock_get_json:
        paths = fetch_sec_form_d(tmp_path, query="AI", limit=25, contact_email="test@example.com")

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["cik"] == "0001234567"
    assert written["form_type"] == "D"

    called_headers = mock_get_json.call_args.kwargs["headers"]
    assert "test@example.com" in called_headers["User-Agent"]

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["forms"] == "D"


def test_fetch_sec_form_d_skips_filings_without_cik(tmp_path):
    with patch(
        "memory_layer.fetchers.sec_edgar.get_json",
        return_value={"hits": {"hits": [FAKE_EDGAR_RESPONSE["hits"]["hits"][1]]}},
    ):
        paths = fetch_sec_form_d(tmp_path, query="AI", limit=25)
    assert paths == []

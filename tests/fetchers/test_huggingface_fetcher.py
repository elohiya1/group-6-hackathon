import json
from unittest.mock import patch

from memory_layer.fetchers.huggingface import fetch_huggingface

FAKE_HF_RESPONSE = [
    {
        "id": "adalovelace/founder-score-model",
        "author": "adalovelace",
        "downloads": 5000,
        "likes": 120,
        "tags": ["text-classification"],
        "createdAt": "2026-06-01T00:00:00.000Z",
    },
    {
        "id": "bert-base-uncased",
        "downloads": 900000,
        "likes": 3000,
        "tags": ["fill-mask"],
    },
]


def test_fetch_huggingface_writes_one_file_per_authored_model(tmp_path):
    with patch(
        "memory_layer.fetchers.huggingface.get_json", return_value=FAKE_HF_RESPONSE
    ) as mock_get_json:
        paths = fetch_huggingface(tmp_path, search="ai", limit=20)

    assert len(paths) == 1
    written = json.loads(paths[0].read_text())
    assert written["author"] == "adalovelace"
    assert written["downloads"] == 5000
    assert written["name"] == "adalovelace"

    call_params = mock_get_json.call_args.kwargs["params"]
    assert call_params["search"] == "ai"


def test_fetch_huggingface_skips_models_without_author(tmp_path):
    with patch(
        "memory_layer.fetchers.huggingface.get_json",
        return_value=[{"id": "bert-base-uncased", "downloads": 1}],
    ):
        paths = fetch_huggingface(tmp_path, search="ai", limit=20)
    assert paths == []


def test_fetch_huggingface_respects_limit(tmp_path):
    with patch(
        "memory_layer.fetchers.huggingface.get_json", return_value=FAKE_HF_RESPONSE * 5
    ):
        paths = fetch_huggingface(tmp_path, search="ai", limit=1)
    assert len(paths) == 1

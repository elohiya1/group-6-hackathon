import json
import sys
from unittest.mock import patch

from memory_layer import cli


def test_cli_fetch_github_invokes_fetcher_and_reports(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        ["memory_layer", "fetch", "github", "--topics", "ai", "ml", "--limit", "5"],
    )
    with patch("memory_layer.cli.fetch_github", return_value=["a.json", "b.json"]) as mock_fetch:
        cli.main()

    mock_fetch.assert_called_once()
    _, kwargs = mock_fetch.call_args
    assert kwargs["topics"] == ["ai", "ml"]
    assert kwargs["per_topic_limit"] == 5
    assert "Fetched 2 new raw record(s)" in capsys.readouterr().out


def test_cli_fetch_tavily_invokes_fetcher_with_source(monkeypatch, capsys):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "memory_layer",
            "fetch",
            "tavily",
            "--source",
            "devpost",
            "--queries",
            "site:devpost.com winners",
        ],
    )
    with patch("memory_layer.cli.fetch_via_tavily", return_value=["a.json"]) as mock_fetch:
        cli.main()

    _, kwargs = mock_fetch.call_args
    args, _ = mock_fetch.call_args
    assert kwargs["queries"] == ["site:devpost.com winners"]


def test_cli_ingest_runs_ingestion_and_reports(tmp_path, monkeypatch, capsys):
    incoming = tmp_path / "incoming"
    (incoming / "github").mkdir(parents=True)
    payload = {"name": "Ada Lovelace", "owner": {"login": "adalovelace"}, "stargazers_count": 5}
    (incoming / "github" / "repo1.json").write_text(json.dumps(payload))
    db_path = tmp_path / "test.db"

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "memory_layer",
            "ingest",
            "--db",
            str(db_path),
            "--incoming",
            str(incoming),
            "--processed",
            str(tmp_path / "processed"),
        ],
    )
    cli.main()

    output = capsys.readouterr().out
    assert "Ingested 1 new raw record" in output

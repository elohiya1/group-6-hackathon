import json
import sys

from memory_layer import cli


def test_cli_run_ingests_and_reports(tmp_path, monkeypatch, capsys):
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
            "run",
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

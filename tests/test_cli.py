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


def test_cli_fetch_huggingface_invokes_fetcher(monkeypatch, capsys):
    monkeypatch.setattr(
        sys, "argv", ["memory_layer", "fetch", "huggingface", "--search", "ai", "--limit", "5"]
    )
    with patch("memory_layer.cli.fetch_huggingface", return_value=["a.json"]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["search"] == "ai"
    assert kwargs["limit"] == 5


def test_cli_fetch_npm_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["memory_layer", "fetch", "npm", "--query", "ai"])
    with patch("memory_layer.cli.fetch_npm", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["query"] == "ai"


def test_cli_fetch_openalex_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["memory_layer", "fetch", "openalex", "--search", "ai"])
    with patch("memory_layer.cli.fetch_openalex", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["search"] == "ai"


def test_cli_fetch_sec_edgar_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["memory_layer", "fetch", "sec-edgar", "--query", "AI", "--contact-email", "a@b.com"],
    )
    with patch("memory_layer.cli.fetch_sec_form_d", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["contact_email"] == "a@b.com"


def test_cli_fetch_reddit_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["memory_layer", "fetch", "reddit", "--subreddits", "startups", "--query", "ai"],
    )
    with patch("memory_layer.cli.fetch_reddit", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["subreddits"] == ["startups"]


def test_cli_fetch_patents_parses_query_json(monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["memory_layer", "fetch", "patents", "--query", '{"_gte": {"patent_date": "2025-01-01"}}'],
    )
    with patch("memory_layer.cli.fetch_patents", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["query"] == {"_gte": {"patent_date": "2025-01-01"}}


def test_cli_fetch_companies_house_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["memory_layer", "fetch", "companies-house", "--query", "Acme"]
    )
    with patch("memory_layer.cli.fetch_companies_house", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["query"] == "Acme"


def test_cli_fetch_opencorporates_invokes_fetcher(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["memory_layer", "fetch", "opencorporates", "--query", "Acme"]
    )
    with patch("memory_layer.cli.fetch_opencorporates", return_value=[]) as mock_fetch:
        cli.main()
    _, kwargs = mock_fetch.call_args
    assert kwargs["query"] == "Acme"


def test_cli_ingest_runs_pipeline_and_reports(tmp_path, monkeypatch, capsys):
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


def test_cli_migrate_retype_companies_reports_count(tmp_path, monkeypatch, capsys):
    from memory_layer.db import init_db
    from memory_layer.entities_repo import add_identifier, create_entity

    db_path = tmp_path / "test.db"
    conn = init_db(str(db_path))
    create_entity(conn, "founder", "Acme AI Ltd")
    entity_id = conn.execute("SELECT id FROM entities").fetchone()[0]
    add_identifier(conn, entity_id, "companies_house_number", "12345678")
    conn.close()

    monkeypatch.setattr(
        sys, "argv", ["memory_layer", "migrate", "retype-companies", "--db", str(db_path)]
    )
    cli.main()

    output = capsys.readouterr().out
    assert "Retyped 1 entity" in output


def test_cli_resolve_resolves_needs_review_record(tmp_path, monkeypatch, capsys):
    from datetime import datetime, timezone

    from memory_layer.db import init_db
    from memory_layer.entities_repo import add_identifier, create_entity
    from memory_layer.entity_resolution import resolve_raw_record
    from memory_layer.sources_repo import get_or_create_source

    db_path = tmp_path / "test.db"
    conn = init_db(str(db_path))
    company = create_entity(conn, "company", "Acme")
    add_identifier(conn, company, "company_domain", "acme.com")
    founder = create_entity(conn, "founder", "Grace Hopper")
    add_identifier(conn, founder, "email", "grace@acme.com")

    source_id = get_or_create_source(conn, "tavily")
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "name": "Acme",
        "company_domain": "acme.com",
        "contact_email": "grace@acme.com",
        "employee_count": 12,
    }
    cursor = conn.execute(
        "INSERT INTO raw_records "
        "(source_id, entity_id, raw_payload, content_hash, origin_file, ingested_at, resolution_status) "
        "VALUES (?, NULL, ?, ?, 'test.json', ?, 'needs_review')",
        (source_id, json.dumps(payload), "cli-resolve-hash", now),
    )
    conn.commit()
    raw_record_id = cursor.lastrowid
    resolve_raw_record(conn, raw_record_id)  # lands in needs_review
    conn.close()

    monkeypatch.setattr(
        sys,
        "argv",
        ["memory_layer", "resolve", str(raw_record_id), str(company), "--db", str(db_path)],
    )
    cli.main()

    output = capsys.readouterr().out
    assert f"Resolved raw_record {raw_record_id} -> entity {company}" in output

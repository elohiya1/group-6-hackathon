import argparse
from pathlib import Path

from .db import init_db
from .fetchers.arxiv import fetch_arxiv
from .fetchers.github import fetch_github
from .fetchers.hackernews import fetch_show_hn
from .fetchers.producthunt import fetch_producthunt
from .fetchers.tavily_scrape import fetch_via_tavily
from .ingest import run_ingestion


def _add_fetch_subparsers(fetch_subparsers) -> None:
    github_parser = fetch_subparsers.add_parser("github", help="Fetch repos by GitHub topic")
    github_parser.add_argument("--topics", nargs="+", required=True)
    github_parser.add_argument("--limit", type=int, default=10)
    github_parser.add_argument("--incoming", default="data/incoming")

    hn_parser = fetch_subparsers.add_parser("hackernews", help="Fetch Show HN posts")
    hn_parser.add_argument("--query", default="Show HN")
    hn_parser.add_argument("--limit", type=int, default=50)
    hn_parser.add_argument("--incoming", default="data/incoming")

    arxiv_parser = fetch_subparsers.add_parser("arxiv", help="Fetch recent arXiv papers")
    arxiv_parser.add_argument("--categories", nargs="+", default=["cs.AI", "cs.LG"])
    arxiv_parser.add_argument("--max-results", type=int, default=50)
    arxiv_parser.add_argument("--incoming", default="data/incoming")

    ph_parser = fetch_subparsers.add_parser(
        "producthunt", help="Fetch Product Hunt posts (requires PRODUCTHUNT_TOKEN)"
    )
    ph_parser.add_argument("--limit", type=int, default=50)
    ph_parser.add_argument("--incoming", default="data/incoming")

    tavily_parser = fetch_subparsers.add_parser(
        "tavily", help="Search + tag results under a source (e.g. devpost, university_challenge)"
    )
    tavily_parser.add_argument("--source", required=True)
    tavily_parser.add_argument("--queries", nargs="+", required=True)
    tavily_parser.add_argument("--max-results", type=int, default=5)
    tavily_parser.add_argument("--incoming", default="data/incoming")


def _run_fetch(args) -> None:
    incoming_dir = Path(args.incoming)
    if args.fetch_source == "github":
        paths = fetch_github(incoming_dir, topics=args.topics, per_topic_limit=args.limit)
    elif args.fetch_source == "hackernews":
        paths = fetch_show_hn(incoming_dir, query=args.query, limit=args.limit)
    elif args.fetch_source == "arxiv":
        paths = fetch_arxiv(incoming_dir, categories=args.categories, max_results=args.max_results)
    elif args.fetch_source == "producthunt":
        paths = fetch_producthunt(incoming_dir, limit=args.limit)
    elif args.fetch_source == "tavily":
        paths = fetch_via_tavily(
            incoming_dir, args.source, queries=args.queries, max_results=args.max_results
        )
    else:
        raise ValueError(f"Unknown fetch source: {args.fetch_source}")

    print(f"Fetched {len(paths)} new raw record(s) into {incoming_dir}.")


def main() -> None:
    parser = argparse.ArgumentParser(prog="memory_layer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch_parser = subparsers.add_parser("fetch", help="Pull raw data from a source into data/incoming")
    fetch_subparsers = fetch_parser.add_subparsers(dest="fetch_source", required=True)
    _add_fetch_subparsers(fetch_subparsers)

    ingest_parser = subparsers.add_parser(
        "ingest", help="Ingest + resolve + normalize raw blobs from data/incoming"
    )
    ingest_parser.add_argument("--db", default="data/vc_brain.db")
    ingest_parser.add_argument("--incoming", default="data/incoming")
    ingest_parser.add_argument("--processed", default="data/processed")

    args = parser.parse_args()

    if args.command == "fetch":
        _run_fetch(args)
    elif args.command == "ingest":
        conn = init_db(args.db)
        ingested = run_ingestion(conn, Path(args.incoming), Path(args.processed))
        print(f"Ingested {len(ingested)} new raw record(s).")


if __name__ == "__main__":
    main()

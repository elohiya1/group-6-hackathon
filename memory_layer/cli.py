import argparse
import json
from pathlib import Path

from .db import init_db
from .entity_resolution import resolve_entity
from .fetchers.arxiv import fetch_arxiv
from .fetchers.companies_house import fetch_companies_house
from .fetchers.github import fetch_github
from .fetchers.hackernews import fetch_show_hn
from .fetchers.huggingface import fetch_huggingface
from .fetchers.npm import fetch_npm
from .fetchers.opencorporates import fetch_opencorporates
from .fetchers.openalex import fetch_openalex
from .fetchers.patents import fetch_patents
from .fetchers.producthunt import fetch_producthunt
from .fetchers.reddit import fetch_reddit
from .fetchers.sec_edgar import fetch_sec_form_d
from .fetchers.tavily_scrape import fetch_via_tavily
from .pipeline import run_pipeline


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
        "tavily",
        help=(
            "Search + tag results under a source with no API "
            "(devpost, university_challenge, accelerator, ycombinator, wellfound, "
            "indiehackers, betalist, events)"
        ),
    )
    tavily_parser.add_argument("--source", required=True)
    tavily_parser.add_argument("--queries", nargs="+", required=True)
    tavily_parser.add_argument("--max-results", type=int, default=5)
    tavily_parser.add_argument("--incoming", default="data/incoming")

    hf_parser = fetch_subparsers.add_parser("huggingface", help="Fetch Hugging Face Hub models")
    hf_parser.add_argument("--search", required=True)
    hf_parser.add_argument("--limit", type=int, default=20)
    hf_parser.add_argument("--incoming", default="data/incoming")

    npm_parser = fetch_subparsers.add_parser("npm", help="Fetch npm registry packages")
    npm_parser.add_argument("--query", required=True)
    npm_parser.add_argument("--limit", type=int, default=20)
    npm_parser.add_argument("--incoming", default="data/incoming")

    openalex_parser = fetch_subparsers.add_parser(
        "openalex", help="Fetch recent OpenAlex works (stable author IDs)"
    )
    openalex_parser.add_argument("--search", required=True)
    openalex_parser.add_argument("--max-results", type=int, default=25)
    openalex_parser.add_argument("--incoming", default="data/incoming")

    sec_parser = fetch_subparsers.add_parser(
        "sec-edgar", help="Fetch recent SEC Form D filings (full-text search)"
    )
    sec_parser.add_argument("--query", default="")
    sec_parser.add_argument("--limit", type=int, default=25)
    sec_parser.add_argument("--contact-email", default="")
    sec_parser.add_argument("--incoming", default="data/incoming")

    reddit_parser = fetch_subparsers.add_parser(
        "reddit", help="Fetch Reddit posts from given subreddits"
    )
    reddit_parser.add_argument("--subreddits", nargs="+", required=True)
    reddit_parser.add_argument("--query", required=True)
    reddit_parser.add_argument("--limit", type=int, default=25)
    reddit_parser.add_argument("--incoming", default="data/incoming")

    patents_parser = fetch_subparsers.add_parser(
        "patents", help="Fetch USPTO patents via PatentsView (requires PATENTSVIEW_API_KEY)"
    )
    patents_parser.add_argument("--query", required=True, help="PatentsView query JSON string")
    patents_parser.add_argument("--limit", type=int, default=25)
    patents_parser.add_argument("--incoming", default="data/incoming")

    ch_parser = fetch_subparsers.add_parser(
        "companies-house",
        help="Fetch UK company records (requires COMPANIES_HOUSE_API_KEY)",
    )
    ch_parser.add_argument("--query", required=True)
    ch_parser.add_argument("--limit", type=int, default=25)
    ch_parser.add_argument("--incoming", default="data/incoming")

    oc_parser = fetch_subparsers.add_parser(
        "opencorporates",
        help="Fetch company registration records (requires OPENCORPORATES_API_KEY)",
    )
    oc_parser.add_argument("--query", required=True)
    oc_parser.add_argument("--limit", type=int, default=25)
    oc_parser.add_argument("--incoming", default="data/incoming")


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
    elif args.fetch_source == "huggingface":
        paths = fetch_huggingface(incoming_dir, search=args.search, limit=args.limit)
    elif args.fetch_source == "npm":
        paths = fetch_npm(incoming_dir, query=args.query, limit=args.limit)
    elif args.fetch_source == "openalex":
        paths = fetch_openalex(incoming_dir, search=args.search, max_results=args.max_results)
    elif args.fetch_source == "sec-edgar":
        paths = fetch_sec_form_d(
            incoming_dir, query=args.query, limit=args.limit, contact_email=args.contact_email
        )
    elif args.fetch_source == "reddit":
        paths = fetch_reddit(
            incoming_dir, subreddits=args.subreddits, query=args.query, limit=args.limit
        )
    elif args.fetch_source == "patents":
        paths = fetch_patents(incoming_dir, query=json.loads(args.query), limit=args.limit)
    elif args.fetch_source == "companies-house":
        paths = fetch_companies_house(incoming_dir, query=args.query, limit=args.limit)
    elif args.fetch_source == "opencorporates":
        paths = fetch_opencorporates(incoming_dir, query=args.query, limit=args.limit)
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
        "ingest", help="Ingest + resolve + normalize + score raw blobs from data/incoming"
    )
    ingest_parser.add_argument("--db", default="data/vc_brain.db")
    ingest_parser.add_argument("--incoming", default="data/incoming")
    ingest_parser.add_argument("--processed", default="data/processed")

    resolve_parser = subparsers.add_parser("resolve", help="Manually resolve a needs_review raw_record")
    resolve_parser.add_argument("raw_record_id", type=int)
    resolve_parser.add_argument("decision", help='An entity_id to merge into, or "new"')
    resolve_parser.add_argument("--db", default="data/vc_brain.db")

    args = parser.parse_args()

    if args.command == "fetch":
        _run_fetch(args)
    elif args.command == "ingest":
        conn = init_db(args.db)
        ingested = run_pipeline(conn, Path(args.incoming), Path(args.processed))
        print(f"Ingested {len(ingested)} new raw record(s).")
    elif args.command == "resolve":
        conn = init_db(args.db)
        decision = args.decision if args.decision == "new" else int(args.decision)
        entity_id = resolve_entity(conn, args.raw_record_id, decision)
        print(f"Resolved raw_record {args.raw_record_id} -> entity {entity_id}")


if __name__ == "__main__":
    main()

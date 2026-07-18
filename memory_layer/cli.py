import argparse
from pathlib import Path

from .db import init_db
from .entity_resolution import resolve_entity
from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="memory_layer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Process new raw blobs from the incoming folder")
    run_parser.add_argument("--db", default="data/vc_brain.db")
    run_parser.add_argument("--incoming", default="data/incoming")
    run_parser.add_argument("--processed", default="data/processed")

    resolve_parser = subparsers.add_parser("resolve", help="Manually resolve a needs_review raw_record")
    resolve_parser.add_argument("raw_record_id", type=int)
    resolve_parser.add_argument("decision", help='An entity_id to merge into, or "new"')
    resolve_parser.add_argument("--db", default="data/vc_brain.db")

    args = parser.parse_args()

    if args.command == "run":
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

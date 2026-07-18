import argparse
import json
import sqlite3

from funnel.db import init_funnel_schema
from memory_layer.db import init_db

from .db import init_intelligence_schema
from .pipeline import run_intelligence, run_pending
from .thesis_repo import get_thesis, set_thesis


def _init(db_path: str) -> sqlite3.Connection:
    conn = init_db(db_path)
    init_funnel_schema(conn)
    init_intelligence_schema(conn)
    return conn


def main() -> None:
    parser = argparse.ArgumentParser(prog="intelligence")
    subparsers = parser.add_subparsers(dest="command", required=True)

    thesis_parser = subparsers.add_parser(
        "thesis", help="View or configure the fund's investment thesis"
    )
    thesis_subparsers = thesis_parser.add_subparsers(dest="thesis_command", required=True)

    thesis_show = thesis_subparsers.add_parser("show", help="Print the current thesis")
    thesis_show.add_argument("--db", default="data/vc_brain.db")

    thesis_set = thesis_subparsers.add_parser("set", help="Configure the fund's investment thesis")
    thesis_set.add_argument("--sectors", nargs="+", required=True)
    thesis_set.add_argument("--stage", required=True)
    thesis_set.add_argument("--geography", nargs="+", required=True)
    thesis_set.add_argument("--check-size-min", type=float, required=True)
    thesis_set.add_argument("--check-size-max", type=float, required=True)
    thesis_set.add_argument("--ownership-target-pct", type=float, required=True)
    thesis_set.add_argument("--risk-appetite", required=True)
    thesis_set.add_argument("--db", default="data/vc_brain.db")

    run_parser = subparsers.add_parser(
        "run", help="Run the full Intelligence pass (thesis fit, axes, memo) on one application"
    )
    run_parser.add_argument("application_id", type=int)
    run_parser.add_argument("--db", default="data/vc_brain.db")

    run_pending_parser = subparsers.add_parser(
        "run-pending", help="Run the Intelligence pass on every screened_pass application"
    )
    run_pending_parser.add_argument("--db", default="data/vc_brain.db")

    args = parser.parse_args()

    if args.command == "thesis":
        conn = _init(args.db)
        if args.thesis_command == "show":
            thesis = get_thesis(conn)
            print(json.dumps(thesis, indent=2) if thesis else "No thesis configured yet.")
        elif args.thesis_command == "set":
            set_thesis(
                conn,
                sectors=args.sectors,
                stage=args.stage,
                geography=args.geography,
                check_size_min=args.check_size_min,
                check_size_max=args.check_size_max,
                ownership_target_pct=args.ownership_target_pct,
                risk_appetite=args.risk_appetite,
            )
            print("Thesis updated.")
    elif args.command == "run":
        conn = _init(args.db)
        result = run_intelligence(conn, args.application_id)
        print(json.dumps(result, indent=2))
    elif args.command == "run-pending":
        conn = _init(args.db)
        processed = run_pending(conn)
        print(f"Ran Intelligence on {len(processed)} application(s): {processed}")


if __name__ == "__main__":
    main()

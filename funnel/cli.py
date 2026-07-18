import argparse
import sqlite3
from pathlib import Path

from memory_layer.db import init_db

from .activate import activate_signal
from .converge import converge_signal
from .db import init_funnel_schema
from .identify import scan_for_signals
from .intake import submit_application
from .screen import screen_application


def _init(db_path: str) -> sqlite3.Connection:
    conn = init_db(db_path)
    init_funnel_schema(conn)
    return conn


def main() -> None:
    parser = argparse.ArgumentParser(prog="funnel")
    subparsers = parser.add_subparsers(dest="command", required=True)

    apply_parser = subparsers.add_parser(
        "apply", help="Submit an inbound application (deck + company name)"
    )
    apply_parser.add_argument("--company-name", required=True)
    apply_parser.add_argument("--deck", required=True)
    apply_parser.add_argument(
        "--company-domain", help="Matches an existing company entity in Memory, if known"
    )
    apply_parser.add_argument("--founder-email")
    apply_parser.add_argument("--founder-github")
    apply_parser.add_argument("--db", default="data/vc_brain.db")

    screen_parser = subparsers.add_parser(
        "screen", help="Run the fast first-pass filter on an application"
    )
    screen_parser.add_argument("application_id", type=int)
    screen_parser.add_argument("--db", default="data/vc_brain.db")

    identify_parser = subparsers.add_parser(
        "identify", help="Scan Memory for founders crossing the conviction threshold"
    )
    identify_parser.add_argument("--db", default="data/vc_brain.db")

    activate_parser = subparsers.add_parser(
        "activate", help="Log outreach for an identified signal"
    )
    activate_parser.add_argument("signal_id", type=int)
    activate_parser.add_argument("--channel", default="email")
    activate_parser.add_argument("--db", default="data/vc_brain.db")

    converge_parser = subparsers.add_parser(
        "converge", help="Turn an activated signal into an application"
    )
    converge_parser.add_argument("signal_id", type=int)
    converge_parser.add_argument("--company-name", required=True)
    converge_parser.add_argument("--deck", required=True)
    converge_parser.add_argument(
        "--company-domain", help="Matches an existing company entity in Memory, if known"
    )
    converge_parser.add_argument("--db", default="data/vc_brain.db")

    args = parser.parse_args()

    if args.command == "apply":
        conn = _init(args.db)
        application_id = submit_application(
            conn,
            args.company_name,
            Path(args.deck),
            company_domain=args.company_domain,
            founder_email=args.founder_email,
            founder_github=args.founder_github,
        )
        print(f"Submitted application {application_id}")
    elif args.command == "screen":
        conn = _init(args.db)
        status = screen_application(conn, args.application_id)
        print(f"Application {args.application_id} -> {status}")
    elif args.command == "identify":
        conn = _init(args.db)
        signal_ids = scan_for_signals(conn)
        print(f"Identified {len(signal_ids)} new signal(s): {signal_ids}")
    elif args.command == "activate":
        conn = _init(args.db)
        activation_id = activate_signal(conn, args.signal_id, channel=args.channel)
        print(f"Logged activation {activation_id} for signal {args.signal_id}")
    elif args.command == "converge":
        conn = _init(args.db)
        application_id = converge_signal(
            conn,
            args.signal_id,
            args.company_name,
            Path(args.deck),
            company_domain=args.company_domain,
        )
        print(f"Converged signal {args.signal_id} -> application {application_id}")


if __name__ == "__main__":
    main()

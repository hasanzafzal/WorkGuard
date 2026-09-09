"""Command-line runner for the PostgreSQL-to-Processing pipeline."""

from __future__ import annotations

import argparse
import json
import logging
import sys

from processing.pipeline import get_pending_sessions, process_all_pending, process_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("processing.runner")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the WorkGuard PostgreSQL processing pipeline.")
    parser.add_argument(
        "--session-id",
        type=str,
        default=None,
        help="Specific session ID to process. If omitted, processes all pending sessions.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force re-processing even if session is already completed.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Max number of pending sessions to process (default: 50).",
    )

    args = parser.parse_args()

    if args.session_id:
        print(f"Processing session {args.session_id} (force={args.force})...")
        try:
            res = process_session(args.session_id, force=args.force)
            print(json.dumps(res, indent=2, default=str))
            return 0
        except Exception as e:
            logger.error("Session processing failed: %s", e)
            return 1
    else:
        pending = get_pending_sessions(limit=args.limit)
        print(f"Found {len(pending)} pending sessions.")
        if not pending:
            print("No pending sessions to process.")
            return 0

        res = process_all_pending(limit=args.limit, force=args.force)
        print(json.dumps(res, indent=2, default=str))
        return 0 if res["failed_count"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())

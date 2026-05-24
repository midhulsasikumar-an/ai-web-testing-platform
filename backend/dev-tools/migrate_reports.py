from __future__ import annotations

import argparse
import json

from backend.database.report_repository import migrate_reports_from_test_runs


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill unified reports from historical test runs.")
    parser.add_argument("--user-id", dest="user_id", default=None, help="Only migrate reports for one user.")
    args = parser.parse_args()

    result = migrate_reports_from_test_runs(user_id=args.user_id)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
from __future__ import annotations

import json

from backend.services.auth import migrate_legacy_users


def main() -> int:
    result = migrate_legacy_users(remove_corrupted=True)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

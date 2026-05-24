import json
import sys
from pathlib import Path

# Ensure project root is on sys.path so backend imports work when executed from scripts/
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.database.mongo import bug_collection
from backend.services.bug_services import normalize_bug_record

out = []
for b in bug_collection.find({}):
    out.append(normalize_bug_record(b))
print(json.dumps(out, default=str, indent=2))

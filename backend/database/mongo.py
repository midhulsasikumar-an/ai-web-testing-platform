from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient, ASCENDING, DESCENDING

logger = logging.getLogger("database.mongo")

env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = MongoClient(MONGO_URL)
db = client[os.getenv("MONGO_DB_NAME", "ai-web-testing")]

collection = db["test_runs"]
bug_collection = db["bugs"]
bug_lifecycle_collection = db["bug_lifecycle"]
run_comparison_collection = db["run_comparisons"]
ai_chat_sessions = db["ai_chat_sessions"]
ai_chat_messages = db["ai_chat_messages"]
ai_knowledge_index = db["ai_knowledge_index"]
ai_memory_collection = db["ai_memory_collection"]
report_export_collection = db["report_exports"]
selector_cache_collection = db["selector_cache"]

users_collection = db["users"]
revoked_tokens_collection = db["revoked_tokens"]


def _safe_create_index(coll, *args, **kwargs) -> None:
    name = kwargs.pop("name", None)
    try:
        if name:
            coll.create_index(*args, name=name, **kwargs)
        else:
            coll.create_index(*args, **kwargs)
    except Exception as exc:
        logger.warning("Index creation skipped on %s: %s", coll.name, exc)


# Users
_safe_create_index(users_collection, "email", unique=True)
_safe_create_index(users_collection, "id", unique=True, sparse=True)

# test_runs: cover user-scoped listings, test_id lookups, status filtering, and recent activity
_safe_create_index(collection, [("user_id", ASCENDING), ("test_id", ASCENDING)], unique=True, name="user_test_unique")
_safe_create_index(collection, [("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created_desc")
_safe_create_index(collection, [("user_id", ASCENDING), ("status", ASCENDING)], name="user_status")
_safe_create_index(collection, [("status", ASCENDING), ("updated_at", DESCENDING)], name="status_updated_desc")
_safe_create_index(collection, "test_id", name="test_id_only")

# bugs: cover user-scoped listings and status filtering
_safe_create_index(bug_collection, [("user_id", ASCENDING), ("test_id", ASCENDING)], name="user_test")
_safe_create_index(bug_collection, [("user_id", ASCENDING), ("status", ASCENDING)], name="user_status")
_safe_create_index(bug_collection, [("user_id", ASCENDING), ("created_at", DESCENDING)], name="user_created_desc")
_safe_create_index(bug_collection, "bug_id", unique=True, sparse=True, name="bug_id_unique")
_safe_create_index(bug_collection, "fingerprint", unique=True, sparse=True, name="bug_fingerprint_unique")

# bug_lifecycle
_safe_create_index(bug_lifecycle_collection, "fingerprint", unique=True, sparse=True, name="lifecycle_fingerprint_unique")
_safe_create_index(bug_lifecycle_collection, [("user_id", ASCENDING), ("status", ASCENDING)], name="lifecycle_user_status")
_safe_create_index(bug_lifecycle_collection, [("user_id", ASCENDING), ("updated_at", DESCENDING)], name="lifecycle_user_updated")

# Reports (report_repository.py also creates an index; align names to avoid collisions)
_safe_create_index(db["reports"], "report_key", unique=True, name="report_key_unique")
_safe_create_index(db["reports"], [("user_id", ASCENDING), ("report_type", ASCENDING)], name="reports_user_type")

# Revoked tokens (logout / admin revoke)
_safe_create_index(revoked_tokens_collection, "jti", unique=True, name="revoked_jti_unique")
_safe_create_index(revoked_tokens_collection, "user_id", name="revoked_user")
_safe_create_index(revoked_tokens_collection, "expires_at", expireAfterSeconds=0, name="revoked_ttl")
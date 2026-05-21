from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv
from pymongo import MongoClient


env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")

client = MongoClient(MONGO_URL)
db = client[os.getenv("MONGO_DB_NAME", "ai-web-testing")]

collection = db["test_runs"]
bug_collection = db["bugs"]
bug_lifecycle_collection = db["bug_lifecycle"]
run_comparison_collection = db["run_comparisons"]
report_export_collection = db["report_exports"]

users_collection = db["users"]

# Ensure unique email index
users_collection.create_index("email", unique=True)
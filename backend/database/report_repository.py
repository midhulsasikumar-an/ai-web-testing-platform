from __future__ import annotations

from typing import Dict, Any
from datetime import datetime
from backend.database.mongo import db


def save_report(report: Dict[str, Any]) -> str:
    collection = db["reports"]
    payload = dict(report)
    payload.setdefault("created_at", datetime.utcnow())
    result = collection.insert_one(payload)
    return str(result.inserted_id)

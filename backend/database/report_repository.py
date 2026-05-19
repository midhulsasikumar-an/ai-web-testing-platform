from __future__ import annotations

import uuid
from typing import Dict, Any
from datetime import datetime
from backend.database.mongo import db


def save_report(report: Dict[str, Any]) -> str:
    collection = db["reports"]
    payload = dict(report)
    payload["report_id"] = str(payload.get("report_id") or uuid.uuid4())
    payload.setdefault("created_at", datetime.utcnow())
    result = collection.insert_one(payload)
    return payload["report_id"]

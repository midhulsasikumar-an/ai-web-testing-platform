from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.database.mongo import revoked_tokens_collection

logger = logging.getLogger("services.token_revocation")

_REVOKED_FINGERPRINT_FIELD = "token_hash"


def _token_fingerprint(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _extract_jti(payload: Dict[str, Any]) -> Optional[str]:
    for key in ("jti", "token_id", "id"):
        value = payload.get(key)
        if value:
            return str(value)
    return None


def _normalize_expiry(expires_at: Any) -> datetime:
    if isinstance(expires_at, datetime):
        return expires_at.astimezone(timezone.utc) if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)
    if isinstance(expires_at, (int, float)):
        return datetime.fromtimestamp(int(expires_at), tz=timezone.utc)
    if isinstance(expires_at, str):
        try:
            cleaned = expires_at.replace("Z", "+00:00") if expires_at.endswith("Z") else expires_at
            parsed = datetime.fromisoformat(cleaned)
            return parsed.astimezone(timezone.utc) if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return datetime.now(timezone.utc).replace(microsecond=0)


def revoke_token(token: str, payload: Dict[str, Any], reason: str = "logout") -> bool:
    if not token:
        return False

    fingerprint = _token_fingerprint(token)
    jti = _extract_jti(payload)
    user_id = str(payload.get("sub") or payload.get("id") or payload.get("user_id") or "").strip()
    expires_at = _normalize_expiry(payload.get("exp") or datetime.now(timezone.utc))

    document = {
        _REVOKED_FINGERPRINT_FIELD: fingerprint,
        "jti": jti,
        "user_id": user_id,
        "reason": reason,
        "revoked_at": datetime.now(timezone.utc),
        "expires_at": expires_at,
    }

    try:
        revoked_tokens_collection.update_one(
            {_REVOKED_FINGERPRINT_FIELD: fingerprint},
            {"$setOnInsert": document},
            upsert=True,
        )
        return True
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to revoke token: %s", exc)
        return False


def revoke_refresh_token(token: str, payload: Dict[str, Any]) -> bool:
    return revoke_token(token, payload, reason="logout_refresh")


def is_token_revoked(token: str) -> bool:
    if not token:
        return False
    fingerprint = _token_fingerprint(token)
    try:
        return revoked_tokens_collection.count_documents(
            {_REVOKED_FINGERPRINT_FIELD: fingerprint},
            limit=1,
        ) > 0
    except Exception as exc:  # pragma: no cover - defensive logging only
        logger.warning("Failed to query revoked tokens: %s", exc)
        return False

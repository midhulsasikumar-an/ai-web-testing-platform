from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext

from backend.database.mongo import users_collection
from backend.services.jwt_utils import create_access_token, decode_access_token
from backend.services.token_revocation import is_token_revoked

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


def normalize_email(email: str | None) -> str:
    return str(email or "").strip().lower()


def _resolve_user_id(user: Dict[str, Any]) -> str:
    value = user.get("id") or user.get("user_id") or user.get("_id")
    return str(value) if value is not None else str(uuid.uuid4())


def _normalize_timestamp(value: Any, fallback: datetime | None = None) -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return (fallback or datetime.now(timezone.utc)).isoformat()


def normalize_user_document(user: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    normalized = dict(user)
    changed = False

    email = normalize_email(normalized.get("email"))
    if email and normalized.get("email") != email:
        normalized["email"] = email
        changed = True

    resolved_id = normalized.get("id") or normalized.get("user_id")
    if resolved_id:
        resolved_id = str(resolved_id)
    else:
        resolved_id = _resolve_user_id(normalized)
        changed = True

    if normalized.get("id") != resolved_id:
        normalized["id"] = resolved_id
        changed = True
    if normalized.get("user_id") != resolved_id:
        normalized["user_id"] = resolved_id
        changed = True

    password_hash = normalized.get("password_hash") or normalized.get("hashed_password")
    if password_hash and normalized.get("password_hash") != password_hash:
        normalized["password_hash"] = password_hash
        changed = True

    name = normalized.get("name") or normalized.get("full_name") or email or resolved_id
    if name and normalized.get("name") != name:
        normalized["name"] = name
        changed = True

    role = normalized.get("role") or "user"
    if normalized.get("role") != role:
        normalized["role"] = role
        changed = True

    created_at = _normalize_timestamp(normalized.get("created_at"))
    if normalized.get("created_at") != created_at:
        normalized["created_at"] = created_at
        changed = True

    updated_at = _normalize_timestamp(normalized.get("updated_at"), datetime.now(timezone.utc))
    if normalized.get("updated_at") != updated_at:
        normalized["updated_at"] = updated_at
        changed = True

    if "full_name" in normalized:
        normalized.pop("full_name", None)
        changed = True
    if "hashed_password" in normalized:
        normalized.pop("hashed_password", None)
        changed = True

    return normalized, changed


def persist_normalized_user(user: Dict[str, Any]) -> Dict[str, Any]:
    normalized_user, changed = normalize_user_document(user)
    if not changed:
        return normalized_user

    users_collection.update_one(
        {"_id": user.get("_id")} if user.get("_id") is not None else {"email": normalized_user["email"]},
        {
            "$set": {
                "id": normalized_user["id"],
                "user_id": normalized_user["id"],
                "email": normalized_user["email"],
                "name": normalized_user["name"],
                "password_hash": normalized_user["password_hash"],
                "role": normalized_user.get("role", "user"),
                "created_at": normalized_user["created_at"],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            "$unset": {"hashed_password": "", "full_name": ""},
        },
    )
    return normalized_user


def serialize_user_document(user: Dict[str, Any]) -> Dict[str, str]:
    normalized_user, _ = normalize_user_document(user)
    return {
        "id": normalized_user["id"],
        "user_id": normalized_user["id"],
        "name": normalized_user["name"],
        "email": normalized_user["email"],
        "role": normalized_user.get("role", "user"),
    }


def migrate_legacy_users(remove_corrupted: bool = True) -> Dict[str, int]:
    inspected = 0
    migrated = 0
    removed_corrupted = 0

    for user in users_collection.find({}):
        inspected += 1
        normalized_user, changed = normalize_user_document(user)

        if not normalized_user.get("password_hash"):
            if remove_corrupted:
                users_collection.delete_one({"_id": user.get("_id")})
                removed_corrupted += 1
            continue

        if not changed:
            continue

        users_collection.update_one(
            {"_id": user.get("_id")},
            {
                "$set": {
                    "id": normalized_user["id"],
                    "user_id": normalized_user["id"],
                    "email": normalized_user["email"],
                    "name": normalized_user["name"],
                    "password_hash": normalized_user["password_hash"],
                    "role": normalized_user.get("role", "user"),
                    "created_at": normalized_user["created_at"],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                },
                "$unset": {"hashed_password": "", "full_name": ""},
            },
        )
        migrated += 1

    return {"inspected": inspected, "migrated": migrated, "removed_corrupted": removed_corrupted}


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if not hashed_password:
        return False

    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def _reject_unauthorized(detail: str = "Unauthorized") -> HTTPException:
    return HTTPException(status_code=401, detail=detail)


def _token_session_version(payload: Dict[str, Any]) -> int:
    try:
        return int(payload.get("session_version") or 0)
    except (TypeError, ValueError):
        raise _reject_unauthorized("Invalid token")


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> Dict[str, str]:
    if credentials is None or credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise _reject_unauthorized()
    return get_current_user_from_token(credentials.credentials)


def get_current_user_from_token(token: str) -> Dict[str, str]:
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise _reject_unauthorized("Invalid token") from exc

    token_type = str(payload.get("token_type") or "access").strip().lower()
    if token_type not in {"", "access"}:
        raise _reject_unauthorized("Invalid token")

    if is_token_revoked(token):
        raise _reject_unauthorized("Token has been revoked")

    user_id = payload.get("sub") or payload.get("id") or payload.get("user_id")
    email = normalize_email(payload.get("email"))
    if not user_id and not email:
        raise _reject_unauthorized("Invalid token")

    query = {"id": str(user_id)} if user_id else {"email": email}
    user = users_collection.find_one(query)
    if not user:
        raise _reject_unauthorized("Invalid token")

    normalized_user = persist_normalized_user(user)
    expected_session_version = int(normalized_user.get("session_version") or 0)
    token_session_version = _token_session_version(payload)
    if token_session_version != expected_session_version:
        raise _reject_unauthorized("Token has been revoked")

    return {
        "id": str(normalized_user.get("id") or user_id or ""),
        "user_id": str(normalized_user.get("id") or user_id or ""),
        "email": str(normalized_user.get("email") or email or ""),
        "name": str(normalized_user.get("name") or payload.get("name") or ""),
        "role": str(normalized_user.get("role") or payload.get("role") or "user"),
        "session_version": str(expected_session_version),
    }

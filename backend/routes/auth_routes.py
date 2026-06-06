from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

from backend.models.schema import SignupRequest, LoginRequest, RefreshTokenRequest
from backend.services.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    normalize_email,
    persist_normalized_user,
    serialize_user_document,
    verify_password,
)
from backend.database.mongo import users_collection
from backend.services.jwt_utils import create_refresh_token, decode_refresh_token
from backend.services.token_revocation import (
    revoke_token,
    revoke_refresh_token,
)
from backend.services.rate_limit import (
    LOGIN_LIMIT,
    REFRESH_LIMIT,
    SIGNUP_LIMIT,
    limiter,
)


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
@limiter.limit(SIGNUP_LIMIT)
def signup(request: Request, req: SignupRequest):
    if not req.name or len(req.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    normalized_email = normalize_email(req.email)
    existing = users_collection.find_one({"email": normalized_email})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    user_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    user_doc = {
        "id": user_id,
        "user_id": user_id,
        "name": req.name.strip(),
        "email": normalized_email,
        "password_hash": hash_password(req.password),
        "role": "user",
        "created_at": now,
        "updated_at": now,
    }

    users_collection.insert_one(user_doc)
    token_payload = {
        "sub": user_id,
        "id": user_id,
        "user_id": user_id,
        "email": user_doc["email"],
        "name": user_doc["name"],
        "role": user_doc["role"],
    }
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {"token": token, "access_token": token, "refresh_token": refresh_token, "user": serialize_user_document(user_doc)}


@router.post("/login")
@limiter.limit(LOGIN_LIMIT)
def login(request: Request, req: LoginRequest):
    normalized_email = normalize_email(req.email)
    user = users_collection.find_one({"email": normalized_email})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = persist_normalized_user(user)
    password_hash = user.get("password_hash")
    if not password_hash:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(req.password, password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_payload = serialize_user_document(user)
    user_id = user_payload["id"]
    token_payload = {
        "sub": user_id,
        "id": user_id,
        "user_id": user_id,
        "email": user_payload["email"],
        "name": user_payload["name"],
        "role": user_payload["role"],
    }
    token = create_access_token(token_payload)
    refresh_token = create_refresh_token(token_payload)

    return {
        "token": token,
        "access_token": token,
        "refresh_token": refresh_token,
        "user": user_payload,
    }


@router.post("/refresh")
@limiter.limit(REFRESH_LIMIT)
def refresh_access_token(request: Request, req: RefreshTokenRequest):
    from backend.services.token_revocation import is_token_revoked, revoke_token

    token = str(req.refresh_token or "").strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    try:
        payload = decode_refresh_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc

    if str(payload.get("token_type") or "").lower() != "refresh":
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if is_token_revoked(token):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    user_id = str(payload.get("sub") or payload.get("id") or payload.get("user_id") or "").strip()
    email = normalize_email(str(payload.get("email") or "").strip())
    if not user_id and not email:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    query = {"id": user_id} if user_id else {"email": email}
    user_doc = users_collection.find_one(query)
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    normalized_user = persist_normalized_user(user_doc)
    access_payload = {
        "sub": str(normalized_user.get("id") or user_id),
        "id": str(normalized_user.get("id") or user_id),
        "user_id": str(normalized_user.get("id") or user_id),
        "email": str(normalized_user.get("email") or email),
        "name": str(normalized_user.get("name") or payload.get("name") or email),
        "role": str(normalized_user.get("role") or "user"),
    }
    new_access_token = create_access_token(access_payload)
    new_refresh_token = create_refresh_token(access_payload)

    revoke_token(token, payload, reason="refresh_rotation")

    return {
        "token": new_access_token,
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "user": {
            "id": access_payload["id"],
            "name": access_payload["name"],
            "email": access_payload["email"],
            "role": access_payload["role"],
        },
    }


@router.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {"user": {"id": current_user["id"], "name": current_user["name"], "email": current_user["email"], "role": current_user.get("role", "user")}}


@router.post("/logout")
@limiter.limit(REFRESH_LIMIT)
def logout(
    request: Request,
    req: LogoutRequest | None = None,
    current_user: dict = Depends(get_current_user),
):
    """Revoke the current access token and (optionally) the supplied refresh token.

    After this call, both tokens are rejected by `get_current_user` and the refresh
    endpoint. The Mongo `revoked_tokens` collection holds a TTL index that purges
    entries automatically once their `exp` has passed.
    """
    revoked_access = False
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization") or ""
    if auth_header.lower().startswith("bearer "):
        bearer_token = auth_header.split(" ", 1)[1].strip()
        if bearer_token:
            try:
                access_payload = decode_refresh_token(bearer_token)
            except Exception:
                access_payload = {}
            revoked_access = revoke_token(bearer_token, access_payload, reason="logout_access")

    revoked_refresh = False
    if req and req.refresh_token:
        try:
            refresh_payload = decode_refresh_token(req.refresh_token)
        except Exception:
            refresh_payload = {}
        revoked_refresh = revoke_refresh_token(req.refresh_token, refresh_payload)

    return {
        "status": "ok",
        "user": current_user["id"],
        "revoked_access": revoked_access,
        "revoked_refresh": revoked_refresh,
    }
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


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _session_version(user_doc: dict) -> int:
    try:
        return int(user_doc.get("session_version") or 0)
    except (TypeError, ValueError):
        return 0


def _payload_session_version(payload: dict) -> int:
    try:
        return int(payload.get("session_version") or 0)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid refresh token")


def _token_payload(user_doc: dict) -> dict:
    user_payload = serialize_user_document(user_doc)
    user_id = user_payload["id"]
    return {
        "sub": user_id,
        "id": user_id,
        "user_id": user_id,
        "email": user_payload["email"],
        "name": user_payload["name"],
        "role": user_payload["role"],
        "session_version": _session_version(user_doc),
    }


def _session_response(user_doc: dict) -> dict:
    payload = _token_payload(user_doc)
    token = create_access_token(payload)
    refresh_token = create_refresh_token(payload)
    return {
        "token": token,
        "access_token": token,
        "refresh_token": refresh_token,
        "user": serialize_user_document(user_doc),
    }


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
        "session_version": 0,
        "created_at": now,
        "updated_at": now,
    }

    users_collection.insert_one(user_doc)
    return _session_response(user_doc)


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

    return _session_response(user)


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
    if _payload_session_version(payload) != _session_version(normalized_user):
        raise HTTPException(status_code=401, detail="Refresh token has been revoked")

    access_payload = {
        "sub": str(normalized_user.get("id") or user_id),
        "id": str(normalized_user.get("id") or user_id),
        "user_id": str(normalized_user.get("id") or user_id),
        "email": str(normalized_user.get("email") or email),
        "name": str(normalized_user.get("name") or payload.get("name") or email),
        "role": str(normalized_user.get("role") or "user"),
        "session_version": _session_version(normalized_user),
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


@router.patch("/me")
def update_current_user(req: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    updates = {}
    if req.name is not None:
        name = req.name.strip()
        if len(name) < 2:
            raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
        updates["name"] = name

    if req.email is not None:
        email = normalize_email(req.email)
        if not email or "@" not in email:
            raise HTTPException(status_code=400, detail="Invalid email address")
        existing = users_collection.find_one({"email": email, "id": {"$ne": current_user["id"]}})
        if existing:
            raise HTTPException(status_code=409, detail="An account with this email already exists")
        updates["email"] = email

    if not updates:
        user_doc = users_collection.find_one({"id": current_user["id"]})
        if not user_doc:
            raise HTTPException(status_code=404, detail="User not found")
        return {"user": serialize_user_document(user_doc)}

    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    users_collection.update_one({"id": current_user["id"]}, {"$set": updates})
    user_doc = users_collection.find_one({"id": current_user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    return {"user": serialize_user_document(user_doc)}


@router.post("/password")
def change_password(req: ChangePasswordRequest, current_user: dict = Depends(get_current_user)):
    if not req.new_password or len(req.new_password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    user_doc = users_collection.find_one({"id": current_user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(req.current_password, user_doc.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="The current password is incorrect")

    next_version = _session_version(user_doc) + 1
    users_collection.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "password_hash": hash_password(req.new_password),
                "session_version": next_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    updated_user = users_collection.find_one({"id": current_user["id"]})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    response = _session_response(updated_user)
    response["revoked_sessions"] = True
    return response


@router.post("/sessions/revoke-all")
def revoke_all_sessions(current_user: dict = Depends(get_current_user)):
    user_doc = users_collection.find_one({"id": current_user["id"]})
    if not user_doc:
        raise HTTPException(status_code=404, detail="User not found")

    next_version = _session_version(user_doc) + 1
    users_collection.update_one(
        {"id": current_user["id"]},
        {
            "$set": {
                "session_version": next_version,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    updated_user = users_collection.find_one({"id": current_user["id"]})
    if not updated_user:
        raise HTTPException(status_code=404, detail="User not found")

    response = _session_response(updated_user)
    response["revoked"] = 1
    return response


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

from __future__ import annotations

import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

_PLACEHOLDER_SECRETS = {
    "",
    "change-me",
    "change-me-in-local-development-only",
    "changeme",
    "secret",
    "development",
    "dev-secret",
    "test",
    "jwt-secret",
    "your-secret-key",
    "please-change-me",
    "insecure",
}

_MIN_SECRET_LENGTH = 32
_LOCAL_DEVELOPMENT_SECRET = "local-development-jwt-secret-for-testpulse-ai-only"


def _parse_expiry_minutes() -> int:
    raw_value = os.getenv("JWT_EXPIRY_MINUTES") or os.getenv("JWT_EXPIRY_HOURS")
    if not raw_value:
        return 24 * 60

    try:
        parsed = int(raw_value)
    except ValueError:
        return 24 * 60

    if parsed <= 0:
        return 24 * 60

    if os.getenv("JWT_EXPIRY_HOURS") and not os.getenv("JWT_EXPIRY_MINUTES"):
        return parsed * 60

    return parsed


JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")

if JWT_SECRET_KEY is None or not JWT_SECRET_KEY.strip():
    allow_weak = os.getenv("JWT_ALLOW_WEAK_SECRET", "").strip().lower() in {"1", "true", "yes"}
    if not allow_weak:
        raise RuntimeError(
            "JWT_SECRET_KEY is required. Set it to a strong secret "
            "(>= 32 chars, not a known placeholder). Generate one with "
            "`python -c \"import secrets; print(secrets.token_urlsafe(48))\"`. "
            "Set JWT_ALLOW_WEAK_SECRET=1 only for ephemeral local development."
        )
    JWT_SECRET_KEY = _LOCAL_DEVELOPMENT_SECRET

_normalized_secret = JWT_SECRET_KEY.strip()
if _normalized_secret.lower() in _PLACEHOLDER_SECRETS or len(_normalized_secret) < _MIN_SECRET_LENGTH:
    allow_weak = os.getenv("JWT_ALLOW_WEAK_SECRET", "").strip().lower() in {"1", "true", "yes"}
    if not allow_weak:
        raise RuntimeError(
            "JWT_SECRET_KEY is too weak (placeholder or shorter than 32 chars). "
            "Generate one with `python -c \"import secrets; print(secrets.token_urlsafe(48))\"`. "
            "Set JWT_ALLOW_WEAK_SECRET=1 only for ephemeral local development."
        )
    JWT_SECRET_KEY = _LOCAL_DEVELOPMENT_SECRET
    _normalized_secret = JWT_SECRET_KEY.strip()

JWT_SECRET_KEY = _normalized_secret
del _normalized_secret

JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_MINUTES = _parse_expiry_minutes()
JWT_REFRESH_EXPIRY_MINUTES = int(os.getenv("JWT_REFRESH_EXPIRY_MINUTES", str(7 * 24 * 60)))


def _create_token(payload: Dict[str, Any], *, token_type: str, expires_delta: timedelta | None = None, default_minutes: int) -> str:
    token_payload = dict(payload)
    expiry = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=default_minutes))
    token_payload["token_type"] = token_type
    token_payload["exp"] = expiry
    token_payload["iat"] = datetime.now(timezone.utc)
    if not token_payload.get("jti"):
        token_payload["jti"] = uuid.uuid4().hex
    return jwt.encode(token_payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def create_access_token(payload: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    return _create_token(
        payload,
        token_type="access",
        expires_delta=expires_delta,
        default_minutes=JWT_EXPIRY_MINUTES,
    )


def create_refresh_token(payload: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    return _create_token(
        payload,
        token_type="refresh",
        expires_delta=expires_delta,
        default_minutes=JWT_REFRESH_EXPIRY_MINUTES,
    )


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def decode_refresh_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])


def is_jwt_error(error: Exception) -> bool:
    return isinstance(error, JWTError)

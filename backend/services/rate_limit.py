from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import Request
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.responses import JSONResponse

logger = logging.getLogger("services.rate_limit")

_DEFAULT_LOGIN_LIMIT = "5/minute"
_DEFAULT_SIGNUP_LIMIT = "3/minute"
_DEFAULT_REFRESH_LIMIT = "20/minute"
_DEFAULT_PASSWORD_LIMIT = "5/hour"

LOGIN_LIMIT = os.getenv("RATE_LIMIT_LOGIN", _DEFAULT_LOGIN_LIMIT)
SIGNUP_LIMIT = os.getenv("RATE_LIMIT_SIGNUP", _DEFAULT_SIGNUP_LIMIT)
REFRESH_LIMIT = os.getenv("RATE_LIMIT_REFRESH", _DEFAULT_REFRESH_LIMIT)
PASSWORD_LIMIT = os.getenv("RATE_LIMIT_PASSWORD_RESET", _DEFAULT_PASSWORD_LIMIT)


def _client_key(request: Request) -> str:
    try:
        if request.client and request.client.host:
            return get_remote_address(request)
    except Exception:
        pass
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return f"xff:{first}"
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return f"xri:{real_ip}"
    return "anonymous"


def _login_key(request: Request) -> str:
    try:
        body = getattr(request, "_json", None)
        if body is None:
            try:
                body_bytes = request.state._body  # type: ignore[attr-defined]
            except Exception:
                body_bytes = None
        else:
            body_bytes = body
    except Exception:
        body_bytes = None

    email = None
    if body_bytes:
        try:
            import json

            parsed = json.loads(body_bytes)
            if isinstance(parsed, dict):
                candidate = parsed.get("email") or parsed.get("username")
                if candidate:
                    email = str(candidate).strip().lower()
        except Exception:
            email = None

    ip = _client_key(request)
    return f"{ip}|{email or 'no-email'}"


def _signup_key(request: Request) -> str:
    return _client_key(request)


def _refresh_key(request: Request) -> str:
    return _client_key(request)


# `strategy="moving-window"` uses a rolling time window so two bursts across
# the boundary of a fixed window cannot combine to exceed the limit. This is
# safer than a plain fixed window and avoids shared state issues between threads.
# We keep `headers_enabled=False` because slowapi requires endpoints to return a
# starlette.responses.Response instance in order to inject rate-limit headers.
# Our auth endpoints return plain dicts (serialized by FastAPI) — we surface the
# `Retry-After` header explicitly via the 429 exception handler instead.
limiter = Limiter(
    key_func=_client_key,
    headers_enabled=False,
    strategy="moving-window",
)


def build_limiter() -> Limiter:
    return limiter


def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    detail = str(exc.detail) if exc and getattr(exc, "detail", None) else "Rate limit exceeded"
    logger.warning("Rate limit exceeded on %s: %s", request.url.path, detail)
    retry_after: Optional[int] = None
    try:
        retry_after = int(getattr(exc, "retry_after", None) or 0) or None
    except Exception:
        retry_after = None

    payload = {
        "error": "rate_limited",
        "detail": f"Too many requests. {detail}",
    }
    headers = {"Retry-After": str(retry_after) if retry_after else "60"}
    return JSONResponse(status_code=429, content=payload, headers=headers)

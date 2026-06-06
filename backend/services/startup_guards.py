"""Startup-time safety checks for production-like deployments.

This module is intentionally side-effect free apart from logging. It will:

* refuse to start if a known development placeholder is detected in MONGO_URL
  and STRICT_SECRETS=1 is set
* warn loudly when GROQ_API_KEY still looks like a development key
* warn when MONGO_URL contains embedded credentials on a non-local host
* warn when JWT_SECRET_KEY was auto-generated (since the auto-generated key
  changes every restart, all previously-issued tokens are invalidated)

The module is safe to import multiple times; each call to `run_startup_guards`
is idempotent and re-reads environment variables.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Iterable, List, Tuple

logger = logging.getLogger("services.startup_guards")

_PLACEHOLDER_MONGO_HOSTS = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "mongomock://localhost",
}

_MONGO_CREDENTIAL_PATTERN = re.compile(r"://(?P<user>[^:@/]+):(?P<password>[^@/]+)@", re.IGNORECASE)

_GROQ_KEY_PREFIX_PATTERN = re.compile(r"^gsk_(?:dev|test|demo|sample)", re.IGNORECASE)

_ISSUES: List[Tuple[str, str]] = []  # (severity, message)


def _record(severity: str, message: str) -> None:
    _ISSUES.append((severity, message))
    if severity == "error":
        logger.error("startup_guard: %s", message)
    else:
        logger.warning("startup_guard: %s", message)


def _check_mongo_url() -> None:
    raw = (os.getenv("MONGO_URL") or "").strip()
    if not raw:
        _record("warning", "MONGO_URL is not set; falling back to mongodb://localhost:27017")
        return

    if any(placeholder in raw.lower() for placeholder in ("example.com", "your-cluster", "changeme", "mongodb+srv://user:password@")):
        _record(
            "error" if os.getenv("STRICT_SECRETS", "").strip().lower() in {"1", "true", "yes"} else "warning",
            f"MONGO_URL contains a placeholder/development value: {raw.split('@')[-1] if '@' in raw else raw}",
        )

    credentials_match = _MONGO_CREDENTIAL_PATTERN.search(raw)
    if credentials_match:
        host_part = raw.split("@", 1)[-1]
        host = host_part.split("/", 1)[0].split("?", 1)[0]
        if host.lower() not in _PLACEHOLDER_MONGO_HOSTS:
            _record(
                "warning",
                "MONGO_URL embeds username and password directly in the connection string. "
                "Move credentials to a secret manager or use environment variable interpolation.",
            )
    else:
        host_part = raw.split("@", 1)[-1] if "@" in raw else raw.split("://", 1)[-1]
        host = host_part.split("/", 1)[0].split("?", 1)[0]
        if host.lower() not in _PLACEHOLDER_MONGO_HOSTS and "mongodb+srv" in raw:
            _record(
                "warning",
                "MONGO_URL is an mongodb+srv connection string without embedded credentials. "
                "Ensure credentials are supplied via a separate secret or IAM role.",
            )


def _check_groq_api_key() -> None:
    raw = (os.getenv("GROQ_API_KEY") or "").strip()
    if not raw:
        _record("warning", "GROQ_API_KEY is not set; AI features will be unavailable")
        return
    if _GROQ_KEY_PREFIX_PATTERN.match(raw):
        _record("warning", "GROQ_API_KEY looks like a development/sample key. Rotate before production.")
    if len(raw) < 40:
        _record("warning", f"GROQ_API_KEY is unusually short ({len(raw)} chars). Verify it is a production key.")


def _check_jwt_secret_rotation() -> None:
    if os.getenv("JWT_ALLOW_WEAK_SECRET", "").strip().lower() in {"1", "true", "yes"}:
        _record(
            "warning",
            "JWT_ALLOW_WEAK_SECRET=1 is set. JWT_SECRET_KEY will be auto-generated per-process; "
            "all tokens will be invalidated on restart and the server is not safe for production.",
        )


def _check_frontend_origins() -> None:
    origins = (os.getenv("FRONTEND_ORIGINS") or "").strip()
    if not origins:
        _record("warning", "FRONTEND_ORIGINS is not set; defaulting to http://localhost:3000")
        return
    parsed: Iterable[str] = [o.strip() for o in origins.split(",") if o.strip()]
    if any(o == "*" for o in parsed):
        _record(
            "error" if os.getenv("STRICT_SECRETS", "").strip().lower() in {"1", "true", "yes"} else "warning",
            "FRONTEND_ORIGINS contains a wildcard; CORS will allow any origin. Set an explicit allowlist.",
        )


def run_startup_guards() -> List[Tuple[str, str]]:
    _ISSUES.clear()
    _check_mongo_url()
    _check_groq_api_key()
    _check_jwt_secret_rotation()
    _check_frontend_origins()
    if _ISSUES:
        severities = [s for s, _ in _ISSUES]
        if "error" in severities and os.getenv("STRICT_SECRETS", "").strip().lower() in {"1", "true", "yes"}:
            raise RuntimeError(
                "startup_guards detected fatal configuration issues: "
                + "; ".join(msg for _, msg in _ISSUES if _ == "error")
            )
    return list(_ISSUES)

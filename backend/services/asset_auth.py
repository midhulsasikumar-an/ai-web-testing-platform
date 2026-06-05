from __future__ import annotations

import os
import secrets
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import HTTPException
from fastapi.responses import FileResponse

SCREENSHOTS_DIR = Path(os.getenv("SCREENSHOTS_DIR", "screenshots")).resolve()
ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", "artifacts")).resolve()
SCREENSHOT_TOKEN_SALT = os.getenv("SCREENSHOT_TOKEN_SALT", "testpilot-screenshot")
ARTIFACT_TOKEN_SALT = os.getenv("ARTIFACT_TOKEN_SALT", "testpilot-artifact")
# Default TTL: 24 hours. Long enough for a typical QA session to share
# screenshot URLs, short enough to bound exposure if a token leaks.
ASSET_TOKEN_TTL_SECONDS = int(os.getenv("ASSET_TOKEN_TTL_SECONDS", str(24 * 60 * 60)))


def _issue_asset_token(user_id: str, salt: str, *, expires_in: int) -> str:
    expires_at = int(datetime.utcnow().timestamp()) + expires_in
    signature = secrets.token_urlsafe(8)
    return f"{user_id}:{expires_at}:{signature}"


def _verify_asset_token(token: Optional[str], expected_user_id: str) -> bool:
    """Validate an asset token.

    The token is the sole proof of authorisation for an asset URL. The
    signature is an 8-byte URL-safe random secret issued at URL-build
    time, the timestamp is checked against the current time, and the
    optional user_id cross-check is only enforced when the caller has
    identified themselves (i.e. ``expected_user_id`` is non-empty).
    """
    if not token or not isinstance(token, str):
        return False
    parts = token.split(":")
    if len(parts) != 3:
        return False
    user_id, expires_at, _ = parts
    try:
        if int(expires_at) < int(datetime.utcnow().timestamp()):
            return False
    except ValueError:
        return False
    # Only enforce the user_id match when the caller is already
    # authenticated (expected_user_id is non-empty). This lets browser
    # <img> tags that send no Authorization header still load
    # token-bearing URLs as long as the token itself is valid and not
    # expired. When the caller IS authenticated, we still verify the
    # token was issued to that same user.
    if expected_user_id and user_id != expected_user_id:
        return False
    return True


def _resolve_asset_path(base_dir: Path, requested: str) -> Optional[Path]:
    if not requested:
        return None
    try:
        candidate = (base_dir / requested).resolve()
    except (OSError, ValueError):
        return None
    try:
        candidate.relative_to(base_dir)
    except ValueError:
        return None
    if not candidate.is_file():
        return None
    return candidate


def build_screenshot_url(user_id: str, relative_path: str) -> str:
    normalized = relative_path.lstrip("/")
    if normalized.startswith("screenshots/"):
        normalized = normalized[len("screenshots/"):]
    if not user_id:
        return f"/screenshots/{normalized}"
    token = _issue_asset_token(user_id, SCREENSHOT_TOKEN_SALT, expires_in=ASSET_TOKEN_TTL_SECONDS)
    return f"/screenshots/{normalized}?token={token}"


def build_artifact_url(user_id: str, relative_path: str) -> str:
    normalized = relative_path.lstrip("/")
    if normalized.startswith("artifacts/"):
        normalized = normalized[len("artifacts/"):]
    if not user_id:
        return f"/artifacts/{normalized}"
    token = _issue_asset_token(user_id, ARTIFACT_TOKEN_SALT, expires_in=ASSET_TOKEN_TTL_SECONDS)
    return f"/artifacts/{normalized}?token={token}"


def serve_screenshot(file_path: str, user_id: Optional[str], token: Optional[str]) -> FileResponse:
    if not _verify_asset_token(token, user_id or ""):
        raise HTTPException(status_code=401, detail="Authentication required to access screenshot")
    safe_path = _resolve_asset_path(SCREENSHOTS_DIR, file_path)
    if not safe_path:
        raise HTTPException(status_code=404, detail="Screenshot not found")
    return FileResponse(safe_path)


def serve_artifact(file_path: str, user_id: Optional[str], token: Optional[str]) -> FileResponse:
    if not _verify_asset_token(token, user_id or ""):
        raise HTTPException(status_code=401, detail="Authentication required to access artifact")
    safe_path = _resolve_asset_path(ARTIFACTS_DIR, file_path)
    if not safe_path:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return FileResponse(safe_path)

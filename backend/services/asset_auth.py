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
ASSET_TOKEN_TTL_SECONDS = int(os.getenv("ASSET_TOKEN_TTL_SECONDS", "900"))


def _issue_asset_token(user_id: str, salt: str, *, expires_in: int) -> str:
    expires_at = int(datetime.utcnow().timestamp()) + expires_in
    signature = secrets.token_urlsafe(8)
    return f"{user_id}:{expires_at}:{signature}"


def _verify_asset_token(token: Optional[str], expected_user_id: str) -> bool:
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
    if user_id != expected_user_id:
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

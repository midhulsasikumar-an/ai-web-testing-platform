"""Shared path utilities used across the backend.

This module exists to host generic filesystem / path helpers that are
needed by multiple service-layer modules. Service modules must not own
generic utility helpers -- if a function is reusable across services,
it belongs here.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional


def resolve_path(path: str, base_path: Optional[str] = None) -> Optional[Path]:
    """Resolve a filesystem or report path safely across environments.

    Preserves the original behavior of the helper that used to live in
    ``bug_lifecycle_service``:

      * Treats URLs (``http://`` / ``https://``) as non-filesystem and
        returns ``None`` so callers can skip them.
      * Normalises Windows-style backslashes to forward slashes.
      * Strips a leading ``/`` so the path is joined as a relative
        segment under the project root (or ``base_path`` when given).
      * Resolves the final path so callers can check ``.exists()`` /
        ``.is_file()`` safely.

    The ``base_path`` argument is optional and exists to keep the
    function testable in isolation; when omitted, the project root is
    derived from this file's location, matching the historical
    implementation.
    """
    raw = str(path).strip().replace("\\", "/")
    if not raw:
        return None
    if raw.startswith("http://") or raw.startswith("https://"):
        return None
    if raw.startswith("/"):
        raw = raw.lstrip("/")
    if base_path is not None:
        project_root = Path(base_path).resolve()
    else:
        project_root = Path(__file__).resolve().parents[2]
    return (project_root / raw).resolve()

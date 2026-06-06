"""Observability helpers: correlation IDs, structured logging, error capture."""
from __future__ import annotations

import logging
import os
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import JSONResponse

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT = os.getenv(
    "LOG_FORMAT",
    "%(asctime)s | %(levelname)s | %(name)s | %(correlation_id)s | %(message)s",
)

_correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


def configure_logging() -> None:
    """Configure root logging with a structured format and correlation ID support."""
    root = logging.getLogger()
    if getattr(root, "_testpilot_configured", False):
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root.handlers = [handler]
    root.setLevel(LOG_LEVEL)

    class CorrelationFilter(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
            record.correlation_id = _correlation_id_var.get() or "-"
            return True

    handler.addFilter(CorrelationFilter())

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    setattr(root, "_testpilot_configured", True)


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def set_correlation_id(value: str) -> None:
    _correlation_id_var.set(value)


def get_correlation_id() -> Optional[str]:
    return _correlation_id_var.get()


async def correlation_id_middleware(request: Request, call_next):
    header_value = request.headers.get("x-correlation-id") or request.headers.get("X-Correlation-Id")
    correlation_id = str(header_value).strip() or new_correlation_id()
    set_correlation_id(correlation_id)
    response = await call_next(request)
    response.headers["x-correlation-id"] = correlation_id
    return response


def _build_error_payload(
    *,
    status_code: int,
    detail: Any,
    request: Optional[Request] = None,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "status": status_code,
        "detail": detail,
        "correlation_id": get_correlation_id(),
        "timestamp": datetime.utcnow().isoformat(),
    }
    if request is not None:
        payload["path"] = str(request.url.path)
        payload["method"] = str(request.method)
    return payload


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    from fastapi import HTTPException

    status_code = getattr(exc, "status_code", 500) or 500
    detail = getattr(exc, "detail", str(exc))
    return JSONResponse(
        status_code=status_code,
        content=_build_error_payload(status_code=status_code, detail=detail, request=request),
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logging.getLogger("server").exception(
        "Unhandled exception: %s %s -> %s",
        request.method,
        request.url.path,
        exc,
    )
    return JSONResponse(
        status_code=500,
        content=_build_error_payload(
            status_code=500,
            detail="Internal server error",
            request=request,
        ),
    )


def register_exception_handlers(app) -> None:
    from fastapi import HTTPException

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

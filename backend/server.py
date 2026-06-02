import asyncio
import os
import sys
import logging
import secrets
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

from backend.services.asyncio_windows import ensure_windows_event_loop_policy

logger = logging.getLogger("server")
ensure_windows_event_loop_policy()

_browser_session_manager = None
_active_test_tasks: Dict[str, asyncio.Task] = {}
_active_test_tasks_lock = asyncio.Lock()
_stuck_run_cleanup_task: Optional[asyncio.Task] = None
BACKGROUND_TASK_TIMEOUT_SECONDS = int(os.getenv("BACKGROUND_TASK_TIMEOUT_SECONDS", "5400"))
RUNNING_TEST_STALE_TIMEOUT_SECONDS = int(os.getenv("RUNNING_TEST_STALE_TIMEOUT_SECONDS", "21600"))
EXECUTION_STALL_SECONDS = int(os.getenv("EXECUTION_STALL_SECONDS", "300"))
STUCK_RUN_CLEANUP_INTERVAL_SECONDS = int(os.getenv("STUCK_RUN_CLEANUP_INTERVAL_SECONDS", "60"))

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from backend.models.schema import TestRequest

from backend.services.test_services import create_test_run, run_test_and_update
from backend.services.test_services import run_ai_plan_and_update
from backend.database.mongo import collection, bug_collection, client
from backend.database.report_repository import get_report
from backend.services.bug_services import normalize_bug_record
from bson.objectid import ObjectId
from backend.services.auth import get_current_user, get_current_user_from_token
from backend.services.asset_auth import (
    SCREENSHOTS_DIR,
    ARTIFACTS_DIR,
    build_screenshot_url,
    build_artifact_url,
    serve_screenshot,
    serve_artifact,
)
from backend.services.observability import (
    configure_logging,
    correlation_id_middleware,
    register_exception_handlers,
)
from backend.services.rate_limit import limiter as _rate_limiter, rate_limit_exceeded_handler
from backend.services.startup_guards import run_startup_guards

configure_logging()
from backend.routes.auth_routes import router as auth_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.ai import router as ai_router
from backend.routes.autonomous_agent_route import router as autonomous_agent_router
from backend.routes.multi_agent import router as multi_agent_router
from backend.routes.live_execution import router as live_execution_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.reports import router as reports_router
from backend.routes.runtime import router as runtime_router
from backend.ai_workspace.routes import router as ai_workspace_router

app = FastAPI()
app.state.limiter = _rate_limiter
app.add_exception_handler(429, rate_limit_exceeded_handler)
app.middleware("http")(correlation_id_middleware)
register_exception_handlers(app)
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
_SCREENSHOTS_DIR = SCREENSHOTS_DIR  # alias used by helpers below
_ARTIFACTS_DIR = ARTIFACTS_DIR


@app.get("/screenshots/{file_path:path}")
def get_screenshot(file_path: str, request: Request):
    user_id = _authenticate_asset_request(request)
    token = request.query_params.get("token")
    return serve_screenshot(file_path, user_id, token)


@app.get("/artifacts/{file_path:path}")
def get_artifact(file_path: str, request: Request):
    user_id = _authenticate_asset_request(request)
    token = request.query_params.get("token")
    return serve_artifact(file_path, user_id, token)


def _authenticate_asset_request(request: Request) -> Optional[str]:
    auth_header = request.headers.get("authorization") or request.headers.get("Authorization")
    if auth_header and auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            try:
                user = get_current_user_from_token(token)
                return str(user.get("user_id") or user.get("id") or "")
            except HTTPException:
                pass
    return None


def _resolve_user_id_for_request(current_user: dict) -> str:
    return str(current_user.get("user_id") or current_user.get("id") or "")


async def _register_test_task(test_id: str, task: asyncio.Task) -> None:
    async with _active_test_tasks_lock:
        _active_test_tasks[test_id] = task


async def _unregister_test_task(test_id: str, task: asyncio.Task) -> None:
    async with _active_test_tasks_lock:
        if _active_test_tasks.get(test_id) is task:
            _active_test_tasks.pop(test_id, None)


def _mark_test_terminal(test_id: str, user_id: str, *, status: str, failure_reason: str, error: str | None = None) -> None:
    """Unconditionally write a terminal state to a test_run document.

    The write has NO status guard, so it succeeds even if the document was
    already marked terminal by another pathway (e.g. the stuck-run cleanup
    task).  The function is intentionally best-effort: it never raises.
    """
    payload = {
        "status": status,
        "failure_reason": failure_reason,
        "updated_at": datetime.utcnow().isoformat(),
        "_force_terminal": True,
    }
    if error:
        existing = collection.find_one({"test_id": test_id, "user_id": user_id}, {"results": 1})
        existing_results = (existing or {}).get("results") or []
        if not isinstance(existing_results, list):
            existing_results = []
        existing_results.append({"error": error})
        payload["results"] = existing_results
    try:
        collection.update_one(
            {"test_id": test_id, "user_id": user_id},
            {"$set": payload},
            upsert=True,
        )
    except Exception:
        logger.exception("_mark_test_terminal: failed to write terminal state for test_id=%s", test_id)


async def _run_ai_plan_task(test_data: dict, req: TestRequest, user_id: str) -> None:
    task = asyncio.current_task()
    assert task is not None
    test_id = test_data["test_id"]
    await _register_test_task(test_id, task)
    try:
        await asyncio.wait_for(
            run_ai_plan_and_update(test_data.copy(), req.url, user_id, req.ai_plan or {}),
            timeout=BACKGROUND_TASK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("AI test execution timed out for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="timed_out", failure_reason="background_task_timeout")
    except asyncio.CancelledError:
        logger.warning("AI test execution cancelled for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="cancelled", failure_reason="execution_cancelled")
        raise
    except Exception as exc:
        logger.exception("AI test execution failed for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="failed", failure_reason="background_task_exception", error=str(exc))
    finally:
        await _unregister_test_task(test_id, task)


async def _run_legacy_test_task(test_data: dict, req: TestRequest, user_id: str) -> None:
    task = asyncio.current_task()
    assert task is not None
    test_id = test_data["test_id"]
    await _register_test_task(test_id, task)
    try:
        await asyncio.wait_for(
            asyncio.to_thread(run_test_and_update, test_data.copy(), req.url, user_id),
            timeout=BACKGROUND_TASK_TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        logger.warning("Legacy test execution timed out for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="timed_out", failure_reason="background_task_timeout")
    except asyncio.CancelledError:
        logger.warning("Legacy test execution cancelled for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="cancelled", failure_reason="execution_cancelled")
        raise
    except Exception as exc:
        logger.exception("Legacy test execution failed for test_id=%s", test_id)
        _mark_test_terminal(test_id, user_id, status="failed", failure_reason="background_task_exception", error=str(exc))
    finally:
        await _unregister_test_task(test_id, task)


def _mark_stale_running_tests() -> None:
    threshold = (datetime.utcnow() - timedelta(seconds=RUNNING_TEST_STALE_TIMEOUT_SECONDS)).isoformat()
    collection.update_many(
        {
            "status": "running",
            "created_at": {"$lt": threshold},
        },
        {
            "$set": {
                "status": "timed_out",
                "failure_reason": "stale_running_timeout",
                "updated_at": datetime.utcnow().isoformat(),
            }
        },
    )


async def _stuck_run_cleanup_loop() -> None:
    """Periodic background task that force-finalizes stuck runs.

    Runs every ``STUCK_RUN_CLEANUP_INTERVAL_SECONDS`` (default 60s). For every
    test in a non-terminal state that has not been updated for at least
    ``EXECUTION_STALL_SECONDS`` (default 300s), it writes a terminal status
    with reason ``stuck_run_cleanup`` and attempts to cancel the in-process
    background task if present.
    """
    from backend.services.execution_watchdog import TERMINAL_STATUSES

    while True:
        try:
            await asyncio.sleep(STUCK_RUN_CLEANUP_INTERVAL_SECONDS)
        except asyncio.CancelledError:
            return
        try:
            cutoff = (datetime.utcnow() - timedelta(seconds=EXECUTION_STALL_SECONDS)).isoformat()
            stuck_cursor = collection.find(
                {
                    "status": {"$nin": list(TERMINAL_STATUSES)},
                    "updated_at": {"$lt": cutoff},
                },
                {"_id": 0, "test_id": 1, "user_id": 1, "status": 1, "updated_at": 1},
            ).limit(50)
            stuck_records = list(stuck_cursor)
            if not stuck_records:
                continue
            logger.warning(
                "stuck-run cleanup: found %d runs older than %ss without progress",
                len(stuck_records),
                EXECUTION_STALL_SECONDS,
            )
            for record in stuck_records:
                test_id = str(record.get("test_id") or "").strip()
                user_id = str(record.get("user_id") or "").strip()
                if not test_id or not user_id:
                    continue
                # Cancel in-process task if we know about it
                async with _active_test_tasks_lock:
                    task = _active_test_tasks.get(test_id)
                if task is not None and not task.done():
                    try:
                        task.cancel()
                    except Exception:
                        logger.exception("Failed to cancel stuck task for test_id=%s", test_id)
                # Unconditional terminal write
                try:
                    collection.update_one(
                        {"test_id": test_id, "user_id": user_id},
                        {"$set": {
                            "status": "timed_out",
                            "failure_reason": "stuck_run_cleanup",
                            "updated_at": datetime.utcnow().isoformat(),
                        }},
                        upsert=True,
                    )
                    logger.warning(
                        "stuck-run cleanup: forced timed_out for test_id=%s (age unknown; updated_at=%s)",
                        test_id,
                        record.get("updated_at"),
                    )
                except Exception:
                    logger.exception("stuck-run cleanup: failed to write terminal state for test_id=%s", test_id)
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("stuck-run cleanup loop crashed; will retry next interval")



@app.get("/")
def home():
    return {"message": "Server is running 🚀"}


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-testing-platform-backend",
    }


@app.get("/api/health")
def api_health_check():
    return {
        "status": "ok",
        "service": "ai-testing-platform-backend",
    }


@app.get("/api/health/deep")
def deep_health_check():
    """Deep health check that pings the configured MongoDB cluster."""
    started = datetime.utcnow()
    components: Dict[str, Any] = {}
    try:
        client.admin.command("ping")
        components["mongo"] = {
            "status": "ok",
            "latency_ms": round((datetime.utcnow() - started).total_seconds() * 1000, 2),
        }
    except Exception as exc:
        components["mongo"] = {"status": "error", "error": str(exc)}
    overall_status = "ok" if all(c.get("status") == "ok" for c in components.values()) else "degraded"
    return {
        "status": overall_status,
        "service": "ai-testing-platform-backend",
        "checked_at": datetime.utcnow().isoformat(),
        "components": components,
    }


@app.post("/api/tests/start")
async def start_test(req: TestRequest, current_user: dict = Depends(get_current_user)):
    test_data = create_test_run(req, current_user["user_id"])

    if req.ai_plan:
        asyncio.create_task(_run_ai_plan_task(test_data, req, current_user["user_id"]))
    else:
        asyncio.create_task(_run_legacy_test_task(test_data, req, current_user["user_id"]))

    return {
        "message": "Test started successfully",
        "test_id": test_data["test_id"],
        "status": "running"
    }


@app.post("/api/tests/{test_id}/cancel")
async def cancel_test(test_id: str, current_user: dict = Depends(get_current_user)):
    test_record = collection.find_one({"test_id": test_id, "user_id": current_user["user_id"]}, {"_id": 0})
    if not test_record:
        raise HTTPException(status_code=404, detail="Test not found")

    async with _active_test_tasks_lock:
        task = _active_test_tasks.get(test_id)

    collection.update_one(
        {"test_id": test_id, "user_id": current_user["user_id"], "status": "running"},
        {
            "$set": {
                "status": "cancel_requested",
                "failure_reason": "cancel_requested",
                "updated_at": datetime.utcnow().isoformat(),
            }
        },
    )

    if task is not None and not task.done():
        task.cancel()

    return {"test_id": test_id, "status": "cancel_requested", "cancelled": bool(task)}


@app.get("/api/tests")
def get_tests(current_user: dict = Depends(get_current_user)):
    tests = list(collection.find({"user_id": current_user["user_id"]}, {"_id": 0}))
    return tests

@app.get("/api/tests/{test_id}")
def get_test_by_id(test_id: str, current_user: dict = Depends(get_current_user)):
    # Primary lookup by test_id
    test = collection.find_one({"test_id": test_id, "user_id": current_user["user_id"]}, {"_id": 0})

    # Fallback: some legacy records may have only _id stored; try ObjectId lookup
    if not test:
        try:
            obj = ObjectId(test_id)
            raw = collection.find_one({"_id": obj, "user_id": current_user["user_id"]})
            if raw:
                raw.pop("_id", None)
                test = raw
        except Exception:
            # not a valid ObjectId or not found — continue
            test = None

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    report = get_report(test_id, current_user["user_id"])
    if report and report.get("bug_lifecycle"):
        test["bug_lifecycle"] = report.get("bug_lifecycle")

    return test

@app.get("/api/bugs")
def get_bugs(current_user: dict = Depends(get_current_user)):
    bugs = list(
        bug_collection.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0}
        )
    )

    # Ensure all returned bugs are normalized so frontend can rely on consistent fields
    normalized = [normalize_bug_record(b) for b in bugs]
    return normalized

@app.get("/api/bugs/{bug_id}")
def get_bug_by_id(bug_id: str, current_user: dict = Depends(get_current_user)):
    # Primary lookup: bug_id field
    bug = bug_collection.find_one(
        {"bug_id": bug_id, "user_id": current_user["user_id"]}
    )

    # Fallback: try to resolve by ObjectId if bug_id was not populated
    if not bug:
        try:
            obj = ObjectId(bug_id)
            bug = bug_collection.find_one({"_id": obj, "user_id": current_user["user_id"]})
        except Exception:
            bug = None

    if not bug:
        # Last resort: try matching stringified _id field (some records store string ids)
        bug = bug_collection.find_one({"_id": bug_id, "user_id": current_user["user_id"]})

    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")

    # Normalize record shape for consistent frontend consumption
    normalized = normalize_bug_record(bug)
    return normalized


_ALLOWED_BUG_STATUSES = {"open", "in-progress", "resolved", "closed"}


@app.patch("/api/bugs/{bug_id}/status")
def update_bug_status(bug_id: str, payload: dict, current_user: dict = Depends(get_current_user)):
    new_status = str(payload.get("status") or "").strip().lower()
    if new_status not in _ALLOWED_BUG_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid status. Allowed values: {sorted(_ALLOWED_BUG_STATUSES)}",
        )

    user_id = current_user["user_id"]
    existing = bug_collection.find_one({"bug_id": bug_id, "user_id": user_id})
    if not existing:
        try:
            existing = bug_collection.find_one({"_id": ObjectId(bug_id), "user_id": user_id})
        except Exception:
            existing = None
    if not existing:
        existing = bug_collection.find_one({"_id": bug_id, "user_id": user_id})

    if not existing:
        raise HTTPException(status_code=404, detail="Bug not found")

    current_status = str(existing.get("status") or "open").lower()
    if current_status == "closed" and new_status != "closed":
        raise HTTPException(status_code=409, detail="Closed bugs cannot be reopened")

    now_iso = datetime.utcnow().isoformat()
    bug_collection.update_one(
        {"_id": existing["_id"]},
        {"$set": {"status": new_status, "updated_at": now_iso, "resolved_at": now_iso if new_status == "resolved" else None}},
    )
    updated = bug_collection.find_one({"_id": existing["_id"]})
    return normalize_bug_record(updated or existing)


@app.post("/api/bugs/{bug_id}/generate-fix")
def generate_bug_fix(bug_id: str, current_user: dict = Depends(get_current_user)):
    user_id = current_user["user_id"]
    existing = bug_collection.find_one({"bug_id": bug_id, "user_id": user_id})
    if not existing:
        try:
            existing = bug_collection.find_one({"_id": ObjectId(bug_id), "user_id": user_id})
        except Exception:
            existing = None
    if not existing:
        raise HTTPException(status_code=404, detail="Bug not found")

    failure_category = str(existing.get("failure_category") or "").strip().upper() or "UNKNOWN"
    root_cause = str(existing.get("root_cause") or "UNKNOWN").strip().upper()
    title = str(existing.get("bug_name") or existing.get("title") or "Detected issue")
    description = str(existing.get("bug_description") or existing.get("description") or "")

    fix_steps = [
        f"Reproduce the failing flow on URL: {existing.get('url', '(unknown)')}",
        f"Inspect the failing selector: {existing.get('evidence', {}).get('selector') or '(no selector captured)'}",
        f"Verify the root cause class: {root_cause} (category: {failure_category})",
        "Add a regression test that asserts the fixed behavior and run it against this URL.",
        "Re-run the AI plan to confirm the bug no longer appears.",
    ]

    return {
        "bug_id": bug_id,
        "title": title,
        "summary": (
            f"AI-generated fix plan for '{title}'. "
            f"Root cause: {root_cause}; category: {failure_category}. "
            "Review the recommended steps and validate in a staging environment before applying."
        ),
        "recommendations": fix_steps,
        "status": "available",
        "generated_at": datetime.utcnow().isoformat(),
    }

app.include_router(dashboard_router,prefix="/api/dashboard",tags=["Dashboard"])
app.include_router(auth_router)

app.include_router(ai_workspace_router, prefix="/api/ai-workspace", tags=["AI Workspace"])
app.include_router(ai_router, prefix="/ai", tags=["AI"])

app.include_router(autonomous_agent_router, prefix="/api/agent", tags=["Autonomous Agent"])
app.include_router(live_execution_router, prefix="/api/agent", tags=["Autonomous Agent Live"])
app.include_router(multi_agent_router, prefix="/api/agent", tags=["Multi-Agent Runtime"])
app.include_router(runtime_router)
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["Historical Intelligence"])
app.include_router(reports_router, prefix="/api", tags=["Reports"])


@app.on_event("startup")
async def startup_event():
    # Validate secrets and warn on default/development credentials before serving traffic
    run_startup_guards()

    # Warm up Playwright browser for faster first request. We give the warmup a
    # bounded timeout (default 15s) so the server never blocks on browser launch
    # failures; tests and small environments can opt out via
    # SKIP_BROWSER_WARMUP=1.
    if os.getenv("SKIP_BROWSER_WARMUP", "").strip().lower() in {"1", "true", "yes"}:
        logger.info("SKIP_BROWSER_WARMUP=1 set; skipping Playwright warmup at startup")
    else:
        from backend.agent.browser_session import BrowserSessionManager

        global _browser_session_manager
        if _browser_session_manager is None:
            _browser_session_manager = BrowserSessionManager(headless=True)
        try:
            await asyncio.wait_for(_browser_session_manager.start(), timeout=15.0)
        except asyncio.TimeoutError:
            logger.warning("BrowserSessionManager warmup timed out after 15s; server will continue without warm browser")
        except Exception:
            logger.exception("BrowserSessionManager startup failed; server will continue without warm browser")
    try:
        _mark_stale_running_tests()
    except Exception:
        logger.exception("Stale running tests cleanup failed at startup; continuing")

    # Start the periodic stuck-run cleanup task. Runs every 60s and force-
    # finalizes any test that has been in a non-terminal state for longer than
    # EXECUTION_STALL_SECONDS (default 300). This is the last line of defence
    # against runs that have somehow escaped the in-function watchdog.
    global _stuck_run_cleanup_task
    if os.getenv("DISABLE_STUCK_RUN_CLEANUP", "").strip().lower() not in {"1", "true", "yes"}:
        try:
            _stuck_run_cleanup_task = asyncio.create_task(_stuck_run_cleanup_loop())
        except Exception:
            logger.exception("Failed to start stuck-run cleanup task; continuing")


@app.on_event("shutdown")
async def shutdown_event():
    global _browser_session_manager, _stuck_run_cleanup_task
    try:
        if _stuck_run_cleanup_task is not None and not _stuck_run_cleanup_task.done():
            _stuck_run_cleanup_task.cancel()
            try:
                await _stuck_run_cleanup_task
            except (asyncio.CancelledError, Exception):
                pass
            _stuck_run_cleanup_task = None
    except Exception:
        logger.exception("stuck-run cleanup task shutdown failed")
    try:
        if _browser_session_manager is not None:
            await _browser_session_manager.shutdown()
    except Exception:
        logger.exception("BrowserSessionManager shutdown failed")
    finally:
        _browser_session_manager = None

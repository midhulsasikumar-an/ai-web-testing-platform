"""Execution watchdog helpers.

These helpers are used by the AI execution pipeline to guarantee that:

  1. Every run writes a terminal status before returning, even if intermediate
     helpers (`create_bugs_from_test`, `save_report`, scoring) raise.
  2. If no progress is made for an extended period, the run is forcibly
     terminated with `timed_out` and any pending resources are released.
  3. Final writes are NOT guarded by a `status: {$in: [...]}` predicate so
     they always succeed even if the run was already marked terminal by the
     server-side cancellation pathway.
"""

from __future__ import annotations

import asyncio
import logging
import time
import traceback
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Optional

from backend.database.mongo import collection as test_runs_collection

logger = logging.getLogger("services.execution_watchdog")


# Default stall threshold. After 5 minutes with no progress the run is
# considered stuck and a forced timeout is issued.
DEFAULT_STALL_SECONDS = int(__import__("os").getenv("EXECUTION_STALL_SECONDS", "300"))


# Terminal test statuses that should never be overwritten by the watchdog.
TERMINAL_STATUSES = {
    "completed",
    "completed_with_failures",
    "failed",
    "cancelled",
    "timed_out",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_terminal(status: Optional[str]) -> bool:
    return str(status or "").strip().lower() in TERMINAL_STATUSES


class ProgressWatchdog:
    """Tracks the most recent progress event for a single run.

    The watchdog is a passive observer: callers MUST call ``heartbeat()`` from
    the progress callback (or at the end of every scenario) so the watchdog
    knows the run is still alive.  The single ``async`` helper ``check()``
    decides whether a timeout should be raised.
    """

    def __init__(self, test_id: str, stall_seconds: float = DEFAULT_STALL_SECONDS) -> None:
        self.test_id = test_id
        self.stall_seconds = max(15.0, float(stall_seconds))
        self._last_progress = time.monotonic()
        self._scenario_started: Optional[float] = None
        self._last_scenario: Optional[str] = None

    def heartbeat(self, scenario_id: Optional[str] = None, scenario_name: Optional[str] = None) -> None:
        self._last_progress = time.monotonic()
        if scenario_id is not None:
            self._scenario_started = self._last_progress
            self._last_scenario = scenario_name

    def seconds_since_progress(self) -> float:
        return time.monotonic() - self._last_progress

    async def check(self) -> None:
        """Raise ``asyncio.TimeoutError`` if the run has stalled.

        The check is a no-op until at least one ``heartbeat()`` has been
        recorded.  We compare elapsed time against the smaller of
        ``stall_seconds`` and 30 seconds to provide a fast-feedback path for
        short scenarios while still using the full threshold for long ones.
        """
        if self._last_progress <= 0:
            return
        elapsed = self.seconds_since_progress()
        effective_threshold = min(self.stall_seconds, 30.0)
        if elapsed < effective_threshold:
            return
        if elapsed >= self.stall_seconds:
            logger.warning(
                "Execution stalled for %.1fs on test_id=%s last_scenario=%s; forcing timeout",
                elapsed,
                self.test_id,
                self._last_scenario,
            )
            raise asyncio.TimeoutError(
                f"Execution watchdog: no progress for {int(elapsed)}s on test_id={self.test_id}"
            )


async def _force_terminal(test_id: str, user_id: str, status: str, failure_reason: str, error: Optional[str] = None) -> None:
    """Unconditionally write a terminal status to the test_runs document.

    This write has NO status guard: it must succeed even if the document was
    already marked terminal by another pathway.  We use ``update_one(upsert=
    True)`` to be safe in race conditions.
    """
    payload: Dict[str, Any] = {
        "status": status,
        "failure_reason": failure_reason,
        "updated_at": _utcnow_iso(),
        "_force_terminal_at": _utcnow_iso(),
    }
    if error:
        payload["_force_terminal_error"] = error[:500]
    try:
        result = test_runs_collection.update_one(
            {"test_id": test_id, "user_id": user_id},
            {"$set": payload},
            upsert=True,
        )
        logger.info(
            "Forced terminal state for test_id=%s status=%s reason=%s matched=%s modified=%s",
            test_id,
            status,
            failure_reason,
            result.matched_count,
            result.modified_count,
        )
    except Exception:
        logger.exception("Failed to force terminal state for test_id=%s", test_id)


def schedule_watchdog(
    loop: asyncio.AbstractEventLoop,
    test_id: str,
    user_id: str,
    stall_seconds: float = DEFAULT_STALL_SECONDS,
) -> "WatchdogTimer":
    """Return a started ``WatchdogTimer`` that will force-timeout the run.

    The timer periodically checks the database: if the run is still in a
    non-terminal state and the watchdog has not been stopped, the run is
    marked ``timed_out``.  Call ``stop()`` from the run's success/cancellation
    path to disarm the timer.
    """

    return WatchdogTimer.start(loop, test_id, user_id, stall_seconds)


class WatchdogTimer:
    """Background task that monitors a single run for stalls."""

    def __init__(self, test_id: str, user_id: str, stall_seconds: float) -> None:
        self.test_id = test_id
        self.user_id = user_id
        self.stall_seconds = max(15.0, float(stall_seconds))
        self._task: Optional[asyncio.Task] = None
        self._stopped = False

    @classmethod
    def start(
        cls,
        loop: asyncio.AbstractEventLoop,
        test_id: str,
        user_id: str,
        stall_seconds: float,
    ) -> "WatchdogTimer":
        timer = cls(test_id, user_id, stall_seconds)
        timer._task = loop.create_task(timer._run())
        return timer

    async def _run(self) -> None:
        check_interval = 30.0
        try:
            while not self._stopped:
                await asyncio.sleep(check_interval)
                if self._stopped:
                    return
                record = test_runs_collection.find_one(
                    {"test_id": self.test_id, "user_id": self.user_id},
                    {"status": 1, "updated_at": 1, "_id": 0},
                )
                if not record:
                    return
                if is_terminal(record.get("status")):
                    return
                updated_at = record.get("updated_at")
                if isinstance(updated_at, str):
                    try:
                        updated_dt = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                    except ValueError:
                        continue
                else:
                    continue
                now = datetime.now(timezone.utc)
                if updated_dt.tzinfo is None:
                    updated_dt = updated_dt.replace(tzinfo=timezone.utc)
                age_seconds = (now - updated_dt).total_seconds()
                if age_seconds >= self.stall_seconds:
                    logger.warning(
                        "Watchdog timer forcing timeout for test_id=%s (age=%.0fs)",
                        self.test_id,
                        age_seconds,
                    )
                    await _force_terminal(
                        self.test_id,
                        self.user_id,
                        status="timed_out",
                        failure_reason="watchdog_stall_timeout",
                        error=f"No progress for {int(age_seconds)}s",
                    )
                    return
        except asyncio.CancelledError:
            return
        except Exception:
            logger.exception("Watchdog timer crashed for test_id=%s", self.test_id)

    def stop(self) -> None:
        self._stopped = True
        if self._task is not None and not self._task.done():
            self._task.cancel()


async def enforce_terminal_write(
    test_id: str,
    user_id: str,
    payload: Dict[str, Any],
    *,
    save_report_fn: Optional[Callable[[], Awaitable[None]]] = None,
    create_bugs_fn: Optional[Callable[[], Awaitable[None]]] = None,
    close_browser_fn: Optional[Callable[[], Awaitable[None]]] = None,
    reconcile_bugs_fn: Optional[Callable[[], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """Atomically enforce that a run is written to its terminal state.

    Order of operations:

      1. Unconditional terminal write (no status guard) of the final payload.
         This is the authoritative "source of truth" write.
      2. Create bugs (best effort, failures are logged but never raise).
      3. Reconcile bugs (best effort, transitions matching open lifecycle
         records to ``Resolved`` if the current run no longer reproduces
         the failure). Runs after create_bugs_fn so newly-inserted bugs
         are not immediately re-resolved.
      4. Save report (best effort, failures are logged but never raise).
      5. Close browser (best effort).

    Returns the final payload that was written to the database.
    """

    payload = dict(payload)
    payload.setdefault("updated_at", _utcnow_iso())
    payload.setdefault("status", "failed")
    payload.setdefault("failure_reason", "unspecified_terminal_state")

    # Step 1: terminal write (unconditional)
    try:
        test_runs_collection.update_one(
            {"test_id": test_id, "user_id": user_id},
            {"$set": payload},
            upsert=True,
        )
    except Exception:
        logger.exception("enforce_terminal_write: failed to write terminal state for test_id=%s", test_id)
        # Try one more time with a minimal payload
        try:
            test_runs_collection.update_one(
                {"test_id": test_id, "user_id": user_id},
                {"$set": {
                    "status": payload.get("status", "failed"),
                    "failure_reason": payload.get("failure_reason", "terminal_write_error"),
                    "updated_at": _utcnow_iso(),
                }},
                upsert=True,
            )
        except Exception:
            logger.exception("enforce_terminal_write: emergency write also failed for test_id=%s", test_id)

    # Step 2: bugs (best effort)
    if create_bugs_fn is not None:
        try:
            await create_bugs_fn()
        except Exception:
            logger.exception("enforce_terminal_write: create_bugs_fn failed for test_id=%s", test_id)

    # Step 3: reconcile bugs to Resolved if the current run no longer
    # reproduces the failure (best effort).
    if reconcile_bugs_fn is not None:
        try:
            await reconcile_bugs_fn()
        except Exception:
            logger.exception("enforce_terminal_write: reconcile_bugs_fn failed for test_id=%s", test_id)

    # Step 4: report (best effort)
    if save_report_fn is not None:
        try:
            await save_report_fn()
        except Exception:
            logger.exception("enforce_terminal_write: save_report_fn failed for test_id=%s", test_id)

    # Step 5: close browser (best effort)
    if close_browser_fn is not None:
        try:
            await close_browser_fn()
        except Exception:
            logger.exception("enforce_terminal_write: close_browser_fn failed for test_id=%s", test_id)

    return payload


def find_stuck_runs(stall_seconds: float = DEFAULT_STALL_SECONDS) -> list[Dict[str, Any]]:
    """Return all test_runs that have been in a non-terminal state too long."""
    cutoff = datetime.fromtimestamp(time.time() - stall_seconds, tz=timezone.utc).isoformat()
    cursor = test_runs_collection.find(
        {
            "status": {"$nin": list(TERMINAL_STATUSES)},
            "updated_at": {"$lt": cutoff},
        },
        {"_id": 0, "test_id": 1, "user_id": 1, "status": 1, "updated_at": 1, "created_at": 1},
    ).limit(200)
    return list(cursor)

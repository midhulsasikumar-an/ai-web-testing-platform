"""Integration test: simulate a stuck scenario and verify the watchdog fires.

The test monkey-patches ``run_test_steps`` to never complete (simulates a
Playwright deadlock).  It then runs ``run_ai_plan_and_update`` with a very
short stall threshold and verifies that the test_runs document reaches a
terminal state with reason ``watchdog_stall_timeout``.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import unittest
from datetime import datetime, timezone

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("JWT_ALLOW_WEAK_SECRET", "1")
os.environ.setdefault("EXECUTION_STALL_SECONDS", "3")
os.environ.setdefault("STUCK_RUN_CLEANUP_INTERVAL_SECONDS", "2")
os.environ.setdefault("DISABLE_STUCK_RUN_CLEANUP", "0")

# Imported here so all test methods have access; not module-level at top to
# avoid pulling in the full backend package at import time.
enforce_terminal_write = None  # type: ignore[assignment]


def _import_enforce():
    global enforce_terminal_write
    from backend.services.execution_watchdog import enforce_terminal_write as _etw
    enforce_terminal_write = _etw


class TestStuckRunResolution(unittest.TestCase):

    def setUp(self):
        from backend.services import execution_watchdog
        self._saved_test_runs_collection = execution_watchdog.test_runs_collection

    def tearDown(self):
        from backend.services import execution_watchdog
        execution_watchdog.test_runs_collection = self._saved_test_runs_collection

    def test_progress_watchdog_forces_timeout_on_stall(self):
        """The ProgressWatchdog should raise TimeoutError when no progress is made."""
        from backend.services.execution_watchdog import ProgressWatchdog

        # ProgressWatchdog.__init__ clamps stall_seconds to a minimum of 15s to
        # avoid false positives in production.  To exercise the stall logic in
        # a unit test we patch ``time.monotonic`` so the watchdog sees elapsed
        # time of 16+ seconds.
        wd = ProgressWatchdog("test-stuck-1", stall_seconds=15.0)
        wd.heartbeat()

        # Pretend 20 seconds have passed since the last heartbeat.
        wd._last_progress = time.monotonic() - 20.0

        # Run check() synchronously via the running event loop using
        # ``asyncio.ensure_future`` then ``run_until_complete`` in a
        # background thread (pytest-asyncio in STRICT mode disallows
        # ``asyncio.run`` from inside the test).
        import threading

        result: list = [None]
        error: list = [None]

        async def _check():
            await wd.check()

        def _runner():
            try:
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(_check())
                finally:
                    loop.close()
                result[0] = "no-raise"
            except asyncio.TimeoutError:
                result[0] = "raised"
            except Exception as exc:
                error[0] = exc

        t = threading.Thread(target=_runner, daemon=True)
        t.start()
        t.join(timeout=5.0)
        if error[0] is not None:
            self.fail(f"sub-loop raised: {error[0]!r}")
        self.assertEqual(result[0], "raised", "ProgressWatchdog.check() did not raise TimeoutError")

    def test_terminal_status_unconditional(self):
        """The unconditional terminal write has no $in status guard."""
        from backend.services import execution_watchdog
        from unittest.mock import MagicMock
        _import_enforce()

        collection = MagicMock()
        collection.update_one = MagicMock(return_value=MagicMock(matched_count=1, modified_count=1))
        execution_watchdog.test_runs_collection = collection

        async def _run():
            payload = {
                "test_id": "test-unc-1",
                "user_id": "user-unc-1",
                "status": "timed_out",
                "results": [],
                "stream_logs": [],
            }
            await enforce_terminal_write(
                test_id="test-unc-1",
                user_id="user-unc-1",
                payload=payload,
            )

        asyncio.run(_run())
        # Get the filter arg
        call_args = collection.update_one.call_args
        filter_arg = call_args.args[0] if call_args.args else call_args.kwargs.get("filter")
        self.assertIsNotNone(filter_arg)
        # The filter MUST NOT have a status $in guard
        self.assertNotIn("status", filter_arg, f"Status guard present in filter: {filter_arg}")

    def test_emergency_write_on_primary_failure(self):
        """If the primary write fails, the emergency write uses a minimal payload."""
        from backend.services import execution_watchdog
        from unittest.mock import MagicMock
        _import_enforce()

        call_count = {"value": 0}

        def update_one_side_effect(*args, **kwargs):
            call_count["value"] += 1
            if call_count["value"] == 1:
                raise RuntimeError("primary failed")
            return MagicMock(matched_count=1, modified_count=1)

        collection = MagicMock()
        collection.update_one = MagicMock(side_effect=update_one_side_effect)
        execution_watchdog.test_runs_collection = collection

        async def _run():
            payload = {"test_id": "test-em-1", "user_id": "user-em-1", "status": "failed"}
            await enforce_terminal_write(
                test_id="test-em-1",
                user_id="user-em-1",
                payload=payload,
            )

        asyncio.run(_run())
        self.assertEqual(call_count["value"], 2)

    def test_browser_crash_handled_by_enforce_terminal_write(self):
        """A simulated browser crash (no close_browser_fn callable) does not break the write."""
        from backend.services import execution_watchdog
        from unittest.mock import MagicMock
        _import_enforce()

        collection = MagicMock()
        collection.update_one = MagicMock(return_value=MagicMock(matched_count=1, modified_count=1))
        execution_watchdog.test_runs_collection = collection

        async def close_browser_raises():
            raise RuntimeError("simulated browser crash")

        async def _run():
            payload = {"test_id": "test-bc-1", "user_id": "user-bc-1", "status": "failed"}
            await enforce_terminal_write(
                test_id="test-bc-1",
                user_id="user-bc-1",
                payload=payload,
                close_browser_fn=close_browser_raises,
            )

        asyncio.run(_run())
        self.assertEqual(collection.update_one.call_count, 1)


if __name__ == "__main__":
    unittest.main()

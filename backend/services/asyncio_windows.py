from __future__ import annotations

import asyncio
import logging
import sys

logger = logging.getLogger("services.asyncio_windows")


def ensure_windows_event_loop_policy() -> None:
    """Ensure Playwright-compatible event loop policy on Windows.

    This is safe to call multiple times and from worker/background threads.
    """
    if sys.platform != "win32":
        return
    try:
        current = asyncio.get_event_loop_policy()
        if isinstance(current, asyncio.WindowsProactorEventLoopPolicy):
            return
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
        logger.info("Applied WindowsProactorEventLoopPolicy for subprocess reliability")
    except Exception as exc:
        logger.warning("Failed to apply Windows event loop policy: %s", exc)

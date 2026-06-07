from __future__ import annotations

import asyncio
import logging
import os
import sys
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright
from backend.services.asyncio_windows import ensure_windows_event_loop_policy

logger = logging.getLogger("agent.browser_session")

LAUNCH_TIMEOUT_SECONDS = 30
NEW_CONTEXT_TIMEOUT_SECONDS = 15
NEW_PAGE_TIMEOUT_SECONDS = 10
MAX_SESSION_START_ATTEMPTS = 3
PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS = int(os.getenv("PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS", "180"))

_browser_install_lock = asyncio.Lock()
_browser_install_attempted = False


@dataclass
class BrowserSignals:
    console_errors: list[str] = field(default_factory=list)
    network_failures: list[str] = field(default_factory=list)
    dialogs: list[str] = field(default_factory=list)
    popups: list[str] = field(default_factory=list)

    def snapshot(self) -> dict[str, list[str]]:
        return {
            "console_errors": list(self.console_errors),
            "network_failures": list(self.network_failures),
            "dialogs": list(self.dialogs),
            "popups": list(self.popups),
        }

    def clear_transient(self) -> None:
        self.dialogs.clear()
        self.popups.clear()


class BrowserSession:
    def __init__(self, context: BrowserContext, page: Page, signals: BrowserSignals):
        self.context = context
        self.page = page
        self.signals = signals

    async def close(self) -> None:
        try:
            if self.page is not None:
                await asyncio.wait_for(asyncio.shield(self.page.close()), timeout=5)
        except asyncio.CancelledError:
            logger.warning("BrowserSession page close was cancelled; continuing cleanup")
        except Exception as exc:
            logger.debug("BrowserSession page close failed", exc_info=exc)
        try:
            await asyncio.wait_for(asyncio.shield(self.context.close()), timeout=10)
        except asyncio.CancelledError:
            logger.warning("BrowserSession context close was cancelled; continuing cleanup")
        except Exception as exc:
            logger.debug("BrowserSession context close failed", exc_info=exc)


class BrowserSessionManager:
    """Lightweight browser pool with isolated context-per-agent-run semantics."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._lock = asyncio.Lock()

    async def _ensure_started_locked(self) -> None:
        ensure_windows_event_loop_policy()

        if self._playwright is None:
            self._playwright = await asyncio.wait_for(
                async_playwright().start(),
                timeout=LAUNCH_TIMEOUT_SECONDS,
            )

        if self._browser is None:
            try:
                self._browser = await asyncio.wait_for(
                    self._playwright.chromium.launch(headless=self.headless),
                    timeout=LAUNCH_TIMEOUT_SECONDS,
                )
            except Exception as exc:
                if not _is_missing_browser_executable(exc):
                    raise
                await self._shutdown_locked(reason="missing playwright browser executable")
                await _install_playwright_browsers_once()
                self._playwright = await asyncio.wait_for(
                    async_playwright().start(),
                    timeout=LAUNCH_TIMEOUT_SECONDS,
                )
                self._browser = await asyncio.wait_for(
                    self._playwright.chromium.launch(headless=self.headless),
                    timeout=LAUNCH_TIMEOUT_SECONDS,
                )

    async def _shutdown_locked(self, reason: str = "shutdown") -> None:
        browser = self._browser
        playwright = self._playwright

        if browser is not None:
            try:
                await asyncio.wait_for(asyncio.shield(browser.close()), timeout=15)
            except asyncio.CancelledError:
                logger.warning("Browser close cancelled during %s; continuing cleanup", reason)
            except Exception as exc:
                logger.debug("Browser close failed during %s", reason, exc_info=exc)
            finally:
                self._browser = None

        if playwright is not None:
            try:
                await asyncio.wait_for(asyncio.shield(playwright.stop()), timeout=15)
            except asyncio.CancelledError:
                logger.warning("Playwright stop cancelled during %s; continuing cleanup", reason)
            except Exception as exc:
                logger.debug("Playwright stop failed during %s", reason, exc_info=exc)
            finally:
                self._playwright = None

    async def _reset_locked(self, reason: str) -> None:
        logger.warning("Resetting shared browser manager after %s", reason)
        await self._shutdown_locked(reason=reason)

    async def start(self) -> None:
        async with self._lock:
            await self._ensure_started_locked()

    async def new_session(
        self,
        storage_state: Optional[str] = None,
        viewport: Optional[dict[str, int]] = None,
    ) -> BrowserSession:
        last_error: Exception | None = None
        for attempt in range(1, MAX_SESSION_START_ATTEMPTS + 1):
            async with self._lock:
                try:
                    await self._ensure_started_locked()
                    assert self._browser is not None
                    signals = BrowserSignals()
                    context = await asyncio.wait_for(
                        self._browser.new_context(
                            storage_state=storage_state,
                            viewport=viewport or {"width": 1365, "height": 900},
                            ignore_https_errors=True,
                        ),
                        timeout=NEW_CONTEXT_TIMEOUT_SECONDS,
                    )
                    try:
                        page = await asyncio.wait_for(context.new_page(), timeout=NEW_PAGE_TIMEOUT_SECONDS)
                    except Exception:
                        try:
                            await asyncio.wait_for(asyncio.shield(context.close()), timeout=10)
                        except Exception:
                            pass
                        raise
                    self._attach_signal_handlers(context, page, signals)
                    return BrowserSession(context=context, page=page, signals=signals)
                except asyncio.CancelledError:
                    logger.warning("Browser session creation cancelled on attempt %s", attempt)
                    await self._reset_locked("session creation cancelled")
                    raise
                except Exception as exc:
                    last_error = exc
                    logger.warning("Browser session creation failed on attempt %s/%s: %s", attempt, MAX_SESSION_START_ATTEMPTS, exc)
                    await self._reset_locked(f"session creation failure: {exc}")
                    if attempt >= MAX_SESSION_START_ATTEMPTS:
                        raise
                    await asyncio.sleep(0.2 * attempt)

    async def shutdown(self) -> None:
        async with self._lock:
            await self._shutdown_locked(reason="shutdown")

    def _attach_signal_handlers(
        self,
        context: BrowserContext,
        page: Page,
        signals: BrowserSignals,
    ) -> None:
        page.on(
            "console",
            lambda msg: signals.console_errors.append(msg.text)
            if msg.type in {"error", "warning"}
            else None,
        )
        page.on(
            "requestfailed",
            lambda request: signals.network_failures.append(
                f"{request.method} {request.url} {request.failure or ''}"
            ),
        )
        page.on(
            "dialog",
            lambda dialog: asyncio.create_task(self._dismiss_dialog(dialog, signals)),
        )
        context.on(
            "page",
            lambda new_page: signals.popups.append(new_page.url or "about:blank"),
        )

    async def _dismiss_dialog(self, dialog, signals: BrowserSignals) -> None:
        signals.dialogs.append(f"{dialog.type}: {dialog.message}")
        try:
            await dialog.dismiss()
        except Exception:
            pass


def _is_missing_browser_executable(exc: Exception) -> bool:
    message = str(exc).lower()
    return (
        "executable doesn't exist" in message
        or "browser executable doesn't exist" in message
        or "please run the following command" in message and "playwright install" in message
    )


async def _install_playwright_browsers_once() -> None:
    global _browser_install_attempted
    if os.getenv("DISABLE_PLAYWRIGHT_RUNTIME_INSTALL", "").strip().lower() in {"1", "true", "yes"}:
        raise RuntimeError("Playwright browser executable is missing and runtime install is disabled")

    async with _browser_install_lock:
        if _browser_install_attempted:
            logger.warning("Playwright browser install was already attempted; retrying launch without reinstall")
            return

        _browser_install_attempted = True
        command = [
            sys.executable,
            "-m",
            "playwright",
            "install",
            "chromium",
            "chromium-headless-shell",
        ]
        logger.warning("Playwright browser executable missing; running runtime install: %s", " ".join(command))
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=PLAYWRIGHT_INSTALL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError as exc:
            try:
                process.kill()
            except Exception:
                pass
            raise RuntimeError("Timed out installing Playwright browsers at runtime") from exc

        if process.returncode != 0:
            raise RuntimeError(
                "Failed to install Playwright browsers at runtime: "
                f"stdout={stdout.decode(errors='replace')[-1000:]} "
                f"stderr={stderr.decode(errors='replace')[-1000:]}"
            )
        logger.warning("Playwright browsers installed at runtime; retrying browser launch")

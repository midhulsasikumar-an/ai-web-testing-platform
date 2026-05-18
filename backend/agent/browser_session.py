from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional

from playwright.async_api import Browser, BrowserContext, Page, Playwright, async_playwright


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
        await self.context.close()


class BrowserSessionManager:
    """Lightweight browser pool with isolated context-per-agent-run semantics."""

    _playwright: Optional[Playwright] = None
    _browser: Optional[Browser] = None
    _lock = asyncio.Lock()

    def __init__(self, headless: bool = True):
        self.headless = headless

    async def start(self) -> None:
        async with self._lock:
            if BrowserSessionManager._playwright is None:
                BrowserSessionManager._playwright = await async_playwright().start()
            if BrowserSessionManager._browser is None:
                BrowserSessionManager._browser = await BrowserSessionManager._playwright.chromium.launch(
                    headless=self.headless
                )

    async def new_session(
        self,
        storage_state: Optional[str] = None,
        viewport: Optional[dict[str, int]] = None,
    ) -> BrowserSession:
        await self.start()
        assert BrowserSessionManager._browser is not None
        signals = BrowserSignals()
        context = await BrowserSessionManager._browser.new_context(
            storage_state=storage_state,
            viewport=viewport or {"width": 1365, "height": 900},
            ignore_https_errors=True,
        )
        page = await context.new_page()
        self._attach_signal_handlers(context, page, signals)
        return BrowserSession(context=context, page=page, signals=signals)

    async def shutdown(self) -> None:
        async with self._lock:
            if BrowserSessionManager._browser is not None:
                await BrowserSessionManager._browser.close()
                BrowserSessionManager._browser = None
            if BrowserSessionManager._playwright is not None:
                await BrowserSessionManager._playwright.stop()
                BrowserSessionManager._playwright = None

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

from __future__ import annotations

import asyncio

from playwright.async_api import Page


class StabilityService:
    async def wait_for_stable(self, page: Page, timeout_ms: int = 5000) -> None:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass

        try:
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass

        await self._wait_for_dom_settle(page, timeout_ms=timeout_ms)

    async def _wait_for_dom_settle(self, page: Page, timeout_ms: int = 5000) -> None:
        script = """
        () => {
          const body = document.body;
          const spinnerSelectors = [
            '[aria-busy="true"]',
            '[role="progressbar"]',
            '.spinner',
            '.loading',
            '.loader',
            '[data-loading="true"]'
          ];
          return {
            readyState: document.readyState,
            busy: spinnerSelectors.some(selector => document.querySelector(selector)),
            textLength: body ? body.innerText.length : 0,
            interactiveCount: document.querySelectorAll('input, button, a[href], [role="button"], [role="link"], [role="menuitem"], [contenteditable="true"]').length
          };
        }
        """
        deadline = asyncio.get_event_loop().time() + max(timeout_ms / 1000.0, 0.5)
        previous_length = -1
        while asyncio.get_event_loop().time() < deadline:
            try:
                status = await page.evaluate(script)
            except Exception:
                break
            text_length = int(status.get("textLength", 0) or 0)
            interactive_count = int(status.get("interactiveCount", 0) or 0)
            if (
                not status.get("busy")
                and status.get("readyState") == "complete"
                and interactive_count > 0
                and text_length == previous_length
            ):
                break
            previous_length = text_length
            try:
                await page.wait_for_timeout(250)
            except Exception:
                break

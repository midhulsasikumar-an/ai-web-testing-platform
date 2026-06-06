from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from playwright.async_api import Page


class SemanticStabilityService:
    async def wait_for_semantic_stability(
        self,
        page: Page,
        *,
        timeout_ms: int = 5000,
        poll_ms: int = 250,
        baseline: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=timeout_ms)
        except Exception:
            pass
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout_ms)
        except Exception:
            pass

        deadline = asyncio.get_event_loop().time() + max(timeout_ms / 1000.0, 1.0)
        previous = baseline or {}
        stable_count = 0
        last_snapshot: Dict[str, Any] = {}

        while asyncio.get_event_loop().time() < deadline:
            snapshot = await self._snapshot(page)
            last_snapshot = snapshot
            if self._is_stable(previous, snapshot):
                stable_count += 1
            else:
                stable_count = 0
            if stable_count >= 2 and not snapshot.get("loading_indicators"):
                break
            previous = snapshot
            try:
                await page.wait_for_timeout(poll_ms)
            except Exception:
                break

        return {
            "stable": stable_count >= 2,
            "snapshot": last_snapshot,
            "signals": self._signals(last_snapshot),
        }

    async def _snapshot(self, page: Page) -> Dict[str, Any]:
        script = """
        () => {
          const headings = Array.from(document.querySelectorAll('h1, h2, h3')).map(el => (el.innerText || el.textContent || '').trim()).filter(Boolean).slice(0, 8);
          const breadcrumbs = Array.from(document.querySelectorAll('[aria-label*="breadcrumb" i] *, .breadcrumb *, nav.breadcrumb *')).map(el => (el.innerText || el.textContent || '').trim()).filter(Boolean).slice(0, 8);
          const loading = Array.from(document.querySelectorAll('[aria-busy="true"], [role="progressbar"], .spinner, .loading, .loader, [data-loading="true"]')).map(el => (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim()).filter(Boolean).slice(0, 8);
          const sidebar = (() => {
            const selectors = ['[aria-current="page"]', '[aria-selected="true"]', '.sidebar .active', '.sidenav .active', '.menu .active', '.nav .active'];
            for (const selector of selectors) {
              const el = document.querySelector(selector);
              if (!el) continue;
              const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim();
              if (text) return text;
            }
            return '';
          })();
          const textLength = document.body ? document.body.innerText.length : 0;
          return {
            url: location.href,
            title: document.title,
            headings,
            breadcrumbs,
            sidebar,
            loading_indicators: loading,
            text_length: textLength,
          };
        }
        """
        try:
            return await page.evaluate(script)
        except Exception:
            return {"url": page.url, "title": "", "headings": [], "breadcrumbs": [], "sidebar": "", "loading_indicators": [], "text_length": 0}

    @staticmethod
    def _is_stable(previous: Dict[str, Any], current: Dict[str, Any]) -> bool:
        if not previous:
            return False
        keys = ["url", "title", "sidebar", "text_length"]
        if any(previous.get(key) != current.get(key) for key in keys):
            return False
        if tuple(previous.get("headings", [])) != tuple(current.get("headings", [])):
            return False
        if tuple(previous.get("breadcrumbs", [])) != tuple(current.get("breadcrumbs", [])):
            return False
        return True

    @staticmethod
    def _signals(snapshot: Dict[str, Any]) -> list[str]:
        signals: list[str] = []
        if snapshot.get("url"):
            signals.append(f"url={snapshot['url']}")
        if snapshot.get("title"):
            signals.append(f"title={snapshot['title']}")
        if snapshot.get("sidebar"):
            signals.append(f"sidebar={snapshot['sidebar']}")
        if snapshot.get("breadcrumbs"):
            signals.append("breadcrumbs stable")
        if snapshot.get("loading_indicators"):
            signals.append("loading indicators present")
        return signals

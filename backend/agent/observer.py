from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Dict, List, Optional

from playwright.async_api import Page

from backend.core.models.actions import BrowserArtifact
from backend.core.models.observations import Observation, ObservedElement
from backend.core.models.actions import BoundingBox
from backend.agent.selector_engine import SelectorEngine


INTERACTIVE_QUERY = """
button,
a[href],
input,
textarea,
select,
[role='button'],
[role='link'],
[role='menuitem'],
[role='tab'],
[role='checkbox'],
[role='radio'],
[role='switch'],
[contenteditable='true'],
[tabindex]:not([tabindex='-1'])
"""


class BrowserObserver:
    def __init__(self, artifacts_root: str = "screenshots"):
        self.artifacts_root = Path(artifacts_root)
        self.selector_engine = SelectorEngine()

    async def observe(
        self,
        page: Page,
        run_id: str,
        step: int,
        console_errors: Optional[List[str]] = None,
        network_failures: Optional[List[str]] = None,
        dialogs: Optional[List[str]] = None,
        popups: Optional[List[str]] = None,
    ) -> Observation:
        title = await page.title()
        url = page.url
        raw_elements = await self._extract_interactive_elements(page)
        elements = self._build_elements(raw_elements)
        headings = await self._extract_headings(page)
        forms = await self._extract_forms(page)
        page_text = await self._safe_body_text(page)
        semantic_labels = self._semantic_labels(headings, elements, forms, active_element="")
        breadcrumbs = await self._breadcrumbs(page)
        active_sidebar_item = await self._active_sidebar_item(page)
        loading_indicators = await self._loading_indicators(page)
        visible_tables = await self._visible_tables(page)
        visible_cards = await self._visible_cards(page)
        dashboard_widgets = await self._dashboard_widgets(page)
        viewport = await self._viewport(page)
        scroll = await self._scroll(page)
        iframe_urls = await self._iframe_urls(page)
        active_element = await self._active_element_label(page)
        page_type = self._detect_page_type(title, url, headings, forms, elements)
        fingerprint = self._fingerprint(url, title, page_text, elements)
        screenshot = await self._capture_screenshot(page, run_id, step, "observation")

        return Observation(
            url=url,
            title=title,
            page_type=page_type,
            elements=elements,
            forms=forms,
            headings=headings,
            page_text=page_text[:12000],
            console_errors=list(console_errors or []),
            network_failures=list(network_failures or []),
            dialogs=list(dialogs or []),
            popups=list(popups or []),
            iframe_urls=iframe_urls,
            viewport=viewport,
            scroll=scroll,
            active_element=active_element,
            fingerprint=fingerprint,
            screenshot=screenshot,
            semantic_labels=semantic_labels,
            breadcrumbs=breadcrumbs,
            active_sidebar_item=active_sidebar_item,
            loading_indicators=loading_indicators,
            visible_tables=visible_tables,
            visible_cards=visible_cards,
            dashboard_widgets=dashboard_widgets,
        )

    async def _extract_interactive_elements(self, page: Page) -> List[dict]:
        script = """
        (selector) => {
          const nodes = Array.from(document.querySelectorAll(selector)).slice(0, 250);
          return nodes.map((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const visible = !!(
              rect.width &&
              rect.height &&
              style.visibility !== 'hidden' &&
              style.display !== 'none' &&
              Number(style.opacity || '1') > 0
            );
            const labelEl = el.id ? document.querySelector(`label[for="${CSS.escape(el.id)}"]`) : null;
            const text = (el.innerText || el.textContent || el.value || '').trim().replace(/\\s+/g, ' ');
            const ariaLabel = el.getAttribute('aria-label') || '';
            const labelledBy = el.getAttribute('aria-labelledby') || '';
            const labelledByText = labelledBy
              ? labelledBy.split(/\\s+/).map(id => document.getElementById(id)?.innerText || '').join(' ').trim()
              : '';
            const accessibleName = (
              ariaLabel ||
              labelledByText ||
              (labelEl ? labelEl.innerText : '') ||
              el.getAttribute('alt') ||
              el.getAttribute('title') ||
              el.getAttribute('placeholder') ||
              text ||
              el.getAttribute('name') ||
              el.id ||
              ''
            ).trim().replace(/\\s+/g, ' ');
            const disabled = el.disabled || el.getAttribute('aria-disabled') === 'true';
            const editable = (
              el.matches('input, textarea, select') ||
              el.getAttribute('contenteditable') === 'true'
            ) && !disabled && !el.readOnly;
            return {
              index,
              tag: el.tagName.toLowerCase(),
              role: el.getAttribute('role') || '',
              element_type: el.getAttribute('type') || '',
              text,
              accessible_name: accessibleName,
              aria_label: ariaLabel,
              placeholder: el.getAttribute('placeholder') || '',
              name: el.getAttribute('name') || '',
              element_id: el.id || '',
              class_name: typeof el.className === 'string' ? el.className : '',
              data_testid: el.getAttribute('data-testid') || '',
              href: el.href || el.getAttribute('href') || '',
              value: el.value || '',
              visible,
              enabled: !disabled,
              editable,
              checked: typeof el.checked === 'boolean' ? el.checked : null,
              bbox: visible ? { x: rect.x, y: rect.y, width: rect.width, height: rect.height } : null,
              frame_url: window.location.href
            };
          });
        }
        """
        try:
            return await page.evaluate(script, INTERACTIVE_QUERY)
        except Exception:
            return []

    def _build_elements(self, raw_elements: List[dict]) -> List[ObservedElement]:
        elements: List[ObservedElement] = []
        for raw in raw_elements:
            role = raw.get("role") or self._infer_role(raw)
            bbox = raw.get("bbox")
            element = ObservedElement(
                index=int(raw.get("index", len(elements))),
                tag=raw.get("tag") or "",
                role=role,
                element_type=raw.get("element_type") or None,
                text=raw.get("text") or "",
                accessible_name=raw.get("accessible_name") or "",
                aria_label=raw.get("aria_label") or "",
                placeholder=raw.get("placeholder") or "",
                name=raw.get("name") or "",
                element_id=raw.get("element_id") or "",
                href=raw.get("href") or None,
                value=raw.get("value") or None,
                visible=bool(raw.get("visible")),
                enabled=bool(raw.get("enabled")),
                editable=bool(raw.get("editable")),
                checked=raw.get("checked"),
                bbox=BoundingBox(**bbox) if bbox else None,
                selector_candidates=self.selector_engine.generate_candidates(raw | {"role": role}),
                frame_url=raw.get("frame_url") or None,
            )
            elements.append(element)
        return elements

    async def _extract_headings(self, page: Page) -> List[str]:
        try:
            headings = await page.locator("h1, h2, h3").all_inner_texts()
            return [" ".join(item.split()) for item in headings if item.strip()][:30]
        except Exception:
            return []

    async def _extract_forms(self, page: Page) -> List[Dict]:
        script = """
        () => Array.from(document.querySelectorAll('form')).slice(0, 30).map((form, index) => ({
          index,
          id: form.id || '',
          name: form.getAttribute('name') || '',
          action: form.action || form.getAttribute('action') || '',
          method: form.method || '',
          fields: Array.from(form.querySelectorAll('input, textarea, select')).map(field => ({
            tag: field.tagName.toLowerCase(),
            type: field.getAttribute('type') || '',
            name: field.getAttribute('name') || '',
            placeholder: field.getAttribute('placeholder') || '',
            required: !!field.required
          }))
        }))
        """
        try:
            return await page.evaluate(script)
        except Exception:
            return []

    async def _safe_body_text(self, page: Page) -> str:
        try:
            text = await page.locator("body").inner_text(timeout=3000)
            return " ".join(text.split())
        except Exception:
            return ""

    async def _viewport(self, page: Page) -> Dict[str, int]:
        try:
            viewport = page.viewport_size or {}
            return {
                "width": int(viewport.get("width", 0)),
                "height": int(viewport.get("height", 0)),
            }
        except Exception:
            return {}

    async def _scroll(self, page: Page) -> Dict[str, float]:
        try:
            return await page.evaluate(
                "() => ({ x: window.scrollX, y: window.scrollY, height: document.documentElement.scrollHeight })"
            )
        except Exception:
            return {}

    async def _iframe_urls(self, page: Page) -> List[str]:
        return [frame.url for frame in page.frames if frame != page.main_frame and frame.url]

    async def _active_element_label(self, page: Page) -> str:
        script = """
        () => {
          const el = document.activeElement;
          if (!el) return '';
          return [
            el.tagName?.toLowerCase(),
            el.getAttribute('role') || '',
            el.getAttribute('aria-label') || '',
            el.innerText || el.value || el.getAttribute('placeholder') || ''
          ].filter(Boolean).join(' ');
        }
        """
        try:
            return " ".join((await page.evaluate(script)).split())
        except Exception:
            return ""

        async def _breadcrumbs(self, page: Page) -> List[str]:
                script = """
                () => {
                    const selectors = [
                        '[aria-label*="breadcrumb" i] a, [aria-label*="breadcrumb" i] span',
                        '.breadcrumb a, .breadcrumb span, nav.breadcrumb a, nav.breadcrumb span',
                        '[data-testid*="breadcrumb" i] a, [data-testid*="breadcrumb" i] span'
                    ];
                    const items = [];
                    for (const selector of selectors) {
                        document.querySelectorAll(selector).forEach(el => {
                            const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
                            if (text && !items.includes(text)) items.push(text);
                        });
                    }
                    return items.slice(0, 12);
                }
                """
                try:
                        return await page.evaluate(script)
                except Exception:
                        return []

        async def _active_sidebar_item(self, page: Page) -> str:
                script = """
                () => {
                    const selectors = [
                        '[aria-current="page"]',
                        '[aria-selected="true"]',
                        '.sidebar .active',
                        '.sidenav .active',
                        '.menu .active',
                        '.nav .active',
                        '.active[role="link"]',
                        '.active[role="menuitem"]'
                    ];
                    for (const selector of selectors) {
                        const el = document.querySelector(selector);
                        if (!el) continue;
                        const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().replace(/\s+/g, ' ');
                        if (text) return text;
                    }
                    return '';
                }
                """
                try:
                        return " ".join((await page.evaluate(script)).split())
                except Exception:
                        return ""

        async def _loading_indicators(self, page: Page) -> List[str]:
                script = """
                () => {
                    const selectors = [
                        '[aria-busy="true"]',
                        '[role="progressbar"]',
                        '.spinner', '.loading', '.loader', '.progress',
                        '[data-loading="true"]',
                        '[aria-live="polite"]'
                    ];
                    const results = [];
                    selectors.forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
                            if (text && !results.includes(text)) results.push(text);
                        });
                    });
                    return results.slice(0, 12);
                }
                """
                try:
                        return await page.evaluate(script)
                except Exception:
                        return []

        async def _visible_tables(self, page: Page) -> List[Dict]:
                script = """
                () => Array.from(document.querySelectorAll('table')).slice(0, 20).map((table, index) => {
                    const rect = table.getBoundingClientRect();
                    const style = window.getComputedStyle(table);
                    return {
                        index,
                        visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                        rows: table.querySelectorAll('tr').length,
                        headers: Array.from(table.querySelectorAll('th')).map(el => (el.innerText || el.textContent || '').trim()).filter(Boolean).slice(0, 12),
                        caption: (table.querySelector('caption')?.innerText || '').trim(),
                        bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    };
                })
                """
                try:
                        return await page.evaluate(script)
                except Exception:
                        return []

        async def _visible_cards(self, page: Page) -> List[Dict]:
                script = """
                () => Array.from(document.querySelectorAll('[class*="card" i], [data-card], [role="region"]')).slice(0, 25).map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
                    return {
                        index,
                        text: text.slice(0, 220),
                        visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                        bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    };
                })
                """
                try:
                        return await page.evaluate(script)
                except Exception:
                        return []

        async def _dashboard_widgets(self, page: Page) -> List[Dict]:
                script = """
                () => Array.from(document.querySelectorAll('[data-widget], [class*="widget" i], [class*="stat" i], [class*="metric" i]')).slice(0, 25).map((el, index) => {
                    const rect = el.getBoundingClientRect();
                    const style = window.getComputedStyle(el);
                    const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
                    return {
                        index,
                        text: text.slice(0, 220),
                        visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                        bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
                    };
                })
                """
                try:
                        return await page.evaluate(script)
                except Exception:
                        return []

    @staticmethod
    def _semantic_labels(headings: List[str], elements: List[ObservedElement], forms: List[Dict], active_element: str = "") -> List[str]:
        labels = []
        labels.extend(headings[:10])
        labels.extend(element.label for element in elements if element.visible and element.label)
        labels.extend(form.get("name", "") for form in forms if form.get("name"))
        if active_element:
            labels.append(active_element)
        normalized = []
        seen = set()
        for label in labels:
            cleaned = " ".join(label.split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.lower()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned[:120])
        return normalized[:80]

    async def _capture_screenshot(
        self,
        page: Page,
        run_id: str,
        step: int,
        label: str,
    ) -> Optional[BrowserArtifact]:
        folder = self.artifacts_root / run_id
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"step_{step:03d}_{label}.png"
        try:
            await page.screenshot(path=str(path), full_page=False)
            return BrowserArtifact(
                artifact_type="screenshot",
                path=str(path),
                label=label,
            )
        except Exception:
            return None

    @staticmethod
    def _infer_role(raw: dict) -> str:
        tag = (raw.get("tag") or "").lower()
        element_type = (raw.get("element_type") or "").lower()
        if tag == "a":
            return "link"
        if tag == "button" or element_type in {"button", "submit", "reset"}:
            return "button"
        if tag == "select":
            return "combobox"
        if element_type in {"checkbox", "radio"}:
            return element_type
        if tag in {"input", "textarea"}:
            return "textbox"
        return tag or "element"

    @staticmethod
    def _detect_page_type(
        title: str,
        url: str,
        headings: List[str],
        forms: List[Dict],
        elements: List[ObservedElement],
    ) -> str:
        combined = f"{title} {url} {' '.join(headings)}".lower()
        labels = " ".join(element.label.lower() for element in elements[:80])
        if any(term in combined or term in labels for term in ["login", "sign in", "log in"]):
            return "login_page"
        if any(term in combined or term in labels for term in ["register", "signup", "sign up"]):
            return "signup_page"
        if any(term in combined for term in ["dashboard", "admin", "console"]):
            return "dashboard"
        if forms:
            return "form_page"
        if len([element for element in elements if element.href]) >= 10:
            return "navigation_page"
        return "generic_page"

    @staticmethod
    def _fingerprint(
        url: str,
        title: str,
        page_text: str,
        elements: List[ObservedElement],
    ) -> str:
        payload = {
            "url": url.split("#")[0],
            "title": title,
            "text": page_text[:2000],
            "elements": [
                {
                    "role": element.role,
                    "label": element.label,
                    "href": element.href,
                }
                for element in elements[:100]
            ],
        }
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


async def _observer_breadcrumbs(self: BrowserObserver, page: Page) -> List[str]:
        script = """
        () => {
            const selectors = [
                '[aria-label*="breadcrumb" i] a, [aria-label*="breadcrumb" i] span',
                '.breadcrumb a, .breadcrumb span, nav.breadcrumb a, nav.breadcrumb span',
                '[data-testid*="breadcrumb" i] a, [data-testid*="breadcrumb" i] span'
            ];
            const items = [];
            for (const selector of selectors) {
                document.querySelectorAll(selector).forEach(el => {
                    const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
                    if (text && !items.includes(text)) items.push(text);
                });
            }
            return items.slice(0, 12);
        }
        """
        try:
                return await page.evaluate(script)
        except Exception:
                return []


async def _observer_active_sidebar_item(self: BrowserObserver, page: Page) -> str:
        script = """
        () => {
            const selectors = [
                '[aria-current="page"]',
                '[aria-selected="true"]',
                '.sidebar .active',
                '.sidenav .active',
                '.menu .active',
                '.nav .active',
                '.active[role="link"]',
                '.active[role="menuitem"]'
            ];
            for (const selector of selectors) {
                const el = document.querySelector(selector);
                if (!el) continue;
                const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || el.getAttribute('title') || '').trim().replace(/\s+/g, ' ');
                if (text) return text;
            }
            return '';
        }
        """
        try:
                return " ".join((await page.evaluate(script)).split())
        except Exception:
                return ""


async def _observer_loading_indicators(self: BrowserObserver, page: Page) -> List[str]:
        script = """
        () => {
            const selectors = [
                '[aria-busy="true"]',
                '[role="progressbar"]',
                '.spinner', '.loading', '.loader', '.progress',
                '[data-loading="true"]',
                '[aria-live="polite"]'
            ];
            const results = [];
            selectors.forEach(selector => {
                document.querySelectorAll(selector).forEach(el => {
                    const text = (el.innerText || el.textContent || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ');
                    if (text && !results.includes(text)) results.push(text);
                });
            });
            return results.slice(0, 12);
        }
        """
        try:
                return await page.evaluate(script)
        except Exception:
                return []


async def _observer_visible_tables(self: BrowserObserver, page: Page) -> List[Dict]:
        script = """
        () => Array.from(document.querySelectorAll('table')).slice(0, 20).map((table, index) => {
            const rect = table.getBoundingClientRect();
            const style = window.getComputedStyle(table);
            return {
                index,
                visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                rows: table.querySelectorAll('tr').length,
                headers: Array.from(table.querySelectorAll('th')).map(el => (el.innerText || el.textContent || '').trim()).filter(Boolean).slice(0, 12),
                caption: (table.querySelector('caption')?.innerText || '').trim(),
                bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
            };
        })
        """
        try:
                return await page.evaluate(script)
        except Exception:
                return []


async def _observer_visible_cards(self: BrowserObserver, page: Page) -> List[Dict]:
        script = """
        () => Array.from(document.querySelectorAll('[class*="card" i], [data-card], [role="region"]')).slice(0, 25).map((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
            return {
                index,
                text: text.slice(0, 220),
                visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
            };
        })
        """
        try:
                return await page.evaluate(script)
        except Exception:
                return []


async def _observer_dashboard_widgets(self: BrowserObserver, page: Page) -> List[Dict]:
        script = """
        () => Array.from(document.querySelectorAll('[data-widget], [class*="widget" i], [class*="stat" i], [class*="metric" i]')).slice(0, 25).map((el, index) => {
            const rect = el.getBoundingClientRect();
            const style = window.getComputedStyle(el);
            const text = (el.innerText || el.textContent || '').trim().replace(/\s+/g, ' ');
            return {
                index,
                text: text.slice(0, 220),
                visible: rect.width > 0 && rect.height > 0 && style.display !== 'none' && style.visibility !== 'hidden',
                bbox: { x: rect.x, y: rect.y, width: rect.width, height: rect.height }
            };
        })
        """
        try:
                return await page.evaluate(script)
        except Exception:
                return []


BrowserObserver._breadcrumbs = _observer_breadcrumbs
BrowserObserver._active_sidebar_item = _observer_active_sidebar_item
BrowserObserver._loading_indicators = _observer_loading_indicators
BrowserObserver._visible_tables = _observer_visible_tables
BrowserObserver._visible_cards = _observer_visible_cards
BrowserObserver._dashboard_widgets = _observer_dashboard_widgets

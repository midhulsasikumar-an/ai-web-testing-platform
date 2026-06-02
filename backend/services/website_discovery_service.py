from __future__ import annotations

import os
from collections import deque
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright
from backend.services.asyncio_windows import ensure_windows_event_loop_policy


MAX_DISCOVERED_PAGES = int(os.getenv("DISCOVERY_MAX_PAGES", "24"))
MAX_LINKS_PER_PAGE = int(os.getenv("DISCOVERY_MAX_LINKS_PER_PAGE", "20"))

FEATURE_ALIASES: Dict[str, List[str]] = {
    "LOGIN": ["login", "sign in", "log in", "authenticate", "authentication"],
    "CHECKOUT": ["checkout", "payment", "purchase", "order"],
    "CART": ["cart", "basket", "shopping cart"],
    "SEARCH": ["search", "find", "lookup", "filter"],
    "INVENTORY": ["inventory", "products", "catalog", "listing"],
    "NAVIGATION": ["menu", "navigation", "sidebar", "breadcrumb", "nav"],
    "FORMS": ["form", "input", "submit", "sign up", "register"],
    "TABLES": ["table", "grid", "rows", "columns", "pagination"],
    "DASHBOARD": ["dashboard", "overview", "home"],
    "SETTINGS": ["settings", "preferences", "configuration"],
    "REPORTS": ["reports", "analytics", "insights", "summary"],
    "USER_MANAGEMENT": ["users", "user management", "roles", "permissions", "accounts"],
    "AUTHENTICATION": ["login", "sign in", "auth", "session"],
}


@dataclass
class PageDiscovery:
    url: str
    title: str
    page_type: str
    headings: List[str]
    forms: List[Dict[str, Any]]
    tables: List[Dict[str, Any]]
    buttons: List[Dict[str, Any]]
    links: List[Dict[str, Any]]


def _normalize_text(value: str) -> str:
    return " ".join((value or "").strip().lower().split())


def _feature_key_from_text(text: str) -> Optional[str]:
    normalized = _normalize_text(text)
    for feature_key, aliases in FEATURE_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            return feature_key
    return None


def _page_type_from_text(text: str) -> str:
    normalized = _normalize_text(text)
    if any(alias in normalized for alias in FEATURE_ALIASES["LOGIN"]):
        return "auth_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["DASHBOARD"]):
        return "dashboard_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["SETTINGS"]):
        return "settings_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["REPORTS"]):
        return "reports_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["USER_MANAGEMENT"]):
        return "user_management_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["CHECKOUT"]):
        return "checkout_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["CART"]):
        return "cart_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["SEARCH"]):
        return "search_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["TABLES"]):
        return "table_page"
    if any(alias in normalized for alias in FEATURE_ALIASES["FORMS"]):
        return "form_page"
    return "general_page"


def _collect_page_feature_map(page: PageDiscovery) -> List[Dict[str, Any]]:
    text_chunks = [page.title, *page.headings]
    for form in page.forms:
        text_chunks.extend([form.get("name") or "", form.get("action") or "", form.get("purpose") or ""])
    for table in page.tables:
        text_chunks.extend([table.get("title") or "", table.get("caption") or "", table.get("purpose") or ""])
    for button in page.buttons:
        text_chunks.extend([button.get("text") or "", button.get("aria_label") or ""])
    for link in page.links:
        text_chunks.extend([link.get("text") or "", link.get("href") or ""])

    feature_map: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()
    for text in text_chunks:
        feature_key = _feature_key_from_text(text)
        if not feature_key:
            continue
        label = feature_key.replace("_", " ").title()
        key = (feature_key, label)
        if key in seen:
            continue
        seen.add(key)
        feature_map.append(
            {
                "feature_key": feature_key,
                "feature_name": label,
                "evidence": text,
                "page_type": page.page_type,
                "url": page.url,
            }
        )
    return feature_map


def _collect_workflows(page: PageDiscovery) -> List[Dict[str, Any]]:
    workflows: List[Dict[str, Any]] = []
    title = _normalize_text(page.title)
    if any(alias in title for alias in FEATURE_ALIASES["LOGIN"]):
        workflows.append({"name": "Authentication Flow", "feature_key": "LOGIN", "entry_point": page.url})
    if any(alias in title for alias in FEATURE_ALIASES["CHECKOUT"]):
        workflows.append({"name": "Checkout Flow", "feature_key": "CHECKOUT", "entry_point": page.url})
    if any(alias in title for alias in FEATURE_ALIASES["DASHBOARD"]):
        workflows.append({"name": "Dashboard Navigation Flow", "feature_key": "DASHBOARD", "entry_point": page.url})
    if page.forms:
        workflows.append({"name": "Form Submission Flow", "feature_key": "FORMS", "entry_point": page.url})
    if page.tables:
        workflows.append({"name": "Table Exploration Flow", "feature_key": "TABLES", "entry_point": page.url})
    if page.links:
        workflows.append({"name": "Navigation Flow", "feature_key": "NAVIGATION", "entry_point": page.url})
    return workflows


async def _extract_page_snapshot(page) -> PageDiscovery:
    title = await page.title()

    headings = await page.locator("h1, h2, h3, h4, [role='heading']").evaluate_all(
        """
        elements => elements.slice(0, 20).map(el => (el.innerText || el.textContent || '').trim()).filter(Boolean)
        """
    )

    forms = await page.locator("form").evaluate_all(
        """
        elements => elements.slice(0, 12).map((el, index) => ({
            index,
            name: el.getAttribute('name') || el.id || `form-${index + 1}`,
            action: el.getAttribute('action') || '',
            method: (el.getAttribute('method') || '').toUpperCase(),
            fields: Array.from(el.querySelectorAll('input, textarea, select')).slice(0, 12).map((field, fieldIndex) => ({
                index: fieldIndex,
                name: field.getAttribute('name') || field.id || '',
                type: field.getAttribute('type') || field.tagName.toLowerCase(),
                placeholder: field.getAttribute('placeholder') || '',
                aria_label: field.getAttribute('aria-label') || '',
            })),
        }))
        """
    )

    tables = await page.locator("table").evaluate_all(
        """
        elements => elements.slice(0, 12).map((el, index) => ({
            index,
            title: el.getAttribute('aria-label') || el.id || `table-${index + 1}`,
            caption: el.querySelector('caption')?.innerText?.trim() || '',
            rows: Math.min(el.querySelectorAll('tr').length, 100),
            columns: Math.min(el.querySelectorAll('th, td').length, 100),
        }))
        """
    )

    buttons = await page.locator("button, input[type='submit'], input[type='button']").evaluate_all(
        """
        elements => elements.slice(0, 30).map((el, index) => ({
            index,
            text: (el.innerText || el.value || '').trim(),
            aria_label: el.getAttribute('aria-label') || '',
            id: el.id || '',
            type: el.getAttribute('type') || el.tagName.toLowerCase(),
        }))
        """
    )

    links = await page.locator("a").evaluate_all(
        """
        elements => elements.slice(0, 40).map((el, index) => ({
            index,
            text: (el.innerText || '').trim(),
            href: el.href || '',
        }))
        """
    )

    page_text = " ".join([title, *headings, *(item.get('text', '') for item in buttons), *(item.get('text', '') for item in links)])
    page_type = _page_type_from_text(page_text)

    return PageDiscovery(
        url=page.url,
        title=title,
        page_type=page_type,
        headings=[str(item) for item in headings if str(item).strip()],
        forms=[item for item in forms if isinstance(item, dict)],
        tables=[item for item in tables if isinstance(item, dict)],
        buttons=[item for item in buttons if isinstance(item, dict)],
        links=[item for item in links if isinstance(item, dict)],
    )


async def discover_website_features(url: str) -> Dict[str, Any]:
    ensure_windows_event_loop_policy()
    parsed = urlparse(url)
    origin = f"{parsed.scheme}://{parsed.netloc}"
    visited: Set[str] = set()
    discovered_pages: List[Dict[str, Any]] = []
    feature_map: List[Dict[str, Any]] = []
    workflows: List[Dict[str, Any]] = []
    forms: List[Dict[str, Any]] = []
    pages: List[Dict[str, Any]] = []
    queue: deque[str] = deque([url])

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        while queue and len(visited) < MAX_DISCOVERED_PAGES:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)

            try:
                await page.goto(current, wait_until="domcontentloaded", timeout=45000)
                snapshot = await _extract_page_snapshot(page)
            except Exception:
                continue

            page_feature_map = _collect_page_feature_map(snapshot)
            page_workflows = _collect_workflows(snapshot)
            feature_map.extend(page_feature_map)
            workflows.extend(page_workflows)

            forms.extend(
                [
                    {
                        "page_url": snapshot.url,
                        "page_title": snapshot.title,
                        "page_type": snapshot.page_type,
                        "form_index": form.get("index"),
                        "name": form.get("name"),
                        "action": form.get("action"),
                        "method": form.get("method"),
                        "fields": form.get("fields", []),
                    }
                    for form in snapshot.forms
                ]
            )

            pages.append(
                {
                    "url": snapshot.url,
                    "title": snapshot.title,
                    "page_type": snapshot.page_type,
                    "headings": snapshot.headings[:8],
                    "forms": len(snapshot.forms),
                    "tables": len(snapshot.tables),
                    "buttons": len(snapshot.buttons),
                    "links": len(snapshot.links),
                }
            )

            discovered_pages.append(
                {
                    "url": snapshot.url,
                    "title": snapshot.title,
                    "page_type": snapshot.page_type,
                    "feature_map": page_feature_map,
                    "workflows": page_workflows,
                    "forms": snapshot.forms,
                    "tables": snapshot.tables,
                }
            )

            for link in snapshot.links[:MAX_LINKS_PER_PAGE]:
                href = str(link.get("href") or "").strip()
                if not href:
                    continue
                absolute = urljoin(snapshot.url, href)
                absolute_parsed = urlparse(absolute)
                if absolute_parsed.scheme not in {"http", "https"}:
                    continue
                if f"{absolute_parsed.scheme}://{absolute_parsed.netloc}" != origin:
                    continue
                normalized = absolute.split("#", 1)[0]
                if normalized not in visited and normalized not in queue:
                    queue.append(normalized)

        await browser.close()

    deduped_feature_map: List[Dict[str, Any]] = []
    seen_features: Set[Tuple[str, str, str]] = set()
    for item in feature_map:
        key = (str(item.get("feature_key") or ""), str(item.get("feature_name") or ""), str(item.get("url") or ""))
        if key in seen_features:
            continue
        seen_features.add(key)
        deduped_feature_map.append(item)

    deduped_workflows: List[Dict[str, Any]] = []
    seen_workflows: Set[Tuple[str, str]] = set()
    for item in workflows:
        key = (str(item.get("name") or ""), str(item.get("entry_point") or ""))
        if key in seen_workflows:
            continue
        seen_workflows.add(key)
        deduped_workflows.append(item)

    return {
        "feature_map": deduped_feature_map,
        "workflows": deduped_workflows,
        "forms": forms,
        "pages": pages,
        "discovered_pages": discovered_pages,
        "root_url": url,
        "page_count": len(pages),
    }

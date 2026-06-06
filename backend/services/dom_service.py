from playwright.async_api import async_playwright
from typing import Dict, Any
from backend.services.asyncio_windows import ensure_windows_event_loop_policy


async def extract_page_elements(url: str) -> Dict[str, Any]:
    """Attempt to extract page elements using Playwright. If Playwright
    cannot be launched (e.g., environment restrictions), fall back to a
    lightweight HTML fetch using requests + BeautifulSoup.
    """
    ensure_windows_event_loop_policy()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded")

            title = await page.title()

            button_elements = await page.locator("button").evaluate_all(
                """
                elements => elements.map(el => ({
                    text: el.innerText?.trim() || "",
                    aria_label: el.getAttribute("aria-label") || "",
                    id: el.id || "",
                    class: el.className || "",
                    type: el.getAttribute("type") || "",
                    name: el.getAttribute("name") || "",
                    role: el.getAttribute("role") || "",
                    data_testid: el.getAttribute("data-testid") || ""
                }))
                """
            )

            input_elements = await page.locator("input").evaluate_all(
                """
                elements => elements.map(el => ({
                    name: el.name || "",
                    type: el.type || "",
                    placeholder: el.placeholder || "",
                    id: el.id || ""
                }))
                """
            )

            submit_buttons = await page.locator(
                "input[type='submit'], input[type='button']"
            ).evaluate_all(
                """
                elements => elements.map(el => ({
                    text: el.value || "",
                    aria_label: el.getAttribute("aria-label") || "",
                    id: el.id || "",
                    class: el.className || "",
                    type: el.type || "",
                    name: el.name || "",
                    role: el.getAttribute("role") || "",
                    data_testid: el.getAttribute("data-testid") || ""
                }))
                """
            )

            button_elements.extend(submit_buttons)

            headings = await page.locator("h1, h2, h3").all_inner_texts()

            links = await page.locator("a").evaluate_all(
                """
                elements => elements.slice(0, 20).map(el => ({
                    text: el.innerText?.trim() || "",
                    href: el.href || ""
                }))
                """
            )

            await browser.close()
            return {
                "title": title,
                "buttons": button_elements,
                "inputs": input_elements,
                "headings": headings,
                "links": links,
            }

    except Exception:
        # Playwright failed (common in restricted environments). Fall back
        # to simple HTML parsing using requests + BeautifulSoup so plan
        # generation can continue in dev environments.
        try:
            import requests
            from bs4 import BeautifulSoup

            resp = requests.get(url, timeout=15)
            soup = BeautifulSoup(resp.text, "html.parser")

            title = (soup.title.string or "") if soup.title else ""

            inputs = []
            for inp in soup.find_all("input")[:20]:
                inputs.append({
                    "name": inp.get("name") or "",
                    "type": inp.get("type") or "",
                    "placeholder": inp.get("placeholder") or "",
                    "id": inp.get("id") or "",
                })

            buttons = []
            for btn in soup.find_all("button")[:20]:
                buttons.append({
                    "text": (btn.get_text() or "").strip(),
                    "aria_label": btn.get("aria-label") or "",
                    "id": btn.get("id") or "",
                    "class": " ".join(btn.get("class") or []),
                    "type": btn.get("type") or "",
                    "name": btn.get("name") or "",
                })

            links = []
            for a in soup.find_all("a")[:20]:
                links.append({
                    "text": (a.get_text() or "").strip(),
                    "href": a.get("href") or "",
                })

            headings = [h.get_text().strip() for h in soup.find_all(["h1", "h2", "h3"])][:10]

            return {
                "title": title,
                "buttons": buttons,
                "inputs": inputs,
                "headings": headings,
                "links": links,
            }
        except Exception:
            # Last-resort fallback
            return {
                "title": "",
                "buttons": [],
                "inputs": [],
                "headings": [],
                "links": [],
            }
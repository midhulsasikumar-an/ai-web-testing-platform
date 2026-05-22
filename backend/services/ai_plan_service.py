from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from groq import Groq

from backend.ai.schema.test_plan_schema import Step, TestCase
from backend.services.dom_service import extract_page_elements

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


def _get_client() -> Groq | None:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


def _clean_json_text(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[1] if "\n" in stripped else stripped
        if stripped.endswith("```"):
            stripped = stripped[:-3]
    return stripped.strip()


def _safe_json_loads(text: str) -> Dict[str, Any] | None:
    try:
        return json.loads(_clean_json_text(text))
    except Exception:
        return None


def _fallback_plan(url: str, instruction: str, dom: Dict[str, Any]) -> Dict[str, Any]:
    title = str(dom.get("title") or "AI Generated Test")
    instruction_lower = instruction.lower()
    inputs = dom.get("inputs") or []
    buttons = dom.get("buttons") or []
    links = dom.get("links") or []

    steps: List[Dict[str, Any]] = []

    if any(keyword in instruction_lower for keyword in ["login", "sign in", "authenticate"]):
        if inputs:
            first_input = inputs[0]
            steps.append({
                "action": "fill",
                "target": first_input.get("placeholder") or first_input.get("name") or first_input.get("id") or "username field",
                "selector": first_input.get("id") and f"#{first_input.get('id')}" or None,
                "value": "test.user@example.com",
            })
        if len(inputs) > 1:
            second_input = inputs[1]
            steps.append({
                "action": "fill",
                "target": second_input.get("placeholder") or second_input.get("name") or second_input.get("id") or "password field",
                "selector": second_input.get("id") and f"#{second_input.get('id')}" or None,
                "value": "Password123!",
            })
        if buttons:
            primary_button = buttons[0]
            steps.append({
                "action": "click",
                "target": primary_button.get("text") or primary_button.get("aria_label") or "Submit",
                "selector": primary_button.get("id") and f"#{primary_button.get('id')}" or None,
            })
    elif any(keyword in instruction_lower for keyword in ["search", "find", "lookup"]):
        if inputs:
            first_input = inputs[0]
            steps.append({
                "action": "fill",
                "target": first_input.get("placeholder") or first_input.get("name") or first_input.get("id") or "search field",
                "selector": first_input.get("id") and f"#{first_input.get('id')}" or None,
                "value": "test query",
            })
            steps.append({
                "action": "press",
                "target": first_input.get("placeholder") or "search field",
                "value": "Enter",
            })
        elif buttons:
            primary_button = buttons[0]
            steps.append({
                "action": "click",
                "target": primary_button.get("text") or "Search",
                "selector": primary_button.get("id") and f"#{primary_button.get('id')}" or None,
            })
    else:
        if buttons:
            primary_button = buttons[0]
            steps.append({
                "action": "click",
                "target": primary_button.get("text") or primary_button.get("aria_label") or "Primary action",
                "selector": primary_button.get("id") and f"#{primary_button.get('id')}" or None,
            })
        if links:
            first_link = links[0]
            steps.append({
                "action": "click",
                "target": first_link.get("text") or first_link.get("href") or "First link",
                "selector": None,
            })

    if not steps:
        steps.append({
            "action": "click",
            "target": "Primary action",
        })

    return {
        "title": f"{title} - {instruction[:80]}".strip(" -"),
        "expected": "Page responds without errors and the requested interaction is completed.",
        "steps": steps,
    }


async def generate_test_plan(url: str, instruction: str, test_type: str | None = None) -> Dict[str, Any]:
    dom = await extract_page_elements(url)
    page_title = dom.get("title")

    prompt = (
        "You are an expert QA automation engineer.\n"
        "Generate ONE executable test case from the following page data and user instruction.\n"
        "Return valid JSON only with keys: title, expected, steps.\n"
        "Each step must include action, target, selector, value when relevant.\n\n"
        f"URL: {url}\n"
        f"Test Type: {test_type or 'AI Generated Test'}\n"
        f"Instruction: {instruction}\n"
        f"Page Title: {page_title}\n"
        f"DOM: {json.dumps(dom, ensure_ascii=False)[:8000]}\n"
        "\nJSON schema example:\n"
        '{"title":"","expected":"","steps":[{"action":"click","target":"","selector":"","value":""}]}'
    )

    client = _get_client()
    if client is not None:
        try:
            response = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=[
                    {
                        "role": "system",
                        "content": "You generate compact executable QA plans from structured UI data. Return JSON only.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
                max_tokens=800,
            )
            content = response.choices[0].message.content or ""
            parsed = _safe_json_loads(content)
            if parsed and isinstance(parsed.get("steps"), list) and parsed.get("title"):
                return {
                    "url": url,
                    "instruction": instruction,
                    "page_title": page_title,
                    "summary": f"AI generated plan for: {instruction}",
                    "source": "ai",
                    "test_case": parsed,
                    "test_cases": [parsed],
                    "raw_plan": parsed,
                }
        except Exception:
            pass

    fallback = _fallback_plan(url, instruction, dom)
    return {
        "url": url,
        "instruction": instruction,
        "page_title": page_title,
        "summary": f"Heuristic plan for: {instruction}",
        "source": "heuristic",
        "test_case": fallback,
        "test_cases": [fallback],
        "raw_plan": {"dom": dom},
    }


def build_executable_test_case(plan: Dict[str, Any]) -> TestCase:
    test_case = plan.get("test_case") or plan
    steps = [Step(**step) for step in test_case.get("steps", [])]
    return TestCase(
        title=test_case.get("title"),
        expected=test_case.get("expected"),
        steps=steps,
    )

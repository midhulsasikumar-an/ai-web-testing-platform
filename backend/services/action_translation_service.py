from __future__ import annotations

from typing import Any, Dict, List, Tuple

from backend.ai.schema.test_plan_schema import Step, TestCase


ACTION_TRANSLATION_TABLE: Dict[str, str] = {
    "verifytitle": "verify",
    "waitforelement": "wait",
    "sendkeys": "type",
    "fillfield": "type",
    "inputtext": "type",
    "takescreenshot": "screenshot",
    "pressbutton": "click",
    "tap": "click",
    "selectoption": "select",
    "hoverelement": "hover",
    "checkelementpresence": "wait",
    "checkelementenabled": "wait",
    "checkelementclickable": "wait",
    "capturescreenshot": "screenshot",
    "verifyelementpresent": "wait",
    "verifyattribute": "verify",
}

INPUT_ACTIONS = {"type", "enter", "fill", "input", "enter_text", "input_text"}


def _normalize_action(action: str) -> str:
    if not action:
        return ""
    key = action.strip().lower().replace("_", "")
    return ACTION_TRANSLATION_TABLE.get(key, action.strip().lower())


def _normalize_selector_and_value(normalized_action: str, selector: str | None, value: str | None) -> tuple[str | None, str | None]:
    selector_value = (selector or "").strip() or None
    step_value = (value or "").strip() or None

    # Some AI plans send selector type in `selector` and real locator in `value`.
    # Convert these into executor-ready selector strings.
    selector_tokens = {"xpath", "css", "text", "name", "id", "label", "placeholder"}
    if selector_value and selector_value.lower() in selector_tokens and step_value:
        selector_value = step_value
        if normalized_action in {"click", "wait", "hover", "select", "verify", "navigate", "screenshot"}:
            step_value = None

    if normalized_action in INPUT_ACTIONS and selector_value and not step_value:
        selector_lower = selector_value.lower()
        if any(keyword in selector_lower for keyword in ["username", "user name", "email", "password", "login", "sign in"]):
            # Preserve the selector phrase and allow the target to be treated as the value.
            step_value = None

    return selector_value, step_value


def translate_test_case(test_case: TestCase) -> Tuple[TestCase, List[Dict[str, Any]]]:
    translated_steps: List[Step] = []
    logs: List[Dict[str, Any]] = []

    for idx, step in enumerate(test_case.steps, start=1):
        original_action = step.action or ""
        normalized_action = _normalize_action(original_action)
        selector, value = _normalize_selector_and_value(normalized_action, step.selector, step.value)

        if normalized_action in INPUT_ACTIONS and selector and not value and step.target:
            target_lower = (step.target or "").lower().strip()
            selector_lower = selector.lower()
            if not any(keyword in target_lower for keyword in ["field", "input", "textbox", "button", "username", "password", "email"]):
                value = step.target
                if any(keyword in selector_lower for keyword in ["username", "email", "password", "field", "input"]):
                    pass
                else:
                    selector = selector

        translated_steps.append(
            Step(
                action=normalized_action,
                target=selector or step.target,
                selector=selector,
                value=value,
            )
        )

        logs.append(
            {
                "index": idx,
                "original_action": original_action,
                "normalized_action": normalized_action,
                "target": selector or step.target,
                "selector": selector,
                "value": value,
            }
        )

    translated = TestCase(
        title=test_case.title,
        expected=test_case.expected,
        steps=translated_steps,
    )
    return translated, logs

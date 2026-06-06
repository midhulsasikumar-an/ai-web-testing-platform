from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional

FAILURE_CATEGORIES = (
    "AUTHENTICATION",
    "NAVIGATION",
    "SELECTOR",
    "NETWORK",
    "CONSOLE",
    "TIMEOUT",
    "VALIDATION",
    "UNKNOWN",
)

FAILURE_CATEGORY_SUMMARY_PHRASES = {
    "AUTHENTICATION": "Authentication failures were the dominant issue.",
    "NAVIGATION": "Navigation failures were the dominant issue.",
    "SELECTOR": "Most failures were related to element selection.",
    "NETWORK": "Network failures were the dominant issue.",
    "CONSOLE": "Console failures were the dominant issue.",
    "TIMEOUT": "Timeout failures were the dominant issue.",
    "VALIDATION": "Validation failures were the dominant issue.",
    "UNKNOWN": "Failure causes could not be classified consistently.",
}

FAILURE_CATEGORY_INSIGHT_PHRASES = {
    "AUTHENTICATION": "Authentication failures indicate access issues.",
    "NAVIGATION": "Navigation failures indicate routing or redirect issues.",
    "SELECTOR": "Multiple selector failures suggest unstable locators.",
    "NETWORK": "Network-related failures were observed.",
    "CONSOLE": "Browser console errors may indicate frontend runtime issues.",
    "TIMEOUT": "Timeout failures suggest slow loading or unstable waits.",
    "VALIDATION": "Validation failures suggest assertion mismatches.",
    "UNKNOWN": "Some failures could not be classified with the available signals.",
}


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _to_text_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    text = str(values).strip()
    return [text] if text else []


def _step_value(step: Any, key: str) -> Any:
    return step.get(key) if isinstance(step, dict) else ""


def classify_failure_category(
    error_text: Any = "",
    *,
    console_errors: Optional[Iterable[Any]] = None,
    network_failures: Optional[Iterable[Any]] = None,
    step_text: Any = "",
    selector: Any = "",
    target: Any = "",
    test_name: Any = "",
    validation: Optional[Dict[str, Any]] = None,
) -> str:
    validation = validation or {}
    console_list = _to_text_list(console_errors if console_errors is not None else validation.get("console_errors"))
    network_list = _to_text_list(network_failures if network_failures is not None else validation.get("network_failures"))

    combined = " ".join(
        part
        for part in [
            _normalize_text(error_text),
            _normalize_text(step_text),
            _normalize_text(selector),
            _normalize_text(target),
            _normalize_text(test_name),
            _normalize_text(validation.get("title")),
            _normalize_text(validation.get("url")),
            _normalize_text(validation.get("expected_matched")),
            _normalize_text(validation.get("error_detected")),
        ]
        if part
    )

    if any(keyword in combined for keyword in ["login failed", "invalid credential", "invalid password", "unauthorized", "authentication", "auth failure", "session expired", "sign in", "sign-in"]):
        return "AUTHENTICATION"

    if network_list or any(keyword in combined for keyword in ["network", "request failed", "fetch failed", "connection refused", "econnreset", "econnrefused", "http 5", "status 5", "failed to load resource"]):
        return "NETWORK"

    if console_list or any(keyword in combined for keyword in ["console", "uncaught", "typeerror", "referenceerror", "syntaxerror", "script error", "javascript error"]):
        return "CONSOLE"

    if any(keyword in combined for keyword in ["timeout", "timed out", "exceeded time", "wait_for timeout", "waiting for"]):
        return "TIMEOUT"

    if any(keyword in combined for keyword in ["selector not found", "locator", "element not found", "no such element", "unable to find", "could not find", "target selector", "missing element"]):
        return "SELECTOR"

    if any(keyword in combined for keyword in ["navigation", "redirect", "route", "url did not change", "page load", "outside allowed domain", "goto"]):
        return "NAVIGATION"

    if any(keyword in combined for keyword in ["assert", "assertion", "expected result did not match", "expected matched", "expected", "mismatch", "validation", "verify", "check failed"]):
        return "VALIDATION"

    return "UNKNOWN"


def collect_failure_category_counts(results: Iterable[Dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for result in results or []:
        if not isinstance(result, dict):
            continue
        status = str(result.get("status") or "").lower()
        if status not in {"fail", "failed"}:
            continue

        validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
        step = result.get("step")
        failure_category = str(result.get("failure_category") or "").strip().upper()
        if failure_category not in FAILURE_CATEGORIES:
            failure_category = classify_failure_category(
                error_text=result.get("error") or result.get("details") or "",
                console_errors=validation.get("console_errors"),
                network_failures=validation.get("network_failures"),
                step_text=result.get("test") or _step_value(step, "action") or "",
                selector=result.get("selector_used") or _step_value(step, "selector") or "",
                target=_step_value(step, "target") or "",
                test_name=result.get("test") or "",
                validation=validation,
            )

        counts[failure_category] += 1

    return counts


def format_failure_category_summary(category: str) -> str:
    return FAILURE_CATEGORY_SUMMARY_PHRASES.get(str(category or "").upper(), FAILURE_CATEGORY_SUMMARY_PHRASES["UNKNOWN"])


def format_failure_category_insight(category: str, count: int) -> str:
    category = str(category or "").upper()
    phrase = FAILURE_CATEGORY_INSIGHT_PHRASES.get(category, FAILURE_CATEGORY_INSIGHT_PHRASES["UNKNOWN"])
    if category == "SELECTOR" and count > 1:
        return phrase
    if category == "SELECTOR":
        return "Selector failures suggest unstable locators."
    if category == "AUTHENTICATION" and count > 1:
        return "Multiple authentication failures indicate access issues."
    if category == "NETWORK" and count > 1:
        return "Network-related failures were observed repeatedly."
    return phrase

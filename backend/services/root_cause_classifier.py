from __future__ import annotations

from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


ROOT_CAUSES = (
    "SELECTOR_CHANGED",
    "ELEMENT_NOT_VISIBLE",
    "ELEMENT_NOT_FOUND",
    "NAVIGATION_REDIRECT",
    "NETWORK_FAILURE",
    "API_FAILURE",
    "AUTHENTICATION_FAILURE",
    "TIMEOUT",
    "PAGE_CRASH",
    "JAVASCRIPT_ERROR",
    "UNKNOWN",
)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def _to_text_list(values: Any) -> List[str]:
    if not values:
        return []
    if isinstance(values, list):
        return [str(item).strip() for item in values if str(item).strip()]
    text = str(values).strip()
    return [text] if text else []


def _contains_any(haystack: str, keywords: Iterable[str]) -> bool:
    return any(keyword in haystack for keyword in keywords)


def classify_root_cause(
    action: Any = "",
    category: Any = "",
    error: Any = "",
    console_errors: Optional[Iterable[Any]] = None,
    network_failures: Optional[Iterable[Any]] = None,
    selector_used: Any = "",
    validation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    validation = validation or {}
    console_list = _to_text_list(console_errors if console_errors is not None else validation.get("console_errors"))
    network_list = _to_text_list(network_failures if network_failures is not None else validation.get("network_failures"))

    combined = " ".join(
        part
        for part in [
            _normalize_text(action),
            _normalize_text(category),
            _normalize_text(error),
            _normalize_text(selector_used),
            _normalize_text(validation.get("message")),
            _normalize_text(validation.get("details")),
            _normalize_text(validation.get("title")),
            _normalize_text(validation.get("url")),
            _normalize_text(validation.get("expected_matched")),
            _normalize_text(validation.get("error_detected")),
        ]
        if part
    )

    if network_list:
        return {"root_cause": "NETWORK_FAILURE", "confidence": 0.98}

    if _contains_any(combined, ["api failure", "api request", "graphql", "endpoint", "response 4", "response 5", "status 4", "status 5", "server error", "internal server error"]):
        return {"root_cause": "API_FAILURE", "confidence": 0.93}

    if _contains_any(combined, ["login failed", "log in", "login", "sign in", "sign-in", "unauthorized", "forbidden", "authentication", "auth failure", "session expired", "credential", "password"]):
        return {"root_cause": "AUTHENTICATION_FAILURE", "confidence": 0.95}

    if _contains_any(combined, ["timeout", "timed out", "exceeded time", "wait for", "waiting for", "etimedout"]):
        return {"root_cause": "TIMEOUT", "confidence": 0.95}

    if _contains_any(combined, ["page crashed", "page crash", "browser closed", "target closed", "crash", "renderer", "tab crashed"]):
        return {"root_cause": "PAGE_CRASH", "confidence": 0.94}

    if console_list or _contains_any(combined, ["referenceerror", "typeerror", "syntaxerror", "javascript error", "uncaught", "cannot read property", "cannot read properties", "is not defined"]):
        return {"root_cause": "JAVASCRIPT_ERROR", "confidence": 0.94}

    if _contains_any(combined, ["element not found", "no such element", "unable to find", "could not find", "selector not found", "locator not found", "missing element", "wait for selector", "strict mode violation"]):
        return {"root_cause": "ELEMENT_NOT_FOUND", "confidence": 0.92}

    if selector_used and _contains_any(combined, ["detached", "stale element", "selector changed", "locator changed", "could not resolve selector", "strict mode violation"]):
        return {"root_cause": "SELECTOR_CHANGED", "confidence": 0.9}

    if _contains_any(combined, ["not visible", "element is not visible", "hidden", "obscured", "covered", "intercepted", "not interactable", "not clickable"]):
        return {"root_cause": "ELEMENT_NOT_VISIBLE", "confidence": 0.9}

    if validation.get("url_changed") or _contains_any(combined, ["redirect", "navigation", "route change", "unexpected url", "url changed", "page load", "goto"]):
        return {"root_cause": "NAVIGATION_REDIRECT", "confidence": 0.88}

    if _contains_any(combined, ["api", "/api", "http 4", "http 5", "status 4", "status 5", "fetch failed", "request failed", "failed to load resource", "connection refused", "econnreset", "econnrefused"]):
        return {"root_cause": "NETWORK_FAILURE", "confidence": 0.9}

    return {"root_cause": "UNKNOWN", "confidence": 0.35}


def collect_root_cause_counts(results: Iterable[Dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for result in results or []:
        if not isinstance(result, dict):
            continue
        status = str(result.get("status") or "").lower()
        if status not in {"fail", "failed"}:
            continue

        validation = result.get("validation") if isinstance(result.get("validation"), dict) else {}
        root_cause = str(result.get("root_cause") or "").strip().upper()
        if root_cause not in ROOT_CAUSES:
            classified = classify_root_cause(
                action=result.get("test") or result.get("step", {}).get("action") or "",
                category=result.get("failure_category") or "",
                error=result.get("error") or result.get("details") or "",
                console_errors=validation.get("console_errors"),
                network_failures=validation.get("network_failures"),
                selector_used=result.get("selector_used") or result.get("step", {}).get("selector") or "",
                validation=validation,
            )
            root_cause = str(classified["root_cause"]).upper()

        counts[root_cause] += 1

    return counts


def summarize_root_causes(results: Iterable[Dict[str, Any]], limit: int = 5) -> Dict[str, Any]:
    counts = collect_root_cause_counts(results)
    total = sum(counts.values())
    top_items = [
        {
            "root_cause": root_cause,
            "count": count,
            "percentage": round((count / total) * 100, 1) if total else 0.0,
        }
        for root_cause, count in counts.most_common(max(0, int(limit or 0)))
    ]
    return {
        "summary": dict(counts),
        "top_items": top_items,
        "total": total,
    }
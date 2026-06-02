from __future__ import annotations

import re
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.database.mongo import ai_memory_collection, bug_collection, collection as test_runs_collection
from backend.database.report_repository import get_report, list_reports_for_user
from backend.services.run_comparison_service import compare_runs


_SEVERITY_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0, "unknown": -1}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _parse_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str) and value.strip():
        text = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(text)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _sort_key(doc: Dict[str, Any]) -> datetime:
    for key in ("created_at", "updated_at", "generated_date", "timestamp"):
        parsed = _parse_datetime(doc.get(key))
        if parsed:
            return parsed
    return datetime.min.replace(tzinfo=timezone.utc)


def _sort_docs(docs: List[Dict[str, Any]], *, reverse: bool = False) -> List[Dict[str, Any]]:
    return sorted(docs, key=_sort_key, reverse=reverse)


def _text_match(doc: Dict[str, Any], query: str, fields: Tuple[str, ...]) -> bool:
    if not query:
        return True
    haystack = " ".join(_clean(doc.get(field)).lower() for field in fields)
    lowered = query.lower().strip()
    return all(token in haystack for token in lowered.split() if token)


def _run_docs(user_id: str) -> List[Dict[str, Any]]:
    return _sort_docs(list(test_runs_collection.find({"user_id": user_id}, {"_id": 0})))


def _report_docs(user_id: str) -> List[Dict[str, Any]]:
    return _sort_docs(list_reports_for_user(user_id))


def _bug_docs(user_id: str) -> List[Dict[str, Any]]:
    return _sort_docs(list(bug_collection.find({"user_id": user_id}, {"_id": 0})))


def _memory_docs(user_id: str) -> List[Dict[str, Any]]:
    return _sort_docs(list(ai_memory_collection.find({"user_id": user_id}, {"_id": 0})))


def _run_label(doc: Dict[str, Any]) -> str:
    return _clean(doc.get("test_name") or doc.get("project") or doc.get("goal") or doc.get("title") or doc.get("test_id") or doc.get("execution_id") or doc.get("report_id") or "Untitled run")


def _bug_label(doc: Dict[str, Any]) -> str:
    return _clean(doc.get("bug_name") or doc.get("title") or doc.get("description") or doc.get("bug_description") or doc.get("bug_id") or "Untitled bug")


def _report_label(doc: Dict[str, Any]) -> str:
    return _clean(doc.get("title") or doc.get("test_name") or doc.get("report_label") or doc.get("report_id") or "Untitled report")


def _collect_screenshots(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    screenshots: List[Dict[str, Any]] = []
    sources = [
        doc.get("screenshot_paths"),
        doc.get("screenshots"),
        doc.get("ai_report", {}).get("screenshots") if isinstance(doc.get("ai_report"), dict) else None,
        doc.get("report_sections", {}).get("screenshots") if isinstance(doc.get("report_sections"), dict) else None,
    ]
    for source in sources:
        if not isinstance(source, list):
            continue
        for index, item in enumerate(source):
            if isinstance(item, dict):
                path = _clean(item.get("artifact_url") or item.get("screenshot_path") or item.get("path") or item.get("url"))
                if not path:
                    continue
                screenshots.append({"path": path, "label": _clean(item.get("label") or item.get("workflow_stage") or item.get("stage") or f"screenshot {index + 1}"), "stage": _clean(item.get("workflow_stage") or item.get("stage") or item.get("label") or "unknown")})
            elif isinstance(item, str) and item.strip():
                screenshots.append({"path": item.strip(), "label": f"screenshot {index + 1}", "stage": "unknown"})
    unique: List[Dict[str, Any]] = []
    seen = set()
    for shot in screenshots:
        path = shot.get("path")
        if path in seen:
            continue
        seen.add(path)
        unique.append(shot)
    return unique


def _run_bug_count(run: Dict[str, Any], bugs: List[Dict[str, Any]]) -> int:
    candidates = {_clean(run.get("test_id")), _clean(run.get("execution_id")), _clean(run.get("run_id")), _clean(run.get("report_id")), _clean(run.get("related_test_id"))}
    count = 0
    for bug in bugs:
        bug_candidates = {_clean(bug.get("test_id")), _clean(bug.get("execution_id")), _clean(bug.get("run_id")), _clean(bug.get("related_test_id")), _clean(bug.get("report_id"))}
        if candidates.intersection(bug_candidates):
            count += 1
    return count


def _run_failure_count(run: Dict[str, Any]) -> int:
    summary = run.get("execution_summary") if isinstance(run.get("execution_summary"), dict) else {}
    ai_report = run.get("ai_report") if isinstance(run.get("ai_report"), dict) else {}
    for value in [summary.get("failed_steps"), summary.get("failures"), summary.get("failed"), ai_report.get("failed_steps"), ai_report.get("bug_count")]:
        if isinstance(value, int):
            return max(0, value)
        if isinstance(value, list):
            return len(value)
    status = _clean(run.get("status")).lower()
    return 1 if status in {"failed", "fail", "error", "timed_out"} else 0


def _run_health_score(run: Dict[str, Any]) -> float:
    for key in ("website_health_score", "health_score", "score", "success_score", "coverage_score"):
        value = run.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    summary = run.get("execution_summary") if isinstance(run.get("execution_summary"), dict) else {}
    value = summary.get("success_rate")
    return float(value) if isinstance(value, (int, float)) else 0.0


def _run_failure_tags(run: Dict[str, Any], bugs: List[Dict[str, Any]]) -> List[str]:
    text = " ".join(_clean(run.get(field)).lower() for field in ("goal", "test_name", "project", "summary", "status", "url"))
    for bug in bugs:
        if _run_bug_count(run, [bug]):
            text += " " + " ".join(_clean(bug.get(field)).lower() for field in ("bug_name", "bug_description", "description", "failure_category", "root_cause", "severity", "status"))
    tags = []
    if any(word in text for word in ("auth", "login", "signin", "password", "credential")):
        tags.append("authentication")
    if any(word in text for word in ("api", "network", "fetch", "request", "response", "timeout")):
        tags.append("api")
    if any(word in text for word in ("flaky", "intermittent", "unstable")):
        tags.append("flaky")
    if any(word in text for word in ("critical", "high", "failure")):
        tags.append("failure")
    return sorted(set(tags))


def _resolve_by_ordinals(items: List[Dict[str, Any]], ordinal: int) -> Optional[Dict[str, Any]]:
    if ordinal < 1 or ordinal > len(items):
        return None
    return items[ordinal - 1]


def _entity_summary(kind: str, selected: Optional[Dict[str, Any]], index: Optional[int], total: int) -> str:
    if not selected:
        return f"No matching {kind} was found."
    label = {"run": _run_label, "bug": _bug_label, "screenshot": lambda item: _clean(item.get("path") or item.get("label") or "screenshot"), "report": _report_label, "memory": lambda item: _clean(item.get("content") or "memory item")}.get(kind, lambda item: _clean(item.get("content") or item.get("title") or kind))(selected)
    created_at = _sort_key(selected).isoformat()
    ordinal = f"#{index}" if index is not None else "selected"
    return f"Resolved {kind} {ordinal} of {total}: {label} ({created_at})."


def _extract_ordinal(query: str, label: str) -> Optional[int]:
    match = re.search(rf"{label}\s*#?\s*(\d+)", query, flags=re.IGNORECASE)
    if match:
        return int(match.group(1))
    match = re.search(r"#\s*(\d+)", query)
    return int(match.group(1)) if match and label in query.lower() else None


def _find_run_identifier(run_doc: Dict[str, Any]) -> Optional[str]:
    for key in ("report_id", "test_id", "execution_id", "run_id", "related_test_id"):
        value = _clean(run_doc.get(key))
        if value:
            return value
    return None


def _find_report_for_run(user_id: str, run_doc: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    for identifier in (run_doc.get("report_id"), run_doc.get("test_id"), run_doc.get("execution_id"), run_doc.get("run_id"), run_doc.get("related_test_id")):
        if identifier:
            report = get_report(str(identifier), user_id=user_id)
            if report:
                return report
    return None


def _resolve_run(user_id: str, query: str) -> Dict[str, Any]:
    runs = _run_docs(user_id)
    lower = query.lower().strip()
    selected: Optional[Dict[str, Any]] = None
    index: Optional[int] = None
    if not runs:
        return {"kind": "run", "items": [], "selected": None, "summary": "No runs available."}
    if any(text in lower for text in ("latest run", "most recent run", "last run")):
        selected = runs[-1]
        index = len(runs)
    elif "previous run" in lower:
        selected = runs[-2] if len(runs) >= 2 else runs[-1]
        index = len(runs) - 1 if len(runs) >= 2 else len(runs)
    elif any(text in lower for text in ("first run", "oldest run", "earliest run")):
        selected = runs[0]
        index = 1
    else:
        ordinal = _extract_ordinal(lower, "run")
        if ordinal:
            selected = _resolve_by_ordinals(runs, ordinal)
            index = ordinal if selected else None
    if not selected:
        for run in runs:
            if _text_match(run, query, ("test_name", "goal", "project", "url", "status", "test_type", "execution_id", "test_id", "report_id")):
                selected = run
                index = runs.index(run) + 1
                break
    if not selected:
        selected = runs[-1]
        index = len(runs)
    selected = dict(selected)
    selected["bug_count"] = _run_bug_count(selected, _bug_docs(user_id))
    selected["failure_count"] = _run_failure_count(selected)
    selected["health_score"] = _run_health_score(selected)
    selected["screenshots"] = _collect_screenshots(selected)
    return {"kind": "run", "items": runs, "selected": selected, "selected_index": index, "summary": _entity_summary("run", selected, index, len(runs))}


def _resolve_bug(user_id: str, query: str) -> Dict[str, Any]:
    bugs = _bug_docs(user_id)
    lower = query.lower().strip()
    selected: Optional[Dict[str, Any]] = None
    index: Optional[int] = None
    if not bugs:
        return {"kind": "bug", "items": [], "selected": None, "summary": "No bugs available."}
    if any(text in lower for text in ("latest bug", "most recent bug", "last bug")):
        selected = bugs[-1]
        index = len(bugs)
    elif any(text in lower for text in ("critical bug", "highest severity bug")):
        selected = sorted(bugs, key=lambda item: (_SEVERITY_ORDER.get(_clean(item.get("severity")).lower(), -1), _sort_key(item)), reverse=True)[0]
        index = bugs.index(selected) + 1
    else:
        ordinal = _extract_ordinal(lower, "bug")
        if ordinal:
            selected = _resolve_by_ordinals(bugs, ordinal)
            index = ordinal if selected else None
    if not selected:
        for bug in bugs:
            if _text_match(bug, query, ("bug_name", "title", "bug_description", "description", "status", "severity", "failure_category", "root_cause")):
                selected = bug
                index = bugs.index(bug) + 1
                break
    if not selected:
        selected = bugs[-1]
        index = len(bugs)
    selected = dict(selected)
    selected["severity_rank"] = _SEVERITY_ORDER.get(_clean(selected.get("severity")).lower(), -1)
    return {"kind": "bug", "items": bugs, "selected": selected, "selected_index": index, "summary": _entity_summary("bug", selected, index, len(bugs))}


def _resolve_screenshot(user_id: str, query: str, *, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> Dict[str, Any]:
    runs = _run_docs(user_id)
    all_screenshots: List[Dict[str, Any]] = []

    def add_screenshots(source: Dict[str, Any], owner: Dict[str, Any]) -> None:
        for screenshot in _collect_screenshots(source):
            item = dict(screenshot)
            item["run_id"] = _clean(owner.get("test_id") or owner.get("execution_id") or owner.get("run_id") or owner.get("report_id"))
            item["report_id"] = _clean(owner.get("report_id") or owner.get("test_run_id") or owner.get("run_id") or owner.get("test_id"))
            item["created_at"] = _sort_key(owner).isoformat()
            all_screenshots.append(item)

    for run in runs:
        report = _find_report_for_run(user_id, run)
        if report:
            add_screenshots(report, run)
        else:
            add_screenshots(run, run)

    if report_id:
        report = get_report(report_id, user_id=user_id)
        if report:
            all_screenshots = []
            add_screenshots(report, report)
    elif test_run_id:
        report = get_report(test_run_id, user_id=user_id)
        if report:
            all_screenshots = []
            add_screenshots(report, report)

    if not all_screenshots:
        return {"kind": "screenshot", "items": [], "selected": None, "summary": "No screenshots available."}
    lower = query.lower().strip()
    selected: Optional[Dict[str, Any]] = None
    index: Optional[int] = None
    if any(text in lower for text in ("latest screenshot", "most recent screenshot", "last screenshot")):
        selected = all_screenshots[-1]
        index = len(all_screenshots)
    else:
        ordinal = _extract_ordinal(lower, "screenshot")
        if ordinal:
            selected = _resolve_by_ordinals(all_screenshots, ordinal)
            index = ordinal if selected else None
    if not selected:
        for screenshot in all_screenshots:
            if _text_match(screenshot, query, ("path", "label", "stage", "run_id", "report_id")):
                selected = screenshot
                index = all_screenshots.index(screenshot) + 1
                break
    if not selected:
        selected = all_screenshots[-1]
        index = len(all_screenshots)
    return {"kind": "screenshot", "items": all_screenshots, "selected": selected, "selected_index": index, "summary": _entity_summary("screenshot", selected, index, len(all_screenshots))}


def _resolve_compare(user_id: str, query: str) -> Dict[str, Any]:
    lower = query.lower().strip()
    pair = re.search(r"compare\s+(.+?)\s+(?:and|with|against)\s+(.+)$", lower)
    if pair:
        left_ref, right_ref = pair.group(1).strip(), pair.group(2).strip()
    else:
        left_ref, right_ref = "latest run", "previous run"
    baseline = _resolve_run(user_id, left_ref)
    comparison = _resolve_run(user_id, right_ref)
    baseline_doc = baseline.get("selected") or {}
    comparison_doc = comparison.get("selected") or {}
    baseline_identifier = _find_run_identifier(baseline_doc)
    comparison_identifier = _find_run_identifier(comparison_doc)
    if not baseline_identifier or not comparison_identifier:
        return {"kind": "compare", "summary": "Unable to resolve both runs for comparison.", "baseline": baseline, "comparison": comparison, "comparison_result": None}
    comparison_result = compare_runs(baseline_identifier, comparison_identifier, user_id=user_id, persist=False)
    return {"kind": "compare", "summary": comparison_result.get("summary", "Run comparison complete."), "baseline": baseline, "comparison": comparison, "comparison_result": comparison_result}


def _summarize_run_choice(run: Optional[Dict[str, Any]], bugs: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not run:
        return {}
    return {"run_id": _find_run_identifier(run), "label": _run_label(run), "status": _clean(run.get("status") or "unknown"), "created_at": _sort_key(run).isoformat(), "bug_count": _run_bug_count(run, bugs), "failure_count": _run_failure_count(run), "health_score": _run_health_score(run), "tags": _run_failure_tags(run, bugs)}


def _history_summary_text(trend_points: List[Dict[str, Any]], most_bugs: Optional[Dict[str, Any]], most_failures: Optional[Dict[str, Any]], auth_run: Optional[Dict[str, Any]], api_run: Optional[Dict[str, Any]], best_run: Optional[Dict[str, Any]], worst_run: Optional[Dict[str, Any]]) -> str:
    parts = []
    if trend_points:
        parts.append(f"Summarized {len(trend_points)} recent run(s).")
    if most_bugs:
        parts.append(f"Most bugs: {_run_label(most_bugs)}.")
    if most_failures:
        parts.append(f"Most failures: {_run_label(most_failures)}.")
    if auth_run:
        parts.append(f"Authentication issues were strongest in {_run_label(auth_run)}.")
    if api_run:
        parts.append(f"API failures were strongest in {_run_label(api_run)}.")
    if best_run:
        parts.append(f"Best run: {_run_label(best_run)}.")
    if worst_run:
        parts.append(f"Worst run: {_run_label(worst_run)}.")
    return " ".join(parts) if parts else "No recent run trends were found."


def _summarize_history(user_id: str, limit: int = 10) -> Dict[str, Any]:
    runs = _run_docs(user_id)
    reports = _report_docs(user_id)
    bugs = _bug_docs(user_id)
    recent_runs = runs[-limit:]
    auth_counts = Counter()
    api_counts = Counter()
    for run in recent_runs:
        tags = _run_failure_tags(run, bugs)
        run_identifier = _find_run_identifier(run) or _clean(run.get("report_id") or run.get("test_id") or run.get("execution_id") or run.get("run_id"))
        if "authentication" in tags:
            auth_counts[run_identifier] += 1
        if "api" in tags:
            api_counts[run_identifier] += 1
    most_bugs = max(recent_runs, key=lambda run: _run_bug_count(run, bugs), default=None) if recent_runs else None
    most_failures = max(recent_runs, key=lambda run: _run_failure_count(run), default=None) if recent_runs else None
    auth_run = max(recent_runs, key=lambda run: auth_counts.get(_find_run_identifier(run) or "", 0), default=None) if recent_runs else None
    api_run = max(recent_runs, key=lambda run: api_counts.get(_find_run_identifier(run) or "", 0), default=None) if recent_runs else None
    best_run = max(recent_runs, key=lambda run: (_run_health_score(run), -_run_bug_count(run, bugs), -_run_failure_count(run)), default=None) if recent_runs else None
    worst_run = min(recent_runs, key=lambda run: (_run_health_score(run), _run_bug_count(run, bugs), _run_failure_count(run)), default=None) if recent_runs else None
    trend_points = [{"label": _run_label(run), "created_at": _sort_key(run).isoformat(), "health_score": _run_health_score(run), "bug_count": _run_bug_count(run, bugs), "failure_count": _run_failure_count(run)} for run in recent_runs]
    return {"kind": "analytics", "total_runs": len(runs), "total_reports": len(reports), "total_bugs": len(bugs), "recent_runs": trend_points, "most_bugs_run": _summarize_run_choice(most_bugs, bugs) if most_bugs else None, "most_failures_run": _summarize_run_choice(most_failures, bugs) if most_failures else None, "authentication_run": _summarize_run_choice(auth_run, bugs) if auth_run else None, "api_failures_run": _summarize_run_choice(api_run, bugs) if api_run else None, "best_run": _summarize_run_choice(best_run, bugs) if best_run else None, "worst_run": _summarize_run_choice(worst_run, bugs) if worst_run else None, "quality_trend": trend_points, "bug_trend": [{"label": point["label"], "bug_count": point["bug_count"], "created_at": point["created_at"]} for point in trend_points], "regression_trend": [{"label": point["label"], "failure_count": point["failure_count"], "created_at": point["created_at"]} for point in trend_points], "severity_counts": dict(Counter(_clean(bug.get("severity")).lower() or "unknown" for bug in bugs)), "summary": _history_summary_text(trend_points, most_bugs, most_failures, auth_run, api_run, best_run, worst_run)}


# ---------------------------------------------------------------------------
# Token sets used to detect instruction-generation intent at routing time.
# These mirror AIWorkspaceService._ACTION_TOKENS / _ARTIFACT_TOKENS so that
# resolve_entity_query can guard the greedy "test" branch without importing
# the service (which would create a circular dependency).
# ---------------------------------------------------------------------------

_ROUTE_ACTION_TOKENS: frozenset = frozenset([
    "generate", "create", "write", "build", "make", "draft",
    "give", "produce", "compose",
])
_ROUTE_ARTIFACT_TOKENS: frozenset = frozenset([
    "instruction", "instructions", "plan", "plans",
    "scenario", "scenarios", "prompt", "prompts",
    "template", "objective", "objectives",
])
_ROUTE_LEGACY_PHRASES = (
    "generate instruction",
    "generate instructions",
    "create instruction",
    "test objective",
)


def _is_instruction_intent(lowered: str) -> bool:
    """Return True if the query is clearly an instruction-generation request.

    Called inside resolve_entity_query so that instruction queries never
    fall into the greedy 'test' -> test_run_analysis branch.
    """
    if any(phrase in lowered for phrase in _ROUTE_LEGACY_PHRASES):
        return True
    tokens = set(re.split(r"[\s\-_/]+", lowered))
    return bool(tokens & _ROUTE_ACTION_TOKENS) and bool(tokens & _ROUTE_ARTIFACT_TOKENS)


def resolve_entity_query(user_id: str, query: str, *, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> Dict[str, Any]:
    lowered = query.lower().strip()
    if not lowered:
        return {"intent": "general_chat", "data": [], "summary": "", "details": {}}

    # Instruction-generation intent ALWAYS wins before any greedy keyword match.
    if _is_instruction_intent(lowered):
        return {"intent": "general_chat", "data": [], "summary": "", "details": {}}

    if "compare" in lowered:
        comparison = _resolve_compare(user_id, query)
        return {"intent": "compare_runs", "data": [comparison], "summary": comparison.get("summary", ""), "details": comparison}
    if any(phrase in lowered for phrase in ("which run had most bugs", "which run failed most", "show regression trend", "show quality trend", "show bug trend", "summarize last 10 runs", "authentication issues", "api failures")):
        analytics = _summarize_history(user_id)
        return {"intent": "historical_analytics", "data": [analytics], "summary": analytics.get("summary", ""), "details": analytics}
    if "bug" in lowered:
        bug = _resolve_bug(user_id, query)
        return {"intent": "query_bugs", "data": [bug.get("selected")] if bug.get("selected") else [], "summary": bug.get("summary", ""), "details": bug}
    if "screenshot" in lowered or "image" in lowered or "visual" in lowered:
        screenshot = _resolve_screenshot(user_id, query, report_id=report_id, test_run_id=test_run_id)
        selected = screenshot.get("selected")
        return {"intent": "screenshot_analysis", "data": selected if isinstance(selected, list) else ([selected] if selected else []), "summary": screenshot.get("summary", ""), "details": screenshot}
    if any(phrase in lowered for phrase in ("report", "run", "test")):
        run = _resolve_run(user_id, query)
        selected = dict(run.get("selected") or {})
        if selected:
            report = _find_report_for_run(user_id, selected)
            if report:
                selected["report"] = report
        return {"intent": "test_run_analysis", "data": [selected] if selected else [], "summary": run.get("summary", ""), "details": run}
    if "memory" in lowered:
        memories = _memory_docs(user_id)
        return {"intent": "memory", "data": memories, "summary": f"Retrieved {len(memories)} memory item(s).", "details": {"count": len(memories)}}
    reports = _report_docs(user_id)
    if reports:
        return {"intent": "query_reports", "data": reports[-5:], "summary": f"Retrieved {min(5, len(reports))} report(s).", "details": {"count": len(reports)}}
    return {"intent": "general_chat", "data": [], "summary": "", "details": {}}


def resolve_memory_action(user_id: str, query: str) -> Dict[str, Any]:
    lowered = query.lower().strip()
    if lowered.startswith(("show my memories", "list memories", "show memories", "my memories")):
        memories = _memory_docs(user_id)
        return {"action": "list", "items": memories, "summary": f"Retrieved {len(memories)} memory item(s)."}
    delete_prefixes = ["forget ", "forget that ", "delete memory ", "delete ", "remove preference ", "remove memory ", "remove "]
    for prefix in delete_prefixes:
        if lowered.startswith(prefix):
            return {"action": "delete", "target": _clean(query[len(prefix):])}
    save_prefixes = ["remember that ", "remember ", "save this preference ", "save preference ", "save this "]
    for prefix in save_prefixes:
        if lowered.startswith(prefix):
            content = _clean(query[len(prefix):])
            if content:
                memory_type = "preference"
                if any(word in content.lower() for word in ("credential", "password", "token", "secret")):
                    memory_type = "credentials"
                elif any(word in content.lower() for word in ("security", "auth", "authentication")):
                    memory_type = "security"
                elif any(word in content.lower() for word in ("project", "platform", "website", "app")):
                    memory_type = "project"
                return {"action": "save", "memory_type": memory_type, "content": content}
    return {"action": None}


def save_memory(user_id: str, memory_type: str, content: str, importance: int = 80) -> Dict[str, Any]:
    payload = {"memory_id": f"mem-{int(_now().timestamp() * 1000)}", "user_id": user_id, "memory_type": memory_type, "content": content, "importance": max(1, min(100, int(importance))), "created_at": _now(), "updated_at": _now()}
    ai_memory_collection.insert_one(payload)
    payload.pop("_id", None)
    return payload


def list_memories(user_id: str) -> List[Dict[str, Any]]:
    return _memory_docs(user_id)


def delete_memory_by_query(user_id: str, target: str) -> Optional[Dict[str, Any]]:
    memories = _memory_docs(user_id)
    if not memories:
        return None
    lowered = target.lower().strip()
    selected = None
    if not lowered:
        selected = memories[-1]
    else:
        for item in memories:
            haystack = " ".join(_clean(item.get(field)).lower() for field in ("memory_type", "content", "importance"))
            if lowered in haystack:
                selected = item
                break
        if selected is None:
            selected = memories[-1]
    memory_id = selected.get("memory_id")
    if memory_id:
        ai_memory_collection.delete_one({"memory_id": memory_id, "user_id": user_id})
    return selected


def generate_instruction_template(topic: str) -> Dict[str, Any]:
    topic_text = _clean(topic).lower()
    templates = {
        "authentication": {"title": "Authentication Testing", "focus": ["Login validation", "Invalid credentials", "Session persistence", "Logout flow", "Security checks"], "requirements": ["Visit every authenticated page", "Capture screenshots for each failure", "Record bug evidence", "Generate a summary report"]},
        "signup": {"title": "Signup Testing", "focus": ["Signup form validation", "Email verification", "Password rules", "Duplicate account handling", "Session creation"], "requirements": ["Test valid and invalid signup paths", "Capture screenshots for every bug", "Verify account creation and login"]},
        "api": {"title": "API Testing", "focus": ["Endpoint availability", "Response codes", "Authentication headers", "Error handling", "Schema validation"], "requirements": ["Cover critical endpoints", "Capture network failures and response payloads", "Record request/response details"]},
        "accessibility": {"title": "Accessibility Testing", "focus": ["Keyboard navigation", "ARIA labels", "Color contrast", "Focus order", "Screen reader support"], "requirements": ["Check all interactive controls", "Capture accessibility bugs with screenshots", "Verify semantic structure"]},
        "performance": {"title": "Performance Testing", "focus": ["Page load times", "Interaction latency", "API responsiveness", "Stability under repeat actions", "Resource usage"], "requirements": ["Measure bottlenecks", "Capture timeout or slow-response evidence", "Summarize regressions"]},
        "security": {"title": "Security Testing", "focus": ["Authentication boundaries", "Authorization checks", "Sensitive data exposure", "Input handling", "Session security"], "requirements": ["Attempt invalid access paths", "Capture security failures", "Document any exposure or bypass"]},
        "regression": {"title": "Regression Testing", "focus": ["Stable user flows", "Core functionality", "High-risk areas", "Recent changes", "Bug revalidation"], "requirements": ["Run the critical path suite", "Capture regression evidence", "Compare against previous runs"]},
        "checkout": {"title": "Checkout Testing", "focus": ["Cart validation", "Address forms", "Payment flow", "Order confirmation", "Error handling"], "requirements": ["Test success and failure paths", "Capture screenshots for each issue", "Verify order state"]},
        "ecommerce": {"title": "E-commerce Testing", "focus": ["Login validation", "Catalog browsing", "Cart flow", "Checkout flow", "Order history"], "requirements": ["Cover the shopping journey", "Capture bugs with screenshots", "Verify end-to-end purchase readiness"]},
        "dashboard": {"title": "Dashboard Testing", "focus": ["Data widgets", "Filters", "Navigation", "Refresh behavior", "Access control"], "requirements": ["Validate every visible widget", "Capture dashboard regressions", "Confirm the data source is live"]},
        "admin": {"title": "Admin Panel Testing", "focus": ["Role-based access", "CRUD actions", "Auditability", "Bulk actions", "Permission boundaries"], "requirements": ["Test privileged and restricted paths", "Record access-control bugs", "Capture screenshots for each failure"]},
    }
    selected = templates["regression"]
    for key, template in templates.items():
        if key in topic_text:
            selected = template
            break
    topic_clean = _clean(topic) or selected["title"]
    lines = ["Test Objective:", f"Perform complete testing of {topic_clean}.", "", "Credentials:", "Email: user@example.com", "Password: password123", "", "Focus Areas:", *[f"- {item}" for item in selected["focus"]], "", "Requirements:", *[f"- {item}" for item in selected["requirements"]]]
    return {"topic": topic_clean, "template": selected["title"], "instructions": "\n".join(lines)}

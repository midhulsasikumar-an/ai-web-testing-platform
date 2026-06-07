from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from backend.database.mongo import ai_knowledge_index, bug_collection, collection as test_runs
from backend.database.report_repository import get_report, list_reports_for_user
from backend.ai_workspace.intelligence import resolve_entity_query


class AIRetrievalSystem:
    def _match_query(self, text: str, query: str) -> bool:
        normalized_text = text.lower()
        normalized_query = query.lower().strip()
        if not normalized_query:
            return True
        return all(token in normalized_text for token in normalized_query.split() if token)

    def _parse_date_query(self, query: str) -> Dict[str, Any]:
        now = datetime.utcnow()
        q = query.lower()
        if "today" in q:
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return {"$gte": start.isoformat()}
        if "yesterday" in q:
            start = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now.replace(hour=0, minute=0, second=0, microsecond=0)
            return {"$gte": start.isoformat(), "$lt": end.isoformat()}
        if "last week" in q:
            return {"$gte": (now - timedelta(days=7)).isoformat()}
        if "last month" in q:
            return {"$gte": (now - timedelta(days=30)).isoformat()}
        return {}

    def retrieve_tests(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {"user_id": user_id}
        date_filter = self._parse_date_query(query)
        if date_filter:
            filters["created_at"] = date_filter
        if "failed" in query.lower():
            filters["status"] = {"$in": ["failed", "fail", "timed_out"]}
        if "running" in query.lower():
            filters["status"] = "running"
        cursor = test_runs.find(filters, {"_id": 0}).sort("created_at", -1).limit(limit)
        items = list(cursor)
        if query:
            items = [item for item in items if self._match_query(" ".join(map(str, [item.get("test_name", ""), item.get("goal", ""), item.get("url", ""), item.get("status", ""), item.get("test_type", "")])), query)]
        return items[:limit]

    def retrieve_reports(self, user_id: str, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        reports = list_reports_for_user(user_id, limit=max(limit, 10))
        if query:
            reports = [item for item in reports if self._match_query(" ".join(map(str, [item.get("title", ""), item.get("summary", ""), item.get("website", ""), item.get("report_type", ""), item.get("status", "") ])), query)]
        return reports[:limit]

    def retrieve_bugs(self, user_id: str, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        filters: Dict[str, Any] = {"user_id": user_id}
        if "critical" in query.lower():
            filters["$or"] = [{"severity": "critical"}, {"priority": "critical"}]
        if "resolved" in query.lower():
            filters["status"] = {"$in": ["resolved", "closed"]}
        cursor = bug_collection.find(filters, {"_id": 0}).sort("created_at", -1).limit(limit)
        items = list(cursor)
        if query:
            items = [item for item in items if self._match_query(" ".join(map(str, [item.get("bug_name", ""), item.get("bug_description", ""), item.get("status", ""), item.get("severity", "") ])), query)]
        return items[:limit]

    def retrieve_screenshots(self, user_id: str, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> List[Dict[str, Any]]:
        report = None
        if report_id:
            report = get_report(report_id, user_id=user_id)
        if not report and test_run_id:
            report = get_report(test_run_id, user_id=user_id)
        if not report:
            return []

        screenshots: List[Dict[str, Any]] = []
        for path in report.get("screenshot_paths") or []:
            if isinstance(path, str) and path.strip():
                screenshots.append({"path": path, "label": "screenshot"})
        ai_report = report.get("ai_report") if isinstance(report.get("ai_report"), dict) else {}
        for item in (ai_report.get("screenshots") or []):
            if isinstance(item, dict):
                screenshots.append(item)
            elif isinstance(item, str) and item.strip():
                screenshots.append({"path": item, "label": "screenshot"})
        return screenshots

    def get_context(self, user_id: str, query: str, *, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> Dict[str, Any]:
        resolved = resolve_entity_query(user_id, query, report_id=report_id, test_run_id=test_run_id)
        return {
            "intent": resolved.get("intent", self.determine_intent(query)),
            "data": resolved.get("data", []),
            "summary": resolved.get("summary", ""),
            "details": resolved.get("details", {}),
        }

    def determine_intent(self, query: str) -> str:
        q = query.lower()
        if "compare" in q:
            return "compare_runs"
        if any(phrase in q for phrase in ["which run had most bugs", "which run failed most", "show regression trend", "show quality trend", "show bug trend", "summarize last 10 runs", "authentication issues", "api failures"]):
            return "historical_analytics"
        if "instruction" in q or "test objective" in q:
            return "instruction_generation"
        if "screenshot" in q or "image" in q or "visual" in q:
            return "screenshot_analysis"
        if "bug" in q or "issue" in q or "failure" in q:
            return "query_bugs"
        if "report" in q or "latest test run" in q or "run" in q or "execution log" in q:
            return "report_analysis"
        if "compare" in q:
            return "compare_runs"
        if "memory" in q:
            return "memory"
        if "test" in q or "run" in q:
            return "test_run_analysis"
        return "general_chat"

    def summarize_reports(self, user_id: str, query: str = "", report_id: Optional[str] = None) -> Dict[str, Any]:
        reports = self.retrieve_reports(user_id, query or "", limit=10)
        selected = get_report(report_id, user_id=user_id) if report_id else (reports[0] if reports else None)
        recurring = Counter()
        flaky = []
        critical = []
        for report in reports:
            summary = str(report.get("summary") or "")
            if "flaky" in summary.lower():
                flaky.append(report)
            if str(report.get("status") or "").lower() in {"failed", "fail"}:
                critical.append(report)
            recurring[report.get("report_type") or "legacy"] += 1
        return {
            "selected_report": selected,
            "count": len(reports),
            "critical_count": len(critical),
            "flaky_count": len(flaky),
            "by_type": dict(recurring),
            "reports": reports,
        }

    def summarize_bugs(self, user_id: str, query: str = "") -> Dict[str, Any]:
        bugs = self.retrieve_bugs(user_id, query, limit=50)
        by_status = Counter(str(b.get("status") or "unknown").lower() for b in bugs)
        by_severity = Counter(str(b.get("severity") or "medium").lower() for b in bugs)
        grouped: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        for bug in bugs:
            grouped[str(bug.get("bug_name") or bug.get("title") or "other")[:80]].append(bug)
        return {
            "count": len(bugs),
            "by_status": dict(by_status),
            "by_severity": dict(by_severity),
            "groups": {key: items[:5] for key, items in grouped.items()},
            "bugs": bugs,
        }

    def summarize_screenshots(self, user_id: str, report_id: Optional[str] = None, test_run_id: Optional[str] = None) -> Dict[str, Any]:
        screenshots = self.retrieve_screenshots(user_id, report_id=report_id, test_run_id=test_run_id)
        if not screenshots:
            return {"count": 0, "message": "No screenshots are available for the selected report or test run.", "screenshots": []}
        return {"count": len(screenshots), "message": "Screenshots are available for inspection.", "screenshots": screenshots}


retrieval_system = AIRetrievalSystem()

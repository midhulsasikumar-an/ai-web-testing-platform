from __future__ import annotations

import asyncio
from collections import Counter
from typing import Any, Dict, List


class WorkflowCoverageEngine:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._routes: set[str] = set()
        self._forms_tested: set[str] = set()
        self._apis_triggered: set[str] = set()
        self._interactions: Counter[str] = Counter()
        self._accessibility_findings = 0
        self._performance_findings = 0

    async def record_route(self, route: str) -> None:
        async with self._lock:
            self._routes.add(route)

    async def record_form(self, form_name: str) -> None:
        async with self._lock:
            self._forms_tested.add(form_name)

    async def record_api(self, api_name: str) -> None:
        async with self._lock:
            self._apis_triggered.add(api_name)

    async def record_interaction(self, interaction_type: str) -> None:
        async with self._lock:
            self._interactions[interaction_type] += 1

    async def record_accessibility(self, finding_count: int) -> None:
        async with self._lock:
            self._accessibility_findings += max(0, finding_count)

    async def record_performance(self, finding_count: int) -> None:
        async with self._lock:
            self._performance_findings += max(0, finding_count)

    async def record_run(self, run_data: Dict[str, Any]) -> None:
        for step in run_data.get("steps", []):
            observation = step.get("observation") or {}
            url = observation.get("url")
            if url:
                await self.record_route(url.split("#")[0])
            action = (step.get("action") or {}).get("action") if isinstance(step.get("action"), dict) else None
            if action:
                await self.record_interaction(str(action))
            forms = observation.get("forms") or []
            for form in forms:
                await self.record_form(str(form.get("name") or form.get("id") or form.get("action") or "form"))

        summary = run_data.get("summary", {}) if isinstance(run_data.get("summary"), dict) else {}
        await self.record_accessibility(len(summary.get("accessibility_findings", []) or []))
        await self.record_performance(len(summary.get("performance_findings", []) or []))

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            score = min(
                100.0,
                len(self._routes) * 10.0
                + len(self._forms_tested) * 8.0
                + len(self._apis_triggered) * 7.0
                + sum(self._interactions.values()) * 2.0
                + max(0, 20 - self._accessibility_findings * 2)
                + max(0, 20 - self._performance_findings * 2),
            )
            return {
                "coverage_score": round(score, 2),
                "routes_explored": sorted(self._routes),
                "forms_tested": sorted(self._forms_tested),
                "apis_triggered": sorted(self._apis_triggered),
                "interactions_performed": dict(self._interactions),
                "accessibility_findings": self._accessibility_findings,
                "performance_findings": self._performance_findings,
            }

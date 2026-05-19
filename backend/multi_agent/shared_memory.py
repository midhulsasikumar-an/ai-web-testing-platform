from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.multi_agent.models import AgentExecutionResult, MultiAgentFinding


class SharedAgentMemory:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._lock = asyncio.Lock()
        self._version = 0
        self._storage_state_path: Optional[str] = None
        self._session_storage: Dict[str, Any] = {}
        self._auth_session: Dict[str, Any] = {}
        self._discovered_routes: List[str] = []
        self._screenshots: List[Dict[str, Any]] = []
        self._workflow_states: List[str] = []
        self._detected_bugs: List[Dict[str, Any]] = []
        self._api_failures: List[Dict[str, Any]] = []
        self._navigation_paths: List[Dict[str, Any]] = []
        self._agent_results: Dict[str, Dict[str, Any]] = {}

    async def set_storage_state_path(self, path: Optional[str]) -> None:
        async with self._lock:
            self._storage_state_path = path
            self._version += 1

    async def set_session_storage(self, session_storage: Dict[str, Any]) -> None:
        async with self._lock:
            self._session_storage = dict(session_storage)
            self._version += 1

    async def set_auth_session(self, *, authenticated: bool, confidence: float, details: Dict[str, Any]) -> None:
        async with self._lock:
            self._auth_session = {
                "authenticated": authenticated,
                "confidence": confidence,
                "details": dict(details),
                "updated_at": datetime.utcnow().isoformat(),
            }
            self._version += 1

    async def record_route(self, url: str) -> None:
        normalized = url.split("#")[0]
        async with self._lock:
            if normalized not in self._discovered_routes:
                self._discovered_routes.append(normalized)
                self._version += 1

    async def record_workflow_state(self, workflow_state: str) -> None:
        async with self._lock:
            if workflow_state and workflow_state not in self._workflow_states:
                self._workflow_states.append(workflow_state)
                self._version += 1

    async def record_screenshot(self, *, agent_name: str, path: str, url: str, workflow_state: Optional[str] = None) -> None:
        async with self._lock:
            self._screenshots.append({
                "agent": agent_name,
                "path": path,
                "url": url,
                "workflow_state": workflow_state,
                "captured_at": datetime.utcnow().isoformat(),
            })
            self._version += 1

    async def record_bug(self, finding: MultiAgentFinding) -> None:
        async with self._lock:
            self._detected_bugs.append(finding.model_dump(mode="json"))
            self._version += 1

    async def record_api_failure(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            self._api_failures.append(dict(payload))
            self._version += 1

    async def record_navigation_path(self, payload: Dict[str, Any]) -> None:
        async with self._lock:
            self._navigation_paths.append(dict(payload))
            self._version += 1

    async def record_agent_result(self, result: AgentExecutionResult) -> None:
        async with self._lock:
            self._agent_results[result.agent_name] = result.model_dump(mode="json")
            self._version += 1

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            return {
                "run_id": self.run_id,
                "version": self._version,
                "storage_state_path": self._storage_state_path,
                "session_storage": dict(self._session_storage),
                "auth_session": dict(self._auth_session),
                "discovered_routes": list(self._discovered_routes),
                "screenshots": list(self._screenshots),
                "workflow_states": list(self._workflow_states),
                "detected_bugs": list(self._detected_bugs),
                "api_failures": list(self._api_failures),
                "navigation_paths": list(self._navigation_paths),
                "agent_results": dict(self._agent_results),
            }

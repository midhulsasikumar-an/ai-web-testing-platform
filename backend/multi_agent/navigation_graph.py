from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    node_id: str
    url: str = ""
    workflow_state: str = ""
    page_type: str = ""
    agent_name: str = ""
    visit_count: int = 0
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class GraphEdge(BaseModel):
    edge_id: str
    from_node: str
    to_node: str
    action: str = ""
    agent_name: str = ""
    url: str = ""
    confidence: float = 0.0
    count: int = 0
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class NavigationGraphEngine:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._nodes: Dict[str, GraphNode] = {}
        self._edges: Dict[str, GraphEdge] = {}

    @staticmethod
    def _node_id(url: str, workflow_state: str, page_type: str = "") -> str:
        normalized_url = url.split("#")[0].split("?")[0]
        return f"{workflow_state or page_type or 'unknown'}::{normalized_url}"

    async def record_transition(
        self,
        *,
        from_url: str,
        to_url: str,
        workflow_state: str,
        page_type: str = "",
        action: str = "",
        agent_name: str = "",
        confidence: float = 0.0,
    ) -> Dict[str, Any]:
        from_node_id = self._node_id(from_url, workflow_state, page_type)
        to_node_id = self._node_id(to_url, workflow_state, page_type)
        edge_id = f"{from_node_id}->{to_node_id}:{action or 'transition'}:{agent_name or 'agent'}"

        async with self._lock:
            from_node = self._nodes.get(from_node_id) or GraphNode(
                node_id=from_node_id,
                url=from_url,
                workflow_state=workflow_state,
                page_type=page_type,
                agent_name=agent_name,
                visit_count=0,
            )
            from_node.visit_count += 1
            from_node.last_seen = datetime.utcnow()
            self._nodes[from_node_id] = from_node

            to_node = self._nodes.get(to_node_id) or GraphNode(
                node_id=to_node_id,
                url=to_url,
                workflow_state=workflow_state,
                page_type=page_type,
                agent_name=agent_name,
                visit_count=0,
            )
            to_node.visit_count += 1
            to_node.last_seen = datetime.utcnow()
            self._nodes[to_node_id] = to_node

            edge = self._edges.get(edge_id) or GraphEdge(
                edge_id=edge_id,
                from_node=from_node_id,
                to_node=to_node_id,
                action=action,
                agent_name=agent_name,
                url=to_url,
                confidence=confidence,
                count=0,
            )
            edge.count += 1
            edge.last_seen = datetime.utcnow()
            edge.confidence = max(edge.confidence, confidence)
            self._edges[edge_id] = edge

        return {
            "from_node": from_node.model_dump(mode="json"),
            "to_node": to_node.model_dump(mode="json"),
            "edge": edge.model_dump(mode="json"),
        }

    async def record_run(self, run_data: Dict[str, Any], agent_name: str) -> None:
        steps = run_data.get("steps", [])
        previous_url = run_data.get("start_url", "")
        for step in steps:
            observation = step.get("observation") or {}
            next_url = observation.get("url") or previous_url
            workflow_state = step.get("workflow_state_after") or observation.get("page_type") or "unknown"
            page_type = observation.get("page_type") or ""
            action = (step.get("action") or {}).get("action") if isinstance(step.get("action"), dict) else str(step.get("action") or "")
            confidence = float((step.get("planner_decision") or {}).get("confidence") or 0.0) if isinstance(step.get("planner_decision"), dict) else 0.0
            await self.record_transition(
                from_url=previous_url or next_url,
                to_url=next_url,
                workflow_state=str(workflow_state),
                page_type=str(page_type),
                action=action,
                agent_name=agent_name,
                confidence=confidence,
            )
            previous_url = next_url

    async def snapshot(self) -> Dict[str, Any]:
        async with self._lock:
            coverage_score = min(100.0, len(self._nodes) * 8.0 + len(self._edges) * 5.0)
            return {
                "nodes": [node.model_dump(mode="json") for node in self._nodes.values()],
                "edges": [edge.model_dump(mode="json") for edge in self._edges.values()],
                "coverage_score": round(coverage_score, 2),
                "path_count": len(self._edges),
            }

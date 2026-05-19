from __future__ import annotations

"""
Navigation edge — a directed edge in the world-state graph representing
an action-based transition between two semantic states.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NavigationEdge(BaseModel):
    """
    A directed edge in the world-model navigation graph.

    Each edge represents a specific action that caused a state transition
    from one NavigationNode to another.
    """
    edge_id: str
    source_node_id: str
    target_node_id: str
    action_type: str  # click, fill, navigate, submit, etc.
    selector: Optional[str] = None
    target_label: Optional[str] = None
    action_value: Optional[str] = None
    transition_confidence: float = 0.0
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    total_latency_ms: float = 0.0
    last_execution_result: Optional[str] = None
    skill_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    @property
    def reliability_score(self) -> float:
        """Reliability score combining success rate with sample size confidence."""
        rate = self.success_rate
        sample_confidence = min(self.execution_count / 5.0, 1.0)
        return rate * sample_confidence

    def record_execution(self, success: bool, latency_ms: float) -> None:
        self.execution_count += 1
        self.total_latency_ms += latency_ms
        self.avg_latency_ms = self.total_latency_ms / self.execution_count
        self.last_used = datetime.utcnow()
        if success:
            self.success_count += 1
            self.last_execution_result = "success"
        else:
            self.failure_count += 1
            self.last_execution_result = "failure"
        self.transition_confidence = self.reliability_score

    @staticmethod
    def generate_edge_id(
        source_node_id: str,
        target_node_id: str,
        action_type: str,
        selector: Optional[str] = None,
    ) -> str:
        import hashlib
        payload = f"{source_node_id}|{target_node_id}|{action_type}|{selector or ''}"
        return hashlib.sha256(payload.encode()).hexdigest()[:24]

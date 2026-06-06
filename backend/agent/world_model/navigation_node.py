from __future__ import annotations

"""
Navigation node — a vertex in the world-state graph representing a
unique semantic application state the agent has observed.
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NavigationNode(BaseModel):
    """
    A single node in the world-model navigation graph.

    Each node represents a unique semantic page state, identified
    by a combination of URL pattern, DOM fingerprint, and page type.
    """
    node_id: str
    url: str
    url_pattern: str = ""  # normalized URL without query params / fragments
    page_type: str = ""
    dom_fingerprint: str = ""
    semantic_labels: List[str] = Field(default_factory=list)
    screenshot_hash: Optional[str] = None
    workflow_state: str = ""
    headings: List[str] = Field(default_factory=list)
    form_count: int = 0
    interactive_element_count: int = 0
    visit_count: int = 0
    first_visited: datetime = Field(default_factory=datetime.utcnow)
    last_visited: datetime = Field(default_factory=datetime.utcnow)
    total_time_spent_ms: int = 0
    success_actions: int = 0
    failed_actions: int = 0
    embeddings: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    is_terminal: bool = False  # dead-end or goal state
    is_error_state: bool = False
    parent_node_id: Optional[str] = None
    depth: int = 0

    @property
    def success_rate(self) -> float:
        total = self.success_actions + self.failed_actions
        return self.success_actions / total if total > 0 else 0.0

    @property
    def revisitation_score(self) -> float:
        """Score indicating how much this node has been revisited
        relative to useful actions. High revisitation with low success
        indicates a stagnation hotspot."""
        if self.visit_count <= 1:
            return 0.0
        return min(self.visit_count / max(self.success_actions, 1), 10.0)

    def update_visit(self, duration_ms: int = 0) -> None:
        self.visit_count += 1
        self.last_visited = datetime.utcnow()
        self.total_time_spent_ms += duration_ms

    def record_action_result(self, success: bool) -> None:
        if success:
            self.success_actions += 1
        else:
            self.failed_actions += 1

    @staticmethod
    def generate_node_id(url: str, dom_fingerprint: str, page_type: str) -> str:
        payload = f"{url.split('?')[0].split('#')[0]}|{dom_fingerprint[:16]}|{page_type}"
        return hashlib.sha256(payload.encode()).hexdigest()[:24]

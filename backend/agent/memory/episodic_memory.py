"""
Advanced episodic memory — execution history, observations, failures,
and recoveries with vector embedding support.
"""

from __future__ import annotations

import uuid
import logging
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.models.memory import EpisodicRecord

logger = logging.getLogger("agent.memory.episodic")


class EpisodicMemory:
    """
    Stores and retrieves episodic records of agent experience.
    Each episode captures a single action-observation-result cycle.
    Supports similarity-based retrieval for future embedding integration.
    """

    def __init__(self, max_records: int = 10000) -> None:
        self._records: List[EpisodicRecord] = []
        self._max_records = max_records
        self._session_index: Dict[str, List[int]] = {}  # session_id -> [record indices]
        self._failure_index: Dict[str, List[int]] = {}  # failure_type -> [record indices]
        self._url_index: Dict[str, List[int]] = {}  # url -> [record indices]

    def record(
        self, session_id: str, step: int, observation_fingerprint: str,
        action_taken: str, result_success: bool, url: str = "",
        page_type: str = "", workflow_state: str = "",
        action_target: Optional[str] = None, failure_type: Optional[str] = None,
        duration_ms: int = 0, recovery_applied: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EpisodicRecord:
        episode = EpisodicRecord(
            episode_id=str(uuid.uuid4())[:12],
            session_id=session_id, step=step,
            observation_fingerprint=observation_fingerprint,
            action_taken=action_taken, action_target=action_target,
            result_success=result_success, failure_type=failure_type,
            url=url, page_type=page_type, workflow_state=workflow_state,
            duration_ms=duration_ms, recovery_applied=recovery_applied,
            metadata=metadata or {},
        )

        idx = len(self._records)
        self._records.append(episode)
        self._session_index.setdefault(session_id, []).append(idx)
        if failure_type:
            self._failure_index.setdefault(failure_type, []).append(idx)
        if url:
            self._url_index.setdefault(url.split("?")[0], []).append(idx)

        if len(self._records) > self._max_records:
            self._compress()

        return episode

    def get_session_history(self, session_id: str) -> List[EpisodicRecord]:
        indices = self._session_index.get(session_id, [])
        return [self._records[i] for i in indices if i < len(self._records)]

    def get_failures_for_url(self, url: str) -> List[EpisodicRecord]:
        url_key = url.split("?")[0]
        indices = self._url_index.get(url_key, [])
        return [self._records[i] for i in indices if i < len(self._records) and not self._records[i].result_success]

    def get_similar_situations(
        self, url: str, page_type: str, action: str, limit: int = 5,
    ) -> List[EpisodicRecord]:
        """Find similar past situations for decision support."""
        scored: List[tuple[float, EpisodicRecord]] = []
        for record in self._records:
            score = 0.0
            if record.url.split("?")[0] == url.split("?")[0]:
                score += 3.0
            if record.page_type == page_type:
                score += 2.0
            if record.action_taken == action:
                score += 1.0
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [r for _, r in scored[:limit]]

    def get_success_rate(self, url: str = "", action: str = "") -> float:
        relevant = self._records
        if url:
            url_key = url.split("?")[0]
            indices = self._url_index.get(url_key, [])
            relevant = [self._records[i] for i in indices if i < len(self._records)]
        if action:
            relevant = [r for r in relevant if r.action_taken == action]
        if not relevant:
            return 0.0
        return sum(1 for r in relevant if r.result_success) / len(relevant)

    def compact_for_llm(self, session_id: str, max_records: int = 10) -> List[Dict[str, Any]]:
        history = self.get_session_history(session_id)[-max_records:]
        return [
            {
                "step": r.step, "action": r.action_taken,
                "target": r.action_target, "success": r.result_success,
                "failure": r.failure_type, "url": r.url, "page": r.page_type,
            }
            for r in history
        ]

    def _compress(self) -> None:
        """Remove oldest 20% of records when limit exceeded."""
        cutoff = len(self._records) // 5
        self._records = self._records[cutoff:]
        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        self._session_index.clear()
        self._failure_index.clear()
        self._url_index.clear()
        for i, record in enumerate(self._records):
            self._session_index.setdefault(record.session_id, []).append(i)
            if record.failure_type:
                self._failure_index.setdefault(record.failure_type, []).append(i)
            if record.url:
                self._url_index.setdefault(record.url.split("?")[0], []).append(i)

    @property
    def total_records(self) -> int:
        return len(self._records)

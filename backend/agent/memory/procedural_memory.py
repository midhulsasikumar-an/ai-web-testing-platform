"""
Procedural memory — reusable action chains learned from successful executions.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.models.memory import ProceduralChain

logger = logging.getLogger("agent.memory.procedural")


class ProceduralMemory:
    """
    Stores and retrieves successful action chains that can be reused.
    Chains are learned from successful multi-step executions and
    can be replayed when similar situations are encountered.
    """

    def __init__(self, max_chains: int = 1000) -> None:
        self._chains: Dict[str, ProceduralChain] = {}
        self._max_chains = max_chains

    def learn_chain(
        self, chain_name: str, description: str,
        steps: List[Dict[str, Any]],
        preconditions: Dict[str, Any],
        postconditions: Dict[str, Any],
        page_types: Optional[List[str]] = None,
        workflow_states: Optional[List[str]] = None,
    ) -> ProceduralChain:
        """Learn a new procedural chain or reinforce an existing one."""
        existing = self._find_matching(chain_name, preconditions)
        if existing:
            existing.success_count += 1
            existing.last_used = datetime.utcnow()
            total = existing.success_count + existing.failure_count
            existing.confidence = existing.success_count / total if total > 0 else 0.0
            return existing

        chain = ProceduralChain(
            chain_id=str(uuid.uuid4())[:12],
            chain_name=chain_name,
            description=description,
            steps=steps,
            preconditions=preconditions,
            postconditions=postconditions,
            success_count=1,
            applicable_page_types=page_types or [],
            applicable_workflow_states=workflow_states or [],
            confidence=0.5,
        )
        self._chains[chain.chain_id] = chain

        if len(self._chains) > self._max_chains:
            self._evict_unused()

        return chain

    def record_failure(self, chain_id: str) -> None:
        chain = self._chains.get(chain_id)
        if chain:
            chain.failure_count += 1
            total = chain.success_count + chain.failure_count
            chain.confidence = chain.success_count / total if total > 0 else 0.0

    def find_applicable(
        self, page_type: str, workflow_state: str,
        min_confidence: float = 0.5, limit: int = 5,
    ) -> List[ProceduralChain]:
        """Find chains applicable to the current situation."""
        candidates: List[tuple[float, ProceduralChain]] = []
        for chain in self._chains.values():
            if chain.confidence < min_confidence:
                continue
            score = chain.confidence
            if page_type in chain.applicable_page_types:
                score += 0.3
            if workflow_state in chain.applicable_workflow_states:
                score += 0.2
            candidates.append((score, chain))
        candidates.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in candidates[:limit]]

    def get_chain(self, chain_id: str) -> Optional[ProceduralChain]:
        return self._chains.get(chain_id)

    def _find_matching(self, name: str, preconditions: Dict[str, Any]) -> Optional[ProceduralChain]:
        for chain in self._chains.values():
            if chain.chain_name == name:
                return chain
        return None

    def _evict_unused(self) -> None:
        sorted_chains = sorted(
            self._chains.values(),
            key=lambda c: (c.confidence, c.last_used),
        )
        to_remove = sorted_chains[: len(sorted_chains) // 5]
        for c in to_remove:
            self._chains.pop(c.chain_id, None)

    @property
    def total_chains(self) -> int:
        return len(self._chains)

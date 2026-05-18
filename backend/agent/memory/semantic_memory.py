"""
Semantic memory — learned patterns, reusable workflows,
and semantic page understanding with confidence tracking.
"""

from __future__ import annotations

import uuid
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from backend.core.models.memory import SemanticPattern

logger = logging.getLogger("agent.memory.semantic")


class SemanticMemory:
    """
    Stores learned semantic patterns from agent experience.
    Patterns include page layouts, form structures, navigation patterns,
    and error patterns that the agent can reuse across sessions.
    """

    def __init__(self, max_patterns: int = 5000) -> None:
        self._patterns: Dict[str, SemanticPattern] = {}
        self._max_patterns = max_patterns
        self._type_index: Dict[str, List[str]] = {}  # pattern_type -> [pattern_ids]

    def learn_pattern(
        self, pattern_type: str, description: str,
        conditions: Dict[str, Any], session_id: str,
        confidence: float = 0.5, success_rate: float = 0.0,
    ) -> SemanticPattern:
        """Learn or reinforce a semantic pattern."""
        existing = self._find_matching(pattern_type, conditions)
        if existing:
            existing.occurrence_count += 1
            existing.last_seen = datetime.utcnow()
            if session_id not in existing.learned_from_sessions:
                existing.learned_from_sessions.append(session_id)
            existing.success_rate = (
                existing.success_rate * (existing.occurrence_count - 1) + success_rate
            ) / existing.occurrence_count
            existing.confidence = min(existing.occurrence_count / 10.0, 0.99)
            return existing

        pattern = SemanticPattern(
            pattern_id=str(uuid.uuid4())[:12],
            pattern_type=pattern_type,
            description=description,
            conditions=conditions,
            learned_from_sessions=[session_id],
            occurrence_count=1,
            success_rate=success_rate,
            confidence=confidence,
        )
        self._patterns[pattern.pattern_id] = pattern
        self._type_index.setdefault(pattern_type, []).append(pattern.pattern_id)

        if len(self._patterns) > self._max_patterns:
            self._evict_low_confidence()

        return pattern

    def query(
        self, pattern_type: Optional[str] = None,
        conditions: Optional[Dict[str, Any]] = None,
        min_confidence: float = 0.0, limit: int = 10,
    ) -> List[SemanticPattern]:
        """Query patterns by type and conditions."""
        candidates = list(self._patterns.values())
        if pattern_type:
            pattern_ids = self._type_index.get(pattern_type, [])
            candidates = [self._patterns[pid] for pid in pattern_ids if pid in self._patterns]
        if min_confidence > 0:
            candidates = [p for p in candidates if p.confidence >= min_confidence]
        if conditions:
            scored: List[tuple[float, SemanticPattern]] = []
            for p in candidates:
                match_score = self._condition_match_score(p.conditions, conditions)
                if match_score > 0:
                    scored.append((match_score, p))
            scored.sort(key=lambda x: x[0], reverse=True)
            return [p for _, p in scored[:limit]]
        candidates.sort(key=lambda p: p.confidence, reverse=True)
        return candidates[:limit]

    def get_page_patterns(self, url: str, page_type: str) -> List[SemanticPattern]:
        """Get patterns relevant to a specific page."""
        conditions = {"url_pattern": url.split("?")[0], "page_type": page_type}
        return self.query(conditions=conditions, min_confidence=0.3)

    def _find_matching(self, pattern_type: str, conditions: Dict[str, Any]) -> Optional[SemanticPattern]:
        pattern_ids = self._type_index.get(pattern_type, [])
        for pid in pattern_ids:
            pattern = self._patterns.get(pid)
            if pattern and self._condition_match_score(pattern.conditions, conditions) > 0.8:
                return pattern
        return None

    @staticmethod
    def _condition_match_score(stored: Dict[str, Any], query: Dict[str, Any]) -> float:
        if not stored or not query:
            return 0.0
        matching = sum(1 for k, v in query.items() if stored.get(k) == v)
        return matching / len(query) if query else 0.0

    def _evict_low_confidence(self) -> None:
        sorted_patterns = sorted(self._patterns.values(), key=lambda p: p.confidence)
        to_remove = sorted_patterns[: len(sorted_patterns) // 5]
        for p in to_remove:
            self._patterns.pop(p.pattern_id, None)
        self._rebuild_type_index()

    def _rebuild_type_index(self) -> None:
        self._type_index.clear()
        for pid, p in self._patterns.items():
            self._type_index.setdefault(p.pattern_type, []).append(pid)

    @property
    def total_patterns(self) -> int:
        return len(self._patterns)

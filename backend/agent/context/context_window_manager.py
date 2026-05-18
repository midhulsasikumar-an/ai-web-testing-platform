"""
Context window manager — intelligent DOM compression, token budget
management, observation prioritization, and reasoning context building.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.core.models.observations import Observation

logger = logging.getLogger("agent.context")


class TokenBudgetManager:
    """Manages token budgets across different context sections."""

    def __init__(
        self, max_budget: int = 8192,
        observation_limit: int = 3000, memory_limit: int = 2000,
        reasoning_limit: int = 2000, reserve: int = 1192,
    ) -> None:
        self.max_budget = max_budget
        self.limits = {
            "observation": observation_limit,
            "memory": memory_limit,
            "reasoning": reasoning_limit,
            "reserve": reserve,
        }
        self._usage: Dict[str, int] = {k: 0 for k in self.limits}

    def allocate(self, section: str, tokens: int) -> int:
        """Allocate tokens for a section, returning actual allocated amount."""
        limit = self.limits.get(section, 0)
        allocated = min(tokens, limit - self._usage.get(section, 0))
        self._usage[section] = self._usage.get(section, 0) + max(allocated, 0)
        return max(allocated, 0)

    def remaining(self, section: str) -> int:
        return self.limits.get(section, 0) - self._usage.get(section, 0)

    @property
    def total_used(self) -> int:
        return sum(self._usage.values())

    @property
    def total_remaining(self) -> int:
        return self.max_budget - self.total_used

    def reset(self) -> None:
        self._usage = {k: 0 for k in self.limits}


class ObservationCompressor:
    """Compresses observations to fit within token budgets."""

    def __init__(self, max_elements: int = 80, max_text_chars: int = 4000) -> None:
        self._max_elements = max_elements
        self._max_text = max_text_chars

    def compress(self, observation: Observation, budget_tokens: int = 3000) -> Dict[str, Any]:
        """Compress observation to fit within token budget."""
        element_limit = self._max_elements
        text_limit = self._max_text

        if budget_tokens < 2000:
            element_limit = min(element_limit, 40)
            text_limit = min(text_limit, 2000)
        elif budget_tokens < 1000:
            element_limit = min(element_limit, 20)
            text_limit = min(text_limit, 1000)

        # Prioritize visible, enabled, interactive elements
        prioritized = sorted(
            observation.elements,
            key=lambda e: (
                e.visible and e.enabled,
                e.role in {"button", "link", "textbox", "combobox"},
                e.editable,
                -(e.index),
            ),
            reverse=True,
        )[:element_limit]

        elements = []
        for el in prioritized:
            elements.append({
                "i": el.index, "role": el.role, "tag": el.tag,
                "label": el.label[:60] if el.label else "",
                "href": el.href[:80] if el.href else None,
                "vis": el.visible, "en": el.enabled, "ed": el.editable,
            })

        return {
            "url": observation.url,
            "title": observation.title[:100],
            "page_type": observation.page_type,
            "headings": observation.headings[:10],
            "text": observation.page_text[:text_limit],
            "errors": observation.console_errors[-5:],
            "network_fails": observation.network_failures[-5:],
            "dialogs": observation.dialogs[-3:],
            "fingerprint": observation.fingerprint[:16],
            "elements": elements,
            "total_elements": len(observation.elements),
        }


class ReasoningContextBuilder:
    """Builds the full context for LLM-based planning."""

    def __init__(self) -> None:
        self._budget = TokenBudgetManager()
        self._compressor = ObservationCompressor()

    def build(
        self, observation: Observation,
        memory_context: Dict[str, Any],
        world_graph_context: Dict[str, Any],
        objective_context: Optional[Dict[str, Any]] = None,
        reasoning_history: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Build a complete reasoning context within token budget."""
        self._budget.reset()

        compressed_obs = self._compressor.compress(
            observation, self._budget.remaining("observation")
        )

        context = {
            "observation": compressed_obs,
            "memory": self._trim_memory(memory_context),
            "world_model": self._trim_world_graph(world_graph_context),
        }

        if objective_context:
            context["objective"] = objective_context

        if reasoning_history:
            context["recent_reasoning"] = reasoning_history[-5:]

        return context

    def _trim_memory(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        """Trim memory context to fit budget."""
        trimmed = {}
        for key, value in memory.items():
            if isinstance(value, list):
                trimmed[key] = value[:8]
            else:
                trimmed[key] = value
        return trimmed

    def _trim_world_graph(self, graph: Dict[str, Any]) -> Dict[str, Any]:
        """Trim world graph context to fit budget."""
        trimmed = {}
        for key, value in graph.items():
            if isinstance(value, list):
                trimmed[key] = value[:10]
            else:
                trimmed[key] = value
        return trimmed

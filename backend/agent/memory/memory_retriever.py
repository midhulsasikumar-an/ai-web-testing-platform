"""
Memory retriever and ranker — unified retrieval across all memory subsystems.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from backend.agent.memory.episodic_memory import EpisodicMemory
from backend.agent.memory.semantic_memory import SemanticMemory
from backend.agent.memory.procedural_memory import ProceduralMemory
from backend.core.models.planner import MemoryReference

logger = logging.getLogger("agent.memory.retriever")


class MemoryRetriever:
    """Unified retrieval across episodic, semantic, and procedural memory."""

    def __init__(
        self,
        episodic: EpisodicMemory,
        semantic: SemanticMemory,
        procedural: ProceduralMemory,
    ) -> None:
        self._episodic = episodic
        self._semantic = semantic
        self._procedural = procedural

    def retrieve_relevant(
        self, url: str, page_type: str, workflow_state: str,
        action: str = "", limit: int = 10,
    ) -> List[MemoryReference]:
        """Retrieve relevant memories from all subsystems."""
        references: List[MemoryReference] = []

        # Episodic memories
        episodes = self._episodic.get_similar_situations(url, page_type, action, limit=5)
        for ep in episodes:
            references.append(MemoryReference(
                memory_type="episodic",
                reference_id=ep.episode_id,
                relevance_score=0.7 if ep.result_success else 0.3,
                content_summary=f"Step {ep.step}: {ep.action_taken} on {ep.page_type} -> {'success' if ep.result_success else 'failed'}",
                step_origin=ep.step,
            ))

        # Semantic patterns
        patterns = self._semantic.get_page_patterns(url, page_type)
        for pat in patterns[:3]:
            references.append(MemoryReference(
                memory_type="semantic",
                reference_id=pat.pattern_id,
                relevance_score=pat.confidence,
                content_summary=f"Pattern: {pat.description} (seen {pat.occurrence_count}x, success {pat.success_rate:.0%})",
            ))

        # Procedural chains
        chains = self._procedural.find_applicable(page_type, workflow_state, limit=3)
        for chain in chains:
            references.append(MemoryReference(
                memory_type="procedural",
                reference_id=chain.chain_id,
                relevance_score=chain.confidence,
                content_summary=f"Chain: {chain.chain_name} ({chain.success_count} successes, {len(chain.steps)} steps)",
            ))

        references.sort(key=lambda r: r.relevance_score, reverse=True)
        return references[:limit]

    def compact_for_llm(self, url: str, page_type: str, workflow_state: str) -> Dict[str, Any]:
        """Compact memory summary for LLM context."""
        refs = self.retrieve_relevant(url, page_type, workflow_state, limit=8)
        return {
            "relevant_memories": [
                {"type": r.memory_type, "summary": r.content_summary, "relevance": round(r.relevance_score, 2)}
                for r in refs
            ],
            "episodic_count": self._episodic.total_records,
            "semantic_patterns": self._semantic.total_patterns,
            "procedural_chains": self._procedural.total_chains,
            "url_success_rate": self._episodic.get_success_rate(url=url),
        }

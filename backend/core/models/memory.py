"""
Memory event models for episodic, semantic, and procedural memory.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class MemoryEvent(BaseModel):
    """A single event in the agent's memory timeline."""
    event_type: Literal[
        "observation", "action", "validation", "execution",
        "recovery", "navigation", "selector", "failure",
        "goal", "skill", "reasoning", "objective",
    ]
    message: str
    step: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance_score: float = 0.5
    embedding: Optional[List[float]] = None


class EpisodicRecord(BaseModel):
    """A single episode in the agent's episodic memory."""
    episode_id: str
    session_id: str
    step: int
    observation_fingerprint: str
    action_taken: str
    action_target: Optional[str] = None
    result_success: bool
    failure_type: Optional[str] = None
    url: str = ""
    page_type: str = ""
    workflow_state: str = ""
    duration_ms: int = 0
    recovery_applied: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SemanticPattern(BaseModel):
    """A learned semantic pattern from agent experience."""
    pattern_id: str
    pattern_type: str  # page_layout, form_structure, navigation_pattern, error_pattern
    description: str
    conditions: Dict[str, Any] = Field(default_factory=dict)
    learned_from_sessions: List[str] = Field(default_factory=list)
    occurrence_count: int = 1
    success_rate: float = 0.0
    confidence: float = 0.0
    embedding: Optional[List[float]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_seen: datetime = Field(default_factory=datetime.utcnow)


class ProceduralChain(BaseModel):
    """A reusable action chain learned from successful executions."""
    chain_id: str
    chain_name: str
    description: str
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    preconditions: Dict[str, Any] = Field(default_factory=dict)
    postconditions: Dict[str, Any] = Field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    avg_duration_ms: float = 0.0
    applicable_page_types: List[str] = Field(default_factory=list)
    applicable_workflow_states: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: datetime = Field(default_factory=datetime.utcnow)


class NavigationTransition(BaseModel):
    """A semantic navigation transition observed during a run."""
    navigation_type: str = "unknown"
    from_state: str = ""
    to_state: str = ""
    from_page_type: str = ""
    to_page_type: str = ""
    action_key: str = ""
    url_before: str = ""
    url_after: str = ""
    semantic_change: bool = False
    workflow_transition: bool = False
    confidence: float = 0.0
    summary: str = ""
    signals: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

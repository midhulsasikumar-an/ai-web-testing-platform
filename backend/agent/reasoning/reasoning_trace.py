"""
Reasoning trace engine — stores candidate actions, rejected actions,
planner rationale, confidence evolution, and reasoning chains.
Supports debugging, replay analysis, and future RL fine-tuning.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReasoningEvent(BaseModel):
    """A single reasoning event in the decision trace."""
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:10])
    event_type: str  # thought, evaluation, selection, rejection, replan
    step: int
    content: str
    evidence: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    skill_name: Optional[str] = None
    action_type: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class DecisionRecord(BaseModel):
    """Complete record of a single planning decision."""
    decision_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    step: int
    selected_action: Optional[str] = None
    selected_skill: Optional[str] = None
    confidence: float = 0.0
    candidate_count: int = 0
    rejected_actions: List[Dict[str, Any]] = Field(default_factory=list)
    reasoning_events: List[ReasoningEvent] = Field(default_factory=list)
    risk_score: float = 0.0
    replanning: bool = False
    replanning_cause: Optional[str] = None
    trajectory_score: float = 0.0
    token_usage: int = 0
    duration_ms: int = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ReasoningTraceEngine:
    """
    Records and manages the full reasoning trace for agent decisions.
    Provides replay, analysis, and RL-ready trajectory data.
    """

    def __init__(self) -> None:
        self._decisions: List[DecisionRecord] = []
        self._events: List[ReasoningEvent] = []
        self._confidence_history: List[tuple[int, float]] = []

    def start_decision(self, step: int) -> DecisionRecord:
        """Start recording a new planning decision."""
        record = DecisionRecord(step=step)
        self._decisions.append(record)
        return record

    def record_event(
        self, step: int, event_type: str, content: str,
        evidence: Optional[List[str]] = None, confidence: float = 0.0,
        skill_name: Optional[str] = None, action_type: Optional[str] = None,
    ) -> ReasoningEvent:
        event = ReasoningEvent(
            event_type=event_type, step=step, content=content,
            evidence=evidence or [], confidence=confidence,
            skill_name=skill_name, action_type=action_type,
        )
        self._events.append(event)
        if self._decisions and self._decisions[-1].step == step:
            self._decisions[-1].reasoning_events.append(event)
        return event

    def record_rejection(
        self, step: int, action_type: str, reason: str,
        skill_name: Optional[str] = None, score: float = 0.0,
    ) -> None:
        rejection = {
            "action_type": action_type, "reason": reason,
            "skill_name": skill_name, "score": score,
        }
        if self._decisions and self._decisions[-1].step == step:
            self._decisions[-1].rejected_actions.append(rejection)

    def finalize_decision(
        self, step: int, selected_action: str,
        selected_skill: Optional[str] = None,
        confidence: float = 0.0, risk_score: float = 0.0,
        candidate_count: int = 0, replanning: bool = False,
        replanning_cause: Optional[str] = None,
    ) -> None:
        if self._decisions and self._decisions[-1].step == step:
            d = self._decisions[-1]
            d.selected_action = selected_action
            d.selected_skill = selected_skill
            d.confidence = confidence
            d.risk_score = risk_score
            d.candidate_count = candidate_count
            d.replanning = replanning
            d.replanning_cause = replanning_cause
        self._confidence_history.append((step, confidence))

    def get_confidence_trend(self) -> List[tuple[int, float]]:
        return list(self._confidence_history)

    def get_decision(self, step: int) -> Optional[DecisionRecord]:
        for d in self._decisions:
            if d.step == step:
                return d
        return None

    def export_for_replay(self) -> List[Dict[str, Any]]:
        return [d.model_dump(mode="json") for d in self._decisions]

    def export_for_rl(self) -> List[Dict[str, Any]]:
        """Export reasoning data in RL-compatible format."""
        return [
            {
                "step": d.step,
                "action": d.selected_action,
                "skill": d.selected_skill,
                "confidence": d.confidence,
                "risk_score": d.risk_score,
                "candidates_evaluated": d.candidate_count,
                "rejections": len(d.rejected_actions),
                "replanning": d.replanning,
                "trajectory_score": d.trajectory_score,
            }
            for d in self._decisions
        ]

    @property
    def total_decisions(self) -> int:
        return len(self._decisions)

    @property
    def avg_confidence(self) -> float:
        if not self._confidence_history:
            return 0.0
        return sum(c for _, c in self._confidence_history) / len(self._confidence_history)

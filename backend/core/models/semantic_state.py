from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PageClassification(BaseModel):
    page_type: str
    confidence: float = 0.0
    signals: List[str] = Field(default_factory=list)
    semantic_state: str = ""
    detected_modules: List[str] = Field(default_factory=list)
    route_type: str = "unknown"
    auth_scores: Dict[str, float] = Field(default_factory=dict)


class ObservationDiff(BaseModel):
    state_changed: bool = False
    semantic_change: bool = False
    url_changed: bool = False
    title_changed: bool = False
    heading_changed: bool = False
    navigation_changed: bool = False
    table_changed: bool = False
    modal_changed: bool = False
    form_changed: bool = False
    workflow_transition_detected: bool = False
    confidence: float = 0.0
    summary: str = ""
    detected_changes: List[str] = Field(default_factory=list)
    fingerprint_changed: bool = False
    new_elements: List[str] = Field(default_factory=list)
    removed_elements: List[str] = Field(default_factory=list)
    visible_text_changed: bool = False


class NavigationTransition(BaseModel):
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


class GoalEvaluation(BaseModel):
    goal_completed: bool
    confidence: float = 0.0
    matched_conditions: List[str] = Field(default_factory=list)
    missing_conditions: List[str] = Field(default_factory=list)
    reasoning: List[str] = Field(default_factory=list)
    goal_name: str = ""
    semantic_state: str = ""

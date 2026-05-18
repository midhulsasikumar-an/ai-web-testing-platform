from __future__ import annotations

from datetime import datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field


class ExecutionSummary(BaseModel):
    success_rate: float
    pages_visited: int
    actions_executed: int
    recoveries_triggered: int
    duration_seconds: float


class WorkflowSummary(BaseModel):
    start_state: str
    end_state: str
    completed: bool


class DetectedIssue(BaseModel):
    step: Optional[int]
    issue_type: str
    severity: str
    description: str
    evidence: Dict[str, Any] = Field(default_factory=dict)


class FailureAnalysis(BaseModel):
    total_failures: int
    repeated_failures: int
    top_failure_types: List[Dict[str, Any]] = Field(default_factory=list)


class UXInsight(BaseModel):
    description: str
    severity: str


class PerformanceInsight(BaseModel):
    description: str
    avg_latency_seconds: Optional[float]


class SecurityInsight(BaseModel):
    description: str
    risk_level: str


class Recommendation(BaseModel):
    title: str
    detail: str
    impact: Optional[str]


class StepNarration(BaseModel):
    step: int
    action: str
    description: str
    status: str
    duration_seconds: Optional[float]
    screenshot: Optional[str] = None


class AIReadableReport(BaseModel):
    run_id: str
    status: str
    goal: Optional[str]
    summary: ExecutionSummary
    workflow: WorkflowSummary
    narrative: str
    authentication_strategy: str = ""
    authentication_result: str = ""
    authentication_confidence: float = 0.0
    authentication_reasoning: List[str] = Field(default_factory=list)
    semantic_navigation_summary: str = ""
    completed_goals: List[str] = Field(default_factory=list)
    failed_goals: List[str] = Field(default_factory=list)
    detected_modules: List[str] = Field(default_factory=list)
    user_journey: List[str] = Field(default_factory=list)
    interaction_narrative: str = ""
    issues: List[DetectedIssue] = Field(default_factory=list)
    failure_analysis: Optional[FailureAnalysis]
    # Structured QA additions
    authentication_summary: Dict[str, Any] = Field(default_factory=dict)
    detected_bugs: List[DetectedIssue] = Field(default_factory=list)
    visual_issues: List[UXInsight] = Field(default_factory=list)
    reproduction_paths: List[Dict[str, Any]] = Field(default_factory=list)
    ux_insights: List[UXInsight] = Field(default_factory=list)
    performance_insights: List[PerformanceInsight] = Field(default_factory=list)
    security_insights: List[SecurityInsight] = Field(default_factory=list)
    recommendations: List[Recommendation] = Field(default_factory=list)
    screenshots: List[Any] = Field(default_factory=list)
    execution_timeline: List[StepNarration] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

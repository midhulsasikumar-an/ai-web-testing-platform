from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class MultiAgentRole(str, Enum):
    AUTHENTICATION = "AuthenticationAgent"
    NAVIGATION = "NavigationAgent"
    ACCESSIBILITY = "AccessibilityAgent"
    PERFORMANCE = "PerformanceAgent"
    VISUAL_QA = "VisualQAAgent"


class MultiAgentRunRequest(BaseModel):
    url: HttpUrl
    goal: str
    credentials: Optional[Dict[str, str]] = None
    run_id: Optional[str] = None
    max_steps: int = Field(default=30, ge=1, le=200)
    enable_parallel: bool = True
    enable_auth_sharing: bool = True
    agent_names: List[str] = Field(default_factory=list)


class MultiAgentFinding(BaseModel):
    agent_name: str
    category: str
    severity: str
    message: str
    root_cause: Optional[str] = None
    url: Optional[str] = None
    workflow_state: Optional[str] = None
    confidence: float = 0.0
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AgentExecutionResult(BaseModel):
    agent_name: str
    status: str = "completed"
    confidence: float = 0.0
    summary: str = ""
    findings: List[MultiAgentFinding] = Field(default_factory=list)
    run: Dict[str, Any] = Field(default_factory=dict)
    report: Dict[str, Any] = Field(default_factory=dict)
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class UnifiedMultiAgentReport(BaseModel):
    report_id: Optional[str] = None
    run_id: str
    goal: str
    status: str
    agent_results: List[Dict[str, Any]] = Field(default_factory=list)
    consensus: Dict[str, Any] = Field(default_factory=dict)
    workflow_coverage: Dict[str, Any] = Field(default_factory=dict)
    navigation_graph: Dict[str, Any] = Field(default_factory=dict)
    shared_memory: Dict[str, Any] = Field(default_factory=dict)
    execution_map: Dict[str, Any] = Field(default_factory=dict)
    reproduction_paths: List[Dict[str, Any]] = Field(default_factory=list)
    severity_prioritization: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

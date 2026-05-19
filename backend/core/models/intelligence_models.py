from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BugLifecycleRecord(BaseModel):
    bug_id: str
    fingerprint: str
    title: str
    description: str = ""
    severity: str = "medium"
    status: str = "Monitoring"
    website: str = ""
    workflow_stage: str = "unknown"
    first_seen_run_id: str = ""
    last_seen_run_id: str = ""
    occurrences: int = 1
    regression_count: int = 0
    resolved_count: int = 0
    flaky_count: int = 0
    affected_components: List[str] = Field(default_factory=list)
    affected_urls: List[str] = Field(default_factory=list)
    screenshot_hashes: List[str] = Field(default_factory=list)
    history: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class BugLifecycleEvent(BaseModel):
    bug_id: str
    fingerprint: str
    status: str
    severity: str
    title: str
    workflow_stage: str = "unknown"
    run_id: str = ""
    report_id: str = ""
    url: str = ""
    screenshot_path: Optional[str] = None
    screenshot_hash: Optional[str] = None
    similarity_to_previous: Optional[float] = None
    evidence: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ComparisonScreenshotResult(BaseModel):
    baseline: Optional[str] = None
    candidate: Optional[str] = None
    similarity: float = 1.0
    difference: float = 0.0
    baseline_hash: Optional[str] = None
    candidate_hash: Optional[str] = None


class RunComparisonRequest(BaseModel):
    baseline_run_id: str
    comparison_run_id: str


class RunComparisonResult(BaseModel):
    comparison_id: str
    baseline_run_id: str
    comparison_run_id: str
    baseline_report_id: Optional[str] = None
    comparison_report_id: Optional[str] = None
    verdict: str = "unknown"
    summary: str = ""
    metrics_delta: Dict[str, Any] = Field(default_factory=dict)
    bug_delta: Dict[str, Any] = Field(default_factory=dict)
    screenshot_deltas: List[ComparisonScreenshotResult] = Field(default_factory=list)
    baseline: Dict[str, Any] = Field(default_factory=dict)
    comparison: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ExportRequest(BaseModel):
    format: str = "pdf"
    include_screenshots: bool = True
    include_comparison: bool = False
    comparison_run_id: Optional[str] = None
    title: Optional[str] = None


class ExportRecord(BaseModel):
    export_id: str
    report_id: str
    format: str
    file_path: str
    title: str
    include_screenshots: bool = True
    include_comparison: bool = False
    comparison_run_id: Optional[str] = None
    file_size_bytes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

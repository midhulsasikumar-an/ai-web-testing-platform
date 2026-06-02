from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class AIChatRequest(BaseModel):
    message: str


class AIPlanRequest(BaseModel):
    url: str
    instruction: str
    test_type: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


class AIPlanStep(BaseModel):
    action: str
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    feature_key: Optional[str] = None
    objective_id: Optional[str] = None
    objective_name: Optional[str] = None
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    coverage_level: Optional[str] = None
    coverage_profile: Optional[str] = None


class AIPlanTestCase(BaseModel):
    title: str
    expected: Optional[str] = None
    steps: List[AIPlanStep]
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    objective_id: Optional[str] = None
    objective_name: Optional[str] = None
    feature_key: Optional[str] = None
    coverage_level: Optional[str] = None
    coverage_profile: Optional[str] = None
    objective_tracking: Optional[List[Dict[str, Any]]] = None
    plan_metrics: Optional[Dict[str, Any]] = None
    scenario_tree: Optional[Dict[str, Any]] = None


class AIPlanResponse(BaseModel):
    url: str
    instruction: str
    parsed_credentials: Optional[Dict[str, Any]] = None
    instruction_context: Optional[Dict[str, Any]] = None
    page_title: Optional[str] = None
    summary: str
    source: str = "ai"
    discovery: Optional[Dict[str, Any]] = None
    discovery_status: Optional[str] = None
    discovery_error: Optional[str] = None
    test_case: AIPlanTestCase
    test_cases: List[AIPlanTestCase]
    raw_plan: Optional[Dict[str, Any]] = None
    requested_objectives: Optional[List[str]] = None
    planned_objectives: Optional[List[str]] = None
    feature_profiles: Optional[List[Dict[str, Any]]] = None
    objective_tracking: Optional[List[Dict[str, Any]]] = None
    plan_metrics: Optional[Dict[str, Any]] = None
    scenario_tree: Optional[Dict[str, Any]] = None
    risk_summary: Optional[Dict[str, Any]] = None
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class Step(BaseModel):
    action: str
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None
    feature_key: Optional[str] = None
    objective_id: Optional[str] = None
    objective_name: Optional[str] = None
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    scenario_category: Optional[str] = None
    coverage_level: Optional[str] = None
    coverage_profile: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    execution_context: Optional[Dict[str, Any]] = None


class TestCase(BaseModel):
    title: Optional[str] = None
    expected: Optional[str] = None
    steps: List[Step]
    objective_id: Optional[str] = None
    objective_name: Optional[str] = None
    feature_key: Optional[str] = None
    coverage_level: Optional[str] = None
    scenario_id: Optional[str] = None
    scenario_name: Optional[str] = None
    scenario_category: Optional[str] = None
    coverage_profile: Optional[str] = None
    risk_score: Optional[int] = None
    risk_level: Optional[str] = None
    objective_tracking: Optional[List[Dict[str, Any]]] = None
    plan_metrics: Optional[Dict[str, Any]] = None
    scenario_tree: Optional[Dict[str, Any]] = None
    depends_on: List[str] = Field(default_factory=list)
    required_state: List[str] = Field(default_factory=list)
    produces_state: List[str] = Field(default_factory=list)
    required_page: Optional[str] = None


class ExecuteRequest(BaseModel):
    url: str
    test_case: TestCase

class AutonomousRequest(BaseModel):
    url: str
    prompt: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None

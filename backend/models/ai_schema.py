from typing import Dict, List, Optional, Any
from pydantic import BaseModel

class AIChatRequest(BaseModel):
    message: str


class AIPlanRequest(BaseModel):
    url: str
    instruction: str
    test_type: Optional[str] = None


class AIPlanStep(BaseModel):
    action: str
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None


class AIPlanTestCase(BaseModel):
    title: str
    expected: Optional[str] = None
    steps: List[AIPlanStep]


class AIPlanResponse(BaseModel):
    url: str
    instruction: str
    page_title: Optional[str] = None
    summary: str
    source: str = "ai"
    test_case: AIPlanTestCase
    test_cases: List[AIPlanTestCase]
    raw_plan: Optional[Dict[str, Any]] = None
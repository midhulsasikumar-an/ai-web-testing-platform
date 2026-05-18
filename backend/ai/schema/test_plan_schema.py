from pydantic import BaseModel
from typing import Dict, List, Optional


class Step(BaseModel):
    action: str
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None


class TestCase(BaseModel):
    title: Optional[str] = None
    expected: Optional[str] = None
    steps: List[Step]


class ExecuteRequest(BaseModel):
    url: str
    test_case: TestCase

class AutonomousRequest(BaseModel):
    url: str
    prompt: Optional[str] = None
    credentials: Optional[Dict[str, str]] = None
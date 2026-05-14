from pydantic import BaseModel
from typing import List, Optional


class Step(BaseModel):
    action: str
    target: Optional[str] = None
    selector: Optional[str] = None
    value: Optional[str] = None


class TestCase(BaseModel):
    steps: List[Step]


class ExecuteRequest(BaseModel):
    url: str
    test_case: TestCase
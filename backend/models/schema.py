from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr

class TestRequest(BaseModel):
    url: str
    project_name: str
    test_type: str
    ai_plan: Optional[Dict[str, Any]] = None

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str
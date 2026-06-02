from typing import Any, Dict, Optional
from pydantic import BaseModel, EmailStr

class TestRequest(BaseModel):
    url: str
    test_name: Optional[str] = None
    goal: Optional[str] = None
    project_name: Optional[str] = None
    test_type: Optional[str] = None
    ai_plan: Optional[Dict[str, Any]] = None
    browser: Optional[str] = None
    device: Optional[str] = None
    coverage_level: Optional[str] = None
    execution_settings: Optional[Dict[str, Any]] = None

class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str
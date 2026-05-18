from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class AuthenticationStrategy(str, Enum):
    LOGIN_EXISTING_USER = "LOGIN_EXISTING_USER"
    CREATE_NEW_ACCOUNT = "CREATE_NEW_ACCOUNT"
    OAUTH_LOGIN = "OAUTH_LOGIN"
    MAGIC_LINK_LOGIN = "MAGIC_LINK_LOGIN"
    GUEST_ACCESS = "GUEST_ACCESS"
    UNKNOWN = "UNKNOWN"


class AuthenticationMode(str, Enum):
    LOGIN_PRIORITY_MODE = "LOGIN_PRIORITY_MODE"
    ACCOUNT_CREATION_MODE = "ACCOUNT_CREATION_MODE"
    GUEST_MODE = "GUEST_MODE"
    SKIP_AUTH_MODE = "SKIP_AUTH_MODE"


class AuthRouteType(str, Enum):
    LOGIN_PAGE = "login_page"
    SIGNUP_PAGE = "signup_page"
    OAUTH_PAGE = "oauth_page"
    FORGOT_PASSWORD_PAGE = "forgot_password_page"
    DASHBOARD_PAGE = "dashboard_page"
    LANDING_PAGE = "landing_page"
    AUTH_PAGE = "auth_page"
    UNKNOWN = "unknown"


class AuthRouteClassification(BaseModel):
    route_type: AuthRouteType = AuthRouteType.UNKNOWN
    confidence: float = 0.0
    login_score: float = 0.0
    signup_score: float = 0.0
    oauth_score: float = 0.0
    forgot_password_score: float = 0.0
    dashboard_score: float = 0.0
    landing_score: float = 0.0
    signals: List[str] = Field(default_factory=list)


class AuthenticationStrategyCandidate(BaseModel):
    strategy: AuthenticationStrategy
    confidence: float = 0.0
    reason: str = ""
    locked: bool = False


class AuthenticationStrategyPlan(BaseModel):
    strategy: AuthenticationStrategy = AuthenticationStrategy.UNKNOWN
    mode: AuthenticationMode = AuthenticationMode.GUEST_MODE
    route: AuthRouteClassification = Field(default_factory=AuthRouteClassification)
    confidence: float = 0.0
    candidates: List[AuthenticationStrategyCandidate] = Field(default_factory=list)
    locked: bool = False
    lock_reason: str = ""
    credentials_provided: bool = False
    auth_required: bool = False
    reasoning: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GeneratedAccountCredentials(BaseModel):
    email: str
    username: str
    password: str
    display_name: str = ""
    source: str = "generated"

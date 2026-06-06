from __future__ import annotations

"""
Unified workflow states, goal types, and failure taxonomy enums.

These are the canonical definitions — all other modules import from here.
"""

from enum import Enum


class ActionType(str, Enum):
    """All browser actions the agent can perform."""
    CLICK = "click"
    FILL = "fill"
    SUBMIT = "submit"
    SELECT = "select"
    SCROLL = "scroll"
    HOVER = "hover"
    WAIT = "wait"
    NAVIGATE = "navigate"
    BACK = "back"
    SCREENSHOT = "screenshot"
    DRAG = "drag"
    KEYBOARD = "keyboard"
    UPLOAD = "upload"
    EXTRACT = "extract"


class GoalType(str, Enum):
    """High-level objective categories the agent can pursue."""
    AUTHENTICATE_USER = "authenticate_user"
    NAVIGATE_DASHBOARD = "navigate_dashboard"
    SUBMIT_FORM = "submit_form"
    EXPLORE_NAVIGATION = "explore_navigation"
    VALIDATE_UI = "validate_ui"
    RUN_REGRESSION = "run_regression"
    VALIDATE_CHECKOUT = "validate_checkout"
    TEST_SEARCH = "test_search"
    VERIFY_PERMISSIONS = "verify_permissions"
    MULTI_STEP_WORKFLOW = "multi_step_workflow"
    CUSTOM = "custom"


class WorkflowState(str, Enum):
    """Finite-state-machine states for the agent execution workflow."""
    INIT = "INIT"
    LANDING_PAGE = "LANDING_PAGE"
    LOGIN_PAGE = "LOGIN_PAGE"
    SIGNUP_PAGE = "SIGNUP_PAGE"
    OAUTH_PAGE = "OAUTH_PAGE"
    FORGOT_PASSWORD_PAGE = "FORGOT_PASSWORD_PAGE"
    CREDENTIALS_FILLED = "CREDENTIALS_FILLED"
    AUTHENTICATED = "AUTHENTICATED"
    DASHBOARD = "DASHBOARD"
    DASHBOARD_HOME = "DASHBOARD_HOME"
    ADMIN_MODULE = "ADMIN_MODULE"
    USER_MANAGEMENT = "USER_MANAGEMENT"
    SETTINGS_PAGE = "SETTINGS_PAGE"
    TABLE_PAGE = "TABLE_PAGE"
    DETAIL_PAGE = "DETAIL_PAGE"
    LISTING_PAGE = "LISTING_PAGE"
    NAVIGATION_PAGE = "NAVIGATION_PAGE"
    LOADING_PAGE = "LOADING_PAGE"
    EMPTY_STATE_PAGE = "EMPTY_STATE_PAGE"
    FORM_PAGE = "FORM_PAGE"
    MODAL_PAGE = "MODAL_PAGE"
    TESTING = "TESTING"
    EXPLORING = "EXPLORING"
    FORM_INTERACTION = "FORM_INTERACTION"
    MODAL_HANDLING = "MODAL_HANDLING"
    ERROR = "ERROR"
    RECOVERY = "RECOVERY"
    REPLANNING = "REPLANNING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class FailureType(str, Enum):
    """Canonical failure taxonomy spanning all agent subsystems."""
    NONE = "none"
    POLICY_BLOCKED = "policy_blocked"
    INVALID_ACTION = "invalid_action"
    SELECTOR_NOT_FOUND = "selector_not_found"
    TIMEOUT = "timeout"
    DETACHED = "detached"
    NAVIGATION = "navigation"
    MODAL_BLOCKED = "modal_blocked"
    POPUP_BLOCKED = "popup_blocked"
    EXECUTION = "execution"
    OUTCOME_MISMATCH = "outcome_mismatch"
    LLM_PARSE_ERROR = "llm_parse_error"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    NETWORK_ERROR = "network_error"
    BROWSER_CRASH = "browser_crash"
    SESSION_EXPIRED = "session_expired"
    STAGNATION = "stagnation"
    LOOP_DETECTED = "loop_detected"
    SKILL_FAILURE = "skill_failure"
    OBJECTIVE_UNREACHABLE = "objective_unreachable"
    CONTEXT_OVERFLOW = "context_overflow"
    VISION_FAILURE = "vision_failure"
    UNKNOWN = "unknown"


class FailureSeverity(str, Enum):
    """How critical is this failure to the overall objective."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    FATAL = "fatal"


class RecoverabilityLevel(str, Enum):
    """Whether and how the agent can recover from this failure."""
    AUTO_RECOVERABLE = "auto_recoverable"
    RETRY_RECOVERABLE = "retry_recoverable"
    REPLAN_REQUIRED = "replan_required"
    SKILL_SWITCH_REQUIRED = "skill_switch_required"
    HUMAN_INTERVENTION = "human_intervention"
    UNRECOVERABLE = "unrecoverable"

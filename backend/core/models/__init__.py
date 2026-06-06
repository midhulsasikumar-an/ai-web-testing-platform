"""
Unified core models for the autonomous agent platform.

All Pydantic models, enums, and shared types live here to eliminate
duplication across agent/, services/, and models/ packages.
"""

from backend.core.models.actions import (
    ActionType,
    AgentAction,
    ActionResult,
    SelectorCandidate,
    BoundingBox,
    ExpectedOutcome,
)
from backend.core.models.observations import (
    ObservedElement,
    Observation,
    BrowserArtifact,
)
from backend.core.models.workflow import (
    WorkflowState,
    GoalType,
    FailureType,
)
from backend.core.models.planner import (
    PlannerDecision,
    ReasoningStep,
    CandidateAction,
    SkillSelection,
    RiskAssessment,
    MemoryReference,
    AgentReasoningOutput,
)
from backend.core.models.validation import (
    ValidationResult,
    ActionValidationResult,
)
from backend.core.models.memory import (
    MemoryEvent,
    EpisodicRecord,
    SemanticPattern,
    ProceduralChain,
    NavigationTransition,
)
from backend.core.models.auth import (
    AuthenticationStrategy,
    AuthenticationMode,
    AuthRouteType,
    AuthRouteClassification,
    AuthenticationStrategyCandidate,
    AuthenticationStrategyPlan,
    GeneratedAccountCredentials,
)
from backend.core.models.semantic_state import (
    PageClassification,
    ObservationDiff,
    GoalEvaluation,
)
from backend.core.models.agent_state import (
    AgentStep,
    AgentRunState,
    AgentRunRequest,
    AgentRunResponse,
    NavigationCandidate,
)
from backend.core.models.failures import (
    FailureSeverity,
    RecoverabilityLevel,
    RetryPolicy,
    AgentFailure,
    SelectorFailure,
    AuthFailure,
    NavigationFailure,
    TimeoutFailure,
    RecoveryFailure,
    PlannerFailure,
)

__all__ = [
    "ActionType", "AgentAction", "ActionResult", "SelectorCandidate",
    "BoundingBox", "ExpectedOutcome",
    "ObservedElement", "Observation", "BrowserArtifact",
    "WorkflowState", "GoalType", "FailureType",
    "PlannerDecision", "ReasoningStep", "CandidateAction",
    "SkillSelection", "RiskAssessment", "MemoryReference",
    "AgentReasoningOutput",
    "ValidationResult", "ActionValidationResult",
    "MemoryEvent", "EpisodicRecord", "SemanticPattern", "ProceduralChain",
    "NavigationTransition",
    "AuthenticationStrategy", "AuthenticationMode", "AuthRouteType",
    "AuthRouteClassification", "AuthenticationStrategyCandidate",
    "AuthenticationStrategyPlan", "GeneratedAccountCredentials",
    "PageClassification", "ObservationDiff", "GoalEvaluation",
    "AgentStep", "AgentRunState", "AgentRunRequest", "AgentRunResponse",
    "NavigationCandidate",
    "FailureSeverity", "RecoverabilityLevel", "RetryPolicy",
    "AgentFailure", "SelectorFailure", "AuthFailure",
    "NavigationFailure", "TimeoutFailure", "RecoveryFailure", "PlannerFailure",
]

from __future__ import annotations

from typing import Any, Dict

from backend.agent.memory_service import AgentMemory
from backend.core.models.observations import Observation
from backend.core.models.workflow import WorkflowState


class SuccessScoringService:
    def score(
        self,
        *,
        goal: str,
        memory: AgentMemory,
        workflow_state: WorkflowState,
        observation: Observation,
        coverage_summary: Dict[str, Any] | None = None,
        navigation_completion: Dict[str, Any] | None = None,
        stability_summary: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        authenticated = memory.authenticated or any(
            term in f"{observation.title} {observation.page_text} {observation.url}".lower()
            for term in ["dashboard", "logout", "my account", "profile"]
        )
        dashboard_reached = workflow_state in {
            WorkflowState.DASHBOARD,
            WorkflowState.DASHBOARD_HOME,
            WorkflowState.AUTHENTICATED,
            WorkflowState.ADMIN_MODULE,
            WorkflowState.USER_MANAGEMENT,
            WorkflowState.SETTINGS_PAGE,
        }
        completed_modules = len((navigation_completion or {}).get("completed_modules", []))
        coverage_score = float((coverage_summary or {}).get("coverage_score", 0.0) or 0.0)
        stability_score = 0.85 if not (stability_summary or {}).get("loading_indicators") else 0.65
        navigation_score = min(0.45 + (0.18 * completed_modules) + (0.18 if dashboard_reached else 0.0) + (0.12 if observation.breadcrumbs else 0.0), 0.99)
        authentication_score = min(0.5 + (0.35 if authenticated else 0.0) + (0.1 if dashboard_reached else 0.0) + (0.05 if any("logout" in element.label.lower() for element in observation.elements) else 0.0), 0.99)
        overall = round(
            min(
                0.99,
                authentication_score * 0.35 + navigation_score * 0.3 + stability_score * 0.2 + (coverage_score / 100.0) * 0.15,
            ),
            3,
        )
        confidence = "high" if overall >= 0.8 else "medium" if overall >= 0.6 else "low"
        return {
            "overall_score": overall,
            "authentication_score": round(authentication_score, 3),
            "navigation_score": round(navigation_score, 3),
            "stability_score": round(stability_score, 3),
            "coverage_score": round((coverage_score / 100.0) if coverage_score > 1 else coverage_score, 3),
            "confidence": confidence,
            "authenticated": authenticated,
            "dashboard_reached": dashboard_reached,
            "completed_modules": completed_modules,
            "success": authenticated and dashboard_reached and overall >= 0.65,
            "goal": goal,
        }

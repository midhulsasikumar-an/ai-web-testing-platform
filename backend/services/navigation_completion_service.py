from __future__ import annotations

from typing import Any, Dict, Optional

from backend.agent.memory_service import AgentMemory
from backend.core.models.observations import Observation
from backend.core.models.workflow import WorkflowState


class NavigationCompletionService:
    def __init__(self) -> None:
        self._completed: Dict[str, Dict[str, Dict[str, Any]]] = {}

    def update(
        self,
        run_id: str,
        memory: AgentMemory,
        observation: Observation,
        workflow_state: WorkflowState,
        semantic_state: str,
        *,
        reason: str = "",
    ) -> Dict[str, Any]:
        module = self._module_key(observation, workflow_state, semantic_state)
        completed = bool(module) and module not in {"login", "signup", "oauth", "forgot_password"}
        entry = {
            "module": module,
            "completed": completed,
            "locked": completed,
            "url": observation.url,
            "heading": observation.headings[0] if observation.headings else observation.title,
            "breadcrumb": " > ".join(observation.breadcrumbs),
            "workflow_state": workflow_state.value,
            "semantic_state": semantic_state,
            "reason": reason or "Semantic destination confirmed",
        }
        if completed:
            self._completed.setdefault(run_id, {})[module] = entry
            memory.mark_module_completed(
                module,
                url=observation.url,
                heading=entry["heading"],
                breadcrumb=entry["breadcrumb"],
                workflow_state=workflow_state.value,
                semantic_state=semantic_state,
                reason=entry["reason"],
            )
        return entry | {"completed_modules": list(self._completed.get(run_id, {}).values())}

    def summary(self, run_id: str) -> Dict[str, Any]:
        completed = list(self._completed.get(run_id, {}).values())
        return {
            "completed_modules": completed,
            "locked_routes": [item.get("url") for item in completed if item.get("url")],
            "completion_count": len(completed),
        }

    @staticmethod
    def _module_key(observation: Observation, workflow_state: WorkflowState, semantic_state: str) -> str:
        sidebar = (observation.active_sidebar_item or "").lower()
        breadcrumbs = " ".join(observation.breadcrumbs).lower()
        text = f"{observation.url} {observation.title} {' '.join(observation.headings)} {sidebar} {breadcrumbs} {semantic_state}".lower()
        if any(term in text for term in ["admin", "system users", "user management"]):
            return "admin"
        if any(term in text for term in ["dashboard", "home"]):
            return "dashboard"
        if any(term in text for term in ["settings", "configuration", "preferences"]):
            return "settings"
        if any(term in text for term in ["profile", "account"]):
            return "profile"
        if workflow_state == WorkflowState.LOGIN_PAGE:
            return "login"
        if workflow_state == WorkflowState.SIGNUP_PAGE:
            return "signup"
        if semantic_state:
            return semantic_state.replace("_page", "").replace("_module", "")
        return ""

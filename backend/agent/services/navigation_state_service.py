from __future__ import annotations

from backend.core.models.actions import AgentAction
from backend.core.models.observations import Observation
from backend.core.models.semantic_state import NavigationTransition, ObservationDiff, PageClassification
from backend.core.models.auth import AuthRouteType
from backend.core.models.workflow import WorkflowState


class NavigationStateService:
    def classify_state(
        self,
        observation: Observation,
        page_classification: PageClassification,
        authenticated: bool = False,
    ) -> str:
        if page_classification.semantic_state:
            return page_classification.semantic_state
        page_type = page_classification.page_type
        if page_type in {"dashboard_home", "dashboard"}:
            return "dashboard_home"
        if page_type in {"admin_module", "user_management", "settings_page", "table_page", "listing_page", "detail_page", "form_page", "modal_page", "loading_page", "empty_state_page"}:
            return page_type
        route_type = page_classification.route_type if hasattr(page_classification, "route_type") else "unknown"
        if route_type == AuthRouteType.LOGIN_PAGE.value:
            return "login_page"
        if route_type == AuthRouteType.SIGNUP_PAGE.value:
            return "signup_page"
        if route_type == AuthRouteType.OAUTH_PAGE.value:
            return "oauth_page"
        if route_type == AuthRouteType.FORGOT_PASSWORD_PAGE.value:
            return "forgot_password_page"
        if route_type == AuthRouteType.DASHBOARD_PAGE.value:
            return "dashboard_home"
        if route_type == AuthRouteType.LANDING_PAGE.value:
            return "landing_page"
        if authenticated:
            return "dashboard_home"
        text = f"{observation.title} {' '.join(observation.headings)} {observation.page_text}".lower()
        if any(term in text for term in ["admin", "user management", "system users"]):
            return "admin_module"
        if any(term in text for term in ["settings", "preferences", "configuration"]):
            return "settings_page"
        if any(term in text for term in ["table", "rows", "pagination", "search", "filter"]):
            return "listing_page"
        if observation.forms:
            return "form_page"
        return page_type or "generic_page"

    def resolve_workflow_state(
        self,
        current_state: WorkflowState,
        observation: Observation,
        page_classification: PageClassification,
        authenticated: bool = False,
    ) -> WorkflowState:
        semantic_state = self.classify_state(observation, page_classification, authenticated)
        if semantic_state == "login_page":
            return WorkflowState.LOGIN_PAGE
        if semantic_state == "signup_page":
            return WorkflowState.SIGNUP_PAGE
        if semantic_state == "oauth_page":
            return WorkflowState.OAUTH_PAGE
        if semantic_state == "forgot_password_page":
            return WorkflowState.FORGOT_PASSWORD_PAGE
        if semantic_state == "dashboard_home":
            return WorkflowState.DASHBOARD_HOME
        if semantic_state == "admin_module":
            return WorkflowState.ADMIN_MODULE
        if semantic_state == "user_management":
            return WorkflowState.USER_MANAGEMENT
        if semantic_state == "settings_page":
            return WorkflowState.SETTINGS_PAGE
        if semantic_state == "table_page":
            return WorkflowState.TABLE_PAGE
        if semantic_state == "listing_page":
            return WorkflowState.LISTING_PAGE
        if semantic_state == "detail_page":
            return WorkflowState.DETAIL_PAGE
        if semantic_state == "form_page":
            return WorkflowState.FORM_PAGE
        if semantic_state == "modal_page":
            return WorkflowState.MODAL_PAGE
        if semantic_state == "loading_page":
            return WorkflowState.LOADING_PAGE
        if semantic_state == "empty_state_page":
            return WorkflowState.EMPTY_STATE_PAGE
        if authenticated:
            return WorkflowState.AUTHENTICATED if current_state != WorkflowState.DASHBOARD else WorkflowState.DASHBOARD
        if current_state == WorkflowState.INIT:
            return WorkflowState.LANDING_PAGE
        return current_state

    def detect_transition(
        self,
        before: Observation,
        after: Observation,
        action: AgentAction | None,
        before_classification: PageClassification,
        after_classification: PageClassification,
        workflow_before: WorkflowState,
        workflow_after: WorkflowState,
    ) -> NavigationTransition:
        from_state = self.classify_state(before, before_classification, authenticated=workflow_before in {WorkflowState.AUTHENTICATED, WorkflowState.DASHBOARD, WorkflowState.DASHBOARD_HOME})
        to_state = self.classify_state(after, after_classification, authenticated=workflow_after in {WorkflowState.AUTHENTICATED, WorkflowState.DASHBOARD, WorkflowState.DASHBOARD_HOME})
        navigation_type = self._navigation_type(action, before_classification, after_classification, before, after)
        semantic_change = from_state != to_state or before_classification.page_type != after_classification.page_type
        workflow_transition = workflow_before != workflow_after
        confidence = self._confidence(before, after, semantic_change, workflow_transition, navigation_type)
        signals = [
            f"{before_classification.page_type} -> {after_classification.page_type}",
            f"{from_state} -> {to_state}",
        ]
        if navigation_type != "unknown":
            signals.append(navigation_type)
        summary = self._summary(action, navigation_type, from_state, to_state, semantic_change, workflow_transition)
        return NavigationTransition(
            navigation_type=navigation_type,
            from_state=from_state,
            to_state=to_state,
            from_page_type=before_classification.page_type,
            to_page_type=after_classification.page_type,
            action_key=self._action_key(action),
            url_before=before.url,
            url_after=after.url,
            semantic_change=semantic_change,
            workflow_transition=workflow_transition,
            confidence=confidence,
            summary=summary,
            signals=signals,
            metadata={"before_title": before.title, "after_title": after.title},
        )

    @staticmethod
    def _action_key(action: AgentAction | None) -> str:
        if not action:
            return "observe"
        return f"{action.action.value}:{action.target or action.selector or action.value or action.url or ''}"

    @staticmethod
    def _navigation_type(
        action: AgentAction | None,
        before_classification: PageClassification,
        after_classification: PageClassification,
        before: Observation,
        after: Observation,
    ) -> str:
        action_text = " ".join(filter(None, [action.target if action else None, action.selector if action else None, action.value if action else None, action.url if action else None])).lower()
        before_text = f"{before.title} {' '.join(before.headings)} {before.page_text}".lower()
        after_text = f"{after.title} {' '.join(after.headings)} {after.page_text}".lower()

        if any(term in action_text for term in ["sidebar", "menu", "nav", "admin", "users", "settings"]):
            return "sidebar_transition"
        if any(term in action_text for term in ["tab"]):
            return "tab_transition"
        if any(term in action_text for term in ["modal", "dialog", "popup", "overlay"]):
            return "modal_transition"
        if any(term in action_text for term in ["page", "next", "previous", "pagination"]):
            return "pagination_transition"
        if any(term in before_text for term in ["dashboard", "home"] ) and any(term in after_text for term in ["admin", "users", "settings"]):
            return "module_transition"
        if before_classification.page_type != after_classification.page_type:
            return "page_transition"
        return "unknown"

    @staticmethod
    def _confidence(before: Observation, after: Observation, semantic_change: bool, workflow_transition: bool, navigation_type: str) -> float:
        score = 0.0
        if semantic_change:
            score += 0.45
        if workflow_transition:
            score += 0.25
        if before.url != after.url:
            score += 0.12
        if before.title != after.title:
            score += 0.08
        if navigation_type != "unknown":
            score += 0.1
        return min(score, 0.99)

    @staticmethod
    def _summary(
        action: AgentAction | None,
        navigation_type: str,
        from_state: str,
        to_state: str,
        semantic_change: bool,
        workflow_transition: bool,
    ) -> str:
        if action and navigation_type == "sidebar_transition":
            return f"Opened {to_state.replace('_', ' ')} from {from_state.replace('_', ' ')} via sidebar navigation."
        if action and navigation_type == "tab_transition":
            return f"Switched tabs into {to_state.replace('_', ' ')}."
        if action and navigation_type == "modal_transition":
            return f"Opened modal flow in {to_state.replace('_', ' ')}."
        if semantic_change or workflow_transition:
            return f"Transitioned from {from_state.replace('_', ' ')} to {to_state.replace('_', ' ')}."
        return "No semantic navigation change detected."

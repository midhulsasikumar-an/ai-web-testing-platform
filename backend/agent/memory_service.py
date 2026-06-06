from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from backend.core.models.actions import ActionResult, AgentAction
from backend.core.models.planner import NavigationCandidate
from backend.core.models.observations import Observation
from backend.core.models.memory import MemoryEvent, NavigationTransition
from backend.agent.selector_engine import SelectorMemory


class AgentMemory:
    """Layered in-run memory for navigation, selectors, failures, and task progress."""

    def __init__(self, goal: str = ""):
        self.goal = goal
        self.events: List[MemoryEvent] = []
        self.observations: List[Observation] = []
        self.actions: List[AgentAction] = []
        self.results: List[ActionResult] = []
        self.visited_sequence: List[str] = []
        self.visited_urls: set[str] = set()
        self.page_fingerprints: Counter[str] = Counter()
        self.failure_patterns: Counter[str] = Counter()
        self.selector_memory = SelectorMemory()
        self.frontier: List[NavigationCandidate] = []
        self.discovered_pages: Dict[str, str] = {}
        self.successful_flows: List[str] = []
        self.authenticated: bool = False
        self.recent_action_keys: deque[str] = deque(maxlen=8)
        self.semantic_state_history: deque[str] = deque(maxlen=20)
        self.workflow_state_history: deque[str] = deque(maxlen=20)
        self.navigation_transitions: List[NavigationTransition] = []
        self.successful_transitions: List[NavigationTransition] = []
        self.failed_transitions: List[NavigationTransition] = []
        self.completed_goals: List[str] = []
        self.failed_goals: List[str] = []
        self.module_traversal_history: List[str] = []
        self.navigation_graph: Dict[str, Dict[str, int]] = defaultdict(dict)
        self.visited_semantic_states: set[str] = set()
        self._last_observed_state: str = ""
        # Authentication tracking
        self.attempted_logins: List[Dict] = []
        self.attempted_signups: List[Dict] = []
        self.auth_redirects: List[Dict] = []
        self.created_accounts: List[Dict] = []
        self.session_cookies: List[Dict] = []
        self.failed_auth_attempts: int = 0
        self.logout_successes: int = 0
        self.completed_modules: Dict[str, Dict[str, Any]] = {}
        self.locked_routes: set[str] = set()

    def remember_observation(self, observation: Observation, step: int) -> None:
        self.observations.append(observation)
        self.visited_sequence.append(observation.url)
        self.visited_urls.add(observation.url)
        self.page_fingerprints[observation.fingerprint] += 1
        self.discovered_pages.setdefault(observation.url, observation.title)
        if observation.page_type:
            self.semantic_state_history.append(observation.page_type)
            self.workflow_state_history.append(observation.page_type)
            self.visited_semantic_states.add(observation.page_type)
        if observation.page_type in {"dashboard", "dashboard_home", "dashboard_page", "admin_module", "user_management", "settings_page"}:
            self.authenticated = True
        self._last_observed_state = observation.page_type
        self.add_event(
            "observation",
            f"Observed {observation.page_type} at {observation.url}",
            step,
            {
                "fingerprint": observation.fingerprint,
                "elements": len(observation.elements),
            },
        )

    def remember_action(self, action: AgentAction, step: int) -> None:
        self.actions.append(action)
        self.recent_action_keys.append(self.action_key(action))
        self.add_event(
            "action",
            f"{action.action.value}: {action.target or action.element_index or action.url or ''}",
            step,
            {"confidence": action.confidence, "reason": action.reason},
        )

    def remember_result(self, result: ActionResult, step: int) -> None:
        self.results.append(result)
        if result.selector_used:
            if result.success:
                self.selector_memory.record_success(result.selector_used)
            else:
                self.selector_memory.record_failure(result.selector_used)
        if result.success:
            self.successful_flows.append(result.action.reason or result.action.action.value)
        else:
            key = f"{result.failure_type.value}:{result.action.action.value}:{result.action.target or result.action.element_index}"
            self.failure_patterns[key] += 1
        self.add_event(
            "execution",
            "Action passed" if result.success else f"Action failed: {result.failure_type.value}",
            step,
            {
                "selector": result.selector_used,
                "error": result.error,
                "duration_ms": result.duration_ms,
                "retries": result.retries,
            },
        )

    def remember_transition(self, transition: NavigationTransition) -> None:
        self.navigation_transitions.append(transition)
        if transition.to_state:
            self.semantic_state_history.append(transition.to_state)
            self.workflow_state_history.append(transition.to_state)
            self.visited_semantic_states.add(transition.to_state)
            self.module_traversal_history.append(transition.to_state)
        if transition.workflow_transition or transition.semantic_change:
            self.successful_transitions.append(transition)
        else:
            self.failed_transitions.append(transition)
        if transition.from_state:
            self.navigation_graph.setdefault(transition.from_state, {})
            self.navigation_graph[transition.from_state][transition.to_state] = (
                self.navigation_graph[transition.from_state].get(transition.to_state, 0) + 1
            )
        self.add_event(
            "navigation",
            transition.summary,
            step=len(self.events),
            metadata=transition.model_dump(mode="json"),
        )

    def remember_goal_completion(self, goal_name: str, completed: bool, confidence: float) -> None:
        if completed:
            if goal_name not in self.completed_goals:
                self.completed_goals.append(goal_name)
        self.add_event(
            "goal",
            f"Goal {'completed' if completed else 'in progress'}: {goal_name}",
            step=len(self.events),
            metadata={"goal": goal_name, "completed": completed, "confidence": confidence},
        )

    def update_frontier(self, candidates: List[NavigationCandidate]) -> None:
        known = {candidate.url: candidate for candidate in self.frontier}
        for candidate in candidates:
            existing = known.get(candidate.url)
            if existing is None or candidate.score > existing.score:
                known[candidate.url] = candidate
        self.frontier = sorted(
            known.values(),
            key=lambda item: (item.visited, -item.score, item.depth),
        )[:200]

    def mark_frontier_visited(self, url: str) -> None:
        for candidate in self.frontier:
            if candidate.url == url:
                candidate.visited = True

    def next_frontier_url(self) -> Optional[str]:
        for candidate in self.frontier:
            if not candidate.visited and candidate.url not in self.visited_urls:
                return candidate.url
        return None

    def repeated_action_count(self, action: AgentAction) -> int:
        key = self.action_key(action)
        return sum(1 for item in self.recent_action_keys if item == key)

    def repeated_failure_count(self, action: AgentAction) -> int:
        prefix = f":{action.action.value}:{action.target or action.element_index}"
        return sum(count for key, count in self.failure_patterns.items() if key.endswith(prefix))

    def detects_loop(
        self,
        semantic_change: bool = False,
        transition: NavigationTransition | None = None,
        goal_completed: bool = False,
        diff_changed: bool = False,
    ) -> bool:
        if goal_completed or semantic_change or diff_changed:
            return False
        if transition and transition.semantic_change and transition.workflow_transition:
            return False
        if len(self.visited_sequence) >= 6:
            recent_urls = self.visited_sequence[-6:]
            if len(set(recent_urls)) <= 2:
                recent_semantic = list(self.semantic_state_history)[-4:]
                if not recent_semantic or len(set(recent_semantic)) <= 1:
                    return True
        if self.observations:
            fingerprint = self.observations[-1].fingerprint
            if self.page_fingerprints[fingerprint] >= 4 and not self.semantic_state_history:
                return True
        if len(self.recent_action_keys) == self.recent_action_keys.maxlen:
            repeated_actions = len(set(self.recent_action_keys)) <= 2
            recent_semantic = list(self.semantic_state_history)[-4:]
            if repeated_actions and len(set(recent_semantic)) <= 1:
                return True
        return False

    def compact_for_llm(self) -> Dict:
        last_failures = [
            {
                "action": result.action.action.value,
                "target": result.action.target,
                "element_index": result.action.element_index,
                "failure_type": result.failure_type.value,
                "error": result.error,
            }
            for result in self.results[-8:]
            if not result.success
        ]
        return {
            "goal": self.goal,
            "visited_count": len(self.visited_urls),
            "recent_urls": self.visited_sequence[-8:],
            "authenticated": self.authenticated,
            "frontier": [
                candidate.model_dump(mode="json")
                for candidate in self.frontier[:10]
                if not candidate.visited
            ],
            "recent_failures": last_failures,
            "successful_intents": self.successful_flows[-10:],
            "loop_risk": self.detects_loop(),
            "visited_semantic_states": list(self.visited_semantic_states),
            "completed_goals": self.completed_goals[-20:],
            "failed_goals": self.failed_goals[-20:],
            "module_traversal_history": self.module_traversal_history[-20:],
            "navigation_graph": self.navigation_graph,
            "successful_transitions": [transition.model_dump(mode="json") for transition in self.successful_transitions[-20:]],
            "auth_summary": {
                "attempted_logins": self.attempted_logins[-8:],
                "attempted_signups": self.attempted_signups[-8:],
                "created_accounts": self.created_accounts[-4:],
                "failed_auth_attempts": self.failed_auth_attempts,
                "logout_successes": self.logout_successes,
            },
            "completed_modules": list(self.completed_modules.values())[-20:],
            "locked_routes": sorted(self.locked_routes)[-50:],
        }

    # Authentication tracking helpers
    def remember_auth_attempt(self, attempt: Dict) -> None:
        """Record an authentication attempt. attempt should include type ('login'|'signup'), success boolean, credentials (optional), and step."""
        if attempt.get("type") == "login":
            self.attempted_logins.append(attempt)
            if not attempt.get("success"):
                self.failed_auth_attempts += 1
        elif attempt.get("type") == "signup":
            self.attempted_signups.append(attempt)
            if not attempt.get("success"):
                self.failed_auth_attempts += 1

    def remember_account_created(self, account: Dict) -> None:
        self.created_accounts.append(account)

    def record_auth_redirect(self, redirect: Dict) -> None:
        self.auth_redirects.append(redirect)

    def store_session_cookie(self, cookie: Dict) -> None:
        self.session_cookies.append(cookie)

    def remember_logout(self, success: bool, step: int) -> None:
        if success:
            self.logout_successes += 1
        self.add_event("auth", f"logout {'succeeded' if success else 'failed'}", step, {"success": success})

    def mark_module_completed(self, module: str, *, url: str = "", heading: str = "", breadcrumb: str = "", workflow_state: str = "", semantic_state: str = "", reason: str = "") -> None:
        if not module:
            return
        key = self._normalize_module_key(module)
        self.completed_modules[key] = {
            "module": key,
            "url": url,
            "heading": heading,
            "breadcrumb": breadcrumb,
            "workflow_state": workflow_state,
            "semantic_state": semantic_state,
            "reason": reason,
            "completed": True,
            "locked": True,
        }
        if url:
            self.locked_routes.add(self._normalize_url(url))

    def module_locked(self, module: str) -> bool:
        return self._normalize_module_key(module) in self.completed_modules

    def route_locked(self, url: str) -> bool:
        return self._normalize_url(url) in self.locked_routes

    def is_locked_target(self, url: str = "", target: str = "", selector: str = "") -> bool:
        normalized = " ".join(part for part in [url, target, selector] if part).lower()
        if not normalized:
            return False
        if url and self.route_locked(url):
            return True
        for module in self.completed_modules.values():
            module_name = str(module.get("module", "")).lower()
            if module_name and module_name in normalized:
                return True
            heading = str(module.get("heading") or "").lower()
            breadcrumb = str(module.get("breadcrumb") or "").lower()
            if heading and heading in normalized:
                return True
            if breadcrumb and breadcrumb in normalized:
                return True
        return False

    def add_event(self, event_type: str, message: str, step: int, metadata: Optional[Dict] = None) -> None:
        self.events.append(
            MemoryEvent(
                event_type=event_type,  # type: ignore[arg-type]
                message=message,
                step=step,
                metadata=metadata or {},
            )
        )

    @staticmethod
    def action_key(action: AgentAction) -> str:
        return "|".join(
            [
                action.action.value,
                str(action.element_index or ""),
                action.target or "",
                action.value or "",
                action.url or "",
            ]
        )

    @staticmethod
    def url_depth(url: str) -> int:
        parsed = urlparse(url)
        return len([part for part in parsed.path.split("/") if part])

    @staticmethod
    def _normalize_module_key(value: str) -> str:
        normalized = (value or "").strip().lower().replace("/", " ")
        for token in ["module", "page", "section", "screen", "route"]:
            normalized = normalized.replace(token, "")
        return " ".join(normalized.split())

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url or "")
        path = "/".join(part for part in parsed.path.lower().split("/") if part)
        return f"{parsed.netloc.lower()}/{path}" if parsed.netloc else path

from __future__ import annotations

from urllib.parse import urljoin, urlparse

from backend.agent.memory_service import AgentMemory
from backend.agent.safety import SafetyPolicy
from backend.core.models.agent_state import NavigationCandidate
from backend.core.models.observations import Observation


HIGH_VALUE_TERMS = {
    "dashboard": 18,
    "admin": 16,
    "login": 15,
    "sign in": 15,
    "profile": 12,
    "settings": 12,
    "account": 12,
    "users": 10,
    "reports": 10,
    "analytics": 10,
    "orders": 9,
    "products": 9,
    "create": 8,
    "new": 7,
    "edit": 7,
    "form": 6,
}

LOW_VALUE_TERMS = {
    "logout": -50,
    "delete": -50,
    "remove": -40,
    "privacy": -8,
    "terms": -8,
    "twitter": -12,
    "facebook": -12,
    "linkedin": -12,
}


class NavigationEngine:
    def __init__(self, safety_policy: SafetyPolicy):
        self.safety_policy = safety_policy

    def discover(self, observation: Observation, memory: AgentMemory) -> list[NavigationCandidate]:
        candidates: list[NavigationCandidate] = []
        for element in observation.links:
            if not element.href:
                continue
            target_url = urljoin(observation.url, element.href)
            safety = self.safety_policy.validate_navigation(observation.url, target_url)
            if not safety.valid:
                continue
            candidate = NavigationCandidate(
                url=target_url,
                text=element.label,
                source_element_index=element.index,
                depth=AgentMemory.url_depth(target_url),
                visited=target_url in memory.visited_urls,
            )
            candidate.score = self._score(candidate, observation, memory)
            candidate.reason = self._reason(candidate)
            candidates.append(candidate)

        candidates.sort(key=lambda item: item.score, reverse=True)
        return candidates[:50]

    def best_candidate(self, observation: Observation, memory: AgentMemory) -> NavigationCandidate | None:
        self.discover_and_update(observation, memory)
        for candidate in memory.frontier:
            if not candidate.visited and candidate.url not in memory.visited_urls:
                return candidate
        return None

    def discover_and_update(self, observation: Observation, memory: AgentMemory) -> None:
        memory.update_frontier(self.discover(observation, memory))

    def _score(self, candidate: NavigationCandidate, observation: Observation, memory: AgentMemory) -> float:
        parsed = urlparse(candidate.url)
        haystack = f"{candidate.text} {parsed.path} {parsed.query}".lower()
        score = 0.0

        for term, value in HIGH_VALUE_TERMS.items():
            if term in haystack:
                score += value

        for term, value in LOW_VALUE_TERMS.items():
            if term in haystack:
                score += value

        goal_terms = [
            term
            for term in memory.goal.lower().replace("/", " ").replace("-", " ").split()
            if len(term) > 3
        ]
        score += sum(8 for term in goal_terms if term in haystack)

        if candidate.url not in memory.visited_urls:
            score += 12
        else:
            score -= 20

        if observation.page_type == "login_page" and any(term in haystack for term in ["dashboard", "account"]):
            score += 8

        score -= min(candidate.depth, 8) * 1.5
        if parsed.fragment:
            score -= 3
        if parsed.query:
            score -= 1

        return score

    @staticmethod
    def _reason(candidate: NavigationCandidate) -> str:
        if candidate.visited:
            return "known URL; deprioritized"
        if candidate.score >= 20:
            return "high semantic relevance and novelty"
        if candidate.score >= 8:
            return "moderate relevance and safe to explore"
        return "low relevance but available as frontier"

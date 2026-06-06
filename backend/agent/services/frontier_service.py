from __future__ import annotations

from urllib.parse import urljoin, urlparse

from pydantic import BaseModel, Field

from backend.core.models.agent_state import NavigationCandidate
from backend.core.models.observations import Observation
from backend.agent.safety import SafetyPolicy


class FrontierState(BaseModel):
    visited_states: set[str] = Field(default_factory=set)
    discovered_routes: dict[str, NavigationCandidate] = Field(default_factory=dict)
    action_paths: dict[str, list[str]] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class FrontierService:
    def __init__(self, safety_policy: SafetyPolicy):
        self.safety_policy = safety_policy
        self.state = FrontierState()

    def update(self, observation: Observation, goal_terms: list[str]) -> list[NavigationCandidate]:
        self.state.visited_states.add(observation.fingerprint)
        candidates: list[NavigationCandidate] = []
        for element in observation.links:
            if not element.href:
                continue
            target_url = urljoin(observation.url, element.href)
            if not self.safety_policy.validate_navigation(observation.url, target_url).valid:
                continue
            candidate = NavigationCandidate(
                url=target_url,
                text=element.label,
                source_element_index=element.index,
                depth=self._depth(target_url),
                visited=False,
            )
            candidate.score = self.score(candidate, goal_terms)
            candidate.reason = "goal/novelty frontier score"
            existing = self.state.discovered_routes.get(target_url)
            if existing is None or candidate.score > existing.score:
                self.state.discovered_routes[target_url] = candidate
            candidates.append(candidate)
        return sorted(candidates, key=lambda item: item.score, reverse=True)

    def next(self, visited_urls: set[str]) -> NavigationCandidate | None:
        candidates = [
            item
            for item in self.state.discovered_routes.values()
            if item.url not in visited_urls and not item.visited
        ]
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (-item.score, item.depth))[0]

    def mark_visited(self, url: str) -> None:
        if url in self.state.discovered_routes:
            self.state.discovered_routes[url].visited = True

    @staticmethod
    def score(candidate: NavigationCandidate, goal_terms: list[str]) -> float:
        parsed = urlparse(candidate.url)
        text = f"{candidate.text} {parsed.path}".lower()
        score = 10.0
        score += sum(8 for term in goal_terms if term and term in text)
        if any(term in text for term in ["dashboard", "settings", "profile", "admin", "reports"]):
            score += 12
        if any(term in text for term in ["logout", "delete", "remove", "privacy", "terms"]):
            score -= 25
        score -= min(candidate.depth, 8)
        return score

    @staticmethod
    def _depth(url: str) -> int:
        return len([part for part in urlparse(url).path.split("/") if part])

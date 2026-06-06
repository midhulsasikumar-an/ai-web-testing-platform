from __future__ import annotations

from typing import Any, Dict, List

from backend.agent.memory_service import AgentMemory
from backend.core.models.observations import Observation


class CoverageExpansionService:
    def summarize(self, memory: AgentMemory, observation: Observation) -> Dict[str, Any]:
        modules = list(dict.fromkeys(memory.module_traversal_history + [item.get("module", "") for item in memory.completed_modules.values() if isinstance(memory.completed_modules, dict)]))
        visible_links = [element.label for element in observation.links if element.visible and element.label]
        unexplored = [link for link in visible_links if not memory.is_locked_target(target=link)]
        routes = []
        for candidate in memory.frontier[:12]:
            if not candidate.visited and not memory.is_locked_target(candidate.url, candidate.text, ""):
                routes.append({
                    "url": candidate.url,
                    "text": candidate.text,
                    "score": candidate.score,
                    "depth": candidate.depth,
                })
        explored_forms = len(observation.forms)
        explored_tables = len(observation.visible_tables)
        explored_cards = len(observation.visible_cards)
        explored_dialogs = len(observation.dialogs)
        coverage_score = min(100.0, 40.0 + len(modules) * 7.0 + len(routes) * 3.0 + (8.0 if memory.authenticated else 0.0))
        return {
            "coverage_score": round(coverage_score, 2),
            "visited_modules": modules[-20:],
            "explored_routes": routes,
            "explored_forms": explored_forms,
            "explored_tables": explored_tables,
            "explored_cards": explored_cards,
            "explored_dialogs": explored_dialogs,
            "unexplored_visible_routes": unexplored[:12],
            "exploration_hint": self._hint(routes, unexplored, memory.authenticated),
        }

    @staticmethod
    def _hint(routes: List[Dict[str, Any]], unexplored: List[str], authenticated: bool) -> str:
        if routes:
            best = routes[0]
            return f"Expand into {best['text'] or best['url']} after the main goal is complete."
        if authenticated and unexplored:
            return f"Explore {unexplored[0]} and nearby authenticated sections next."
        if authenticated:
            return "Continue coverage by opening meaningful sidebar modules and inspecting visible tables or forms."
        return "Coverage expansion should wait until the primary workflow reaches a stable authenticated state."

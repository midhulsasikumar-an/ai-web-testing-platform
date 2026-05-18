"""
Skill initializer — registers all default skills at startup.
"""

from backend.agent.skill_engine.skill_registry import SkillRegistry
from backend.agent.skills.authenticate import AuthenticateSkill
from backend.agent.skills.dismiss_modal import DismissModalSkill
from backend.agent.skills.complete_form import CompleteFormSkill
from backend.agent.skills.navigate_sidebar import NavigateSidebarSkill
from backend.agent.skills.search_site import SearchSiteSkill
from backend.agent.skills.resolve_overlay import ResolveOverlaySkill
from backend.agent.skills.recover_navigation import RecoverNavigationSkill
from backend.agent.skills.detect_dashboard import (
    DetectDashboardSkill, ValidatePageSkill, PaginationSkill,
)


def create_skill_registry() -> SkillRegistry:
    """Create and populate a skill registry with all default skills."""
    registry = SkillRegistry()
    for skill_cls in [
        AuthenticateSkill,
        DismissModalSkill,
        CompleteFormSkill,
        NavigateSidebarSkill,
        SearchSiteSkill,
        ResolveOverlaySkill,
        RecoverNavigationSkill,
        DetectDashboardSkill,
        ValidatePageSkill,
        PaginationSkill,
    ]:
        registry.register(skill_cls())
    return registry

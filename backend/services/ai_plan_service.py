from __future__ import annotations

from pathlib import Path
from typing import Any, Dict
import os

from dotenv import load_dotenv

from backend.ai.schema.test_plan_schema import Step, TestCase
from backend.services.instruction_parser import parse_instruction_context
from backend.services.scenario_expansion_service import expand_scenarios
from backend.services.dom_service import extract_page_elements
from backend.services.website_discovery_service import discover_website_features

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

_CHECKPOINT_MARKERS = (
    "vercel security checkpoint",
    "website owner? click here to fix",
    "security checkpoint",
    "checking if the site connection is secure",
    "bot protection",
    "cloudflare",
)


def _flatten_text(value: Any) -> str:
    parts: list[str] = []

    def visit(item: Any) -> None:
        if item is None:
            return
        if isinstance(item, str):
            parts.append(item)
            return
        if isinstance(item, (int, float, bool)):
            parts.append(str(item))
            return
        if isinstance(item, dict):
            for nested in item.values():
                visit(nested)
            return
        if isinstance(item, (list, tuple, set)):
            for nested in item:
                visit(nested)

    visit(value)
    return " ".join(parts).lower()


def _is_security_checkpoint(dom: Dict[str, Any], discovery: Dict[str, Any]) -> bool:
    text = _flatten_text({"dom": dom, "discovery": discovery})
    return any(marker in text for marker in _CHECKPOINT_MARKERS)


def _blocked_target_plan(url: str, instruction: str, dom: Dict[str, Any], discovery: Dict[str, Any]) -> Dict[str, Any]:
    title = str(dom.get("title") or "Target blocked automation")
    step = {
        "action": "verify",
        "target": "target accessibility",
        "selector": "target accessibility",
        "value": None,
    }
    test_case = {
        "title": "Target access check",
        "expected": "Target page is reachable without an anti-bot or owner checkpoint.",
        "steps": [step],
    }
    return {
        "url": url,
        "instruction": instruction,
        "page_title": title,
        "summary": "Target page appears to be blocked by a security checkpoint, so TestPulse AI generated an access-check plan instead of fake workflow steps.",
        "source": "checkpoint_guard",
        "test_case": test_case,
        "test_cases": [test_case],
        "raw_plan": None,
        "discovery": discovery,
        "discovery_status": "blocked",
        "discovery_error": "target_security_checkpoint",
        "target_blocked": True,
        "target_blocked_reason": "security_checkpoint",
    }


def _plan_step_limit(test_type: str | None) -> int:
    default_limit = int(os.getenv("AI_PLAN_STEP_LIMIT", "18"))
    by_type = {
        "smoke": int(os.getenv("AI_PLAN_SMOKE_STEP_LIMIT", "6")),
        "quick": int(os.getenv("AI_PLAN_SMOKE_STEP_LIMIT", "6")),
        "regression": int(os.getenv("AI_PLAN_REGRESSION_STEP_LIMIT", "18")),
        "deep": int(os.getenv("AI_PLAN_DEEP_STEP_LIMIT", "28")),
        "full": int(os.getenv("AI_PLAN_STEP_LIMIT", "18")),
    }
    return max(1, by_type.get(str(test_type or "").lower(), default_limit))


def _cap_steps(plan: Dict[str, Any], limit: int) -> Dict[str, Any]:
    def cap_case(case: Dict[str, Any], remaining: int) -> int:
        steps = case.get("steps")
        if isinstance(steps, list):
            case["steps"] = steps[:remaining]
            return max(0, remaining - len(case["steps"]))
        return remaining

    remaining = limit
    test_case = plan.get("test_case")
    if isinstance(test_case, dict):
        remaining = cap_case(test_case, remaining)

    test_cases = plan.get("test_cases")
    if isinstance(test_cases, list):
        capped_cases = []
        for case in test_cases:
            if not isinstance(case, dict) or remaining <= 0:
                continue
            before = remaining
            remaining = cap_case(case, remaining)
            if before != remaining:
                capped_cases.append(case)
        plan["test_cases"] = capped_cases

    plan["step_limit"] = limit
    return plan


async def generate_test_plan(url: str, instruction: str, test_type: str | None = None, credentials: Dict[str, Any] | None = None) -> Dict[str, Any]:
    discovery_status = "ready"
    discovery_error = None

    try:
        dom = await extract_page_elements(url)
    except Exception as exc:
        dom = {}
        discovery_status = "dom_failed"
        discovery_error = str(exc)

    try:
        discovery = await discover_website_features(url)
    except Exception as exc:
        discovery = {"feature_map": [], "workflows": [], "forms": [], "pages": [], "discovered_pages": []}
        discovery_status = "partial" if discovery_error is None else "dom_only"
        discovery_error = discovery_error or str(exc)

    instruction_context = parse_instruction_context(instruction, credentials)
    if _is_security_checkpoint(dom, discovery):
        plan = _blocked_target_plan(url, instruction_context["sanitized_instruction"], dom, discovery)
        plan["instruction_context"] = instruction_context
        plan["parsed_credentials"] = instruction_context.get("credentials") or {}
        if test_type:
            plan["test_type"] = test_type
        return plan

    plan = expand_scenarios(url, instruction_context["sanitized_instruction"], dom, discovery)
    _cap_steps(plan, _plan_step_limit(test_type))
    plan["discovery_status"] = discovery_status
    plan["discovery_error"] = discovery_error
    plan["instruction_context"] = instruction_context
    plan["parsed_credentials"] = instruction_context.get("credentials") or {}
    if test_type:
        plan["test_type"] = test_type
    return plan


def _build_autonomous_instruction(discovery: Dict[str, Any]) -> str:
    features = discovery.get("feature_map", []) if isinstance(discovery, dict) else []
    workflows = discovery.get("workflows", []) if isinstance(discovery, dict) else []
    pages = discovery.get("pages", []) if isinstance(discovery, dict) else []

    feature_names = [str(item.get("feature_name") or item.get("feature_key") or "").strip() for item in features if isinstance(item, dict)]
    workflow_names = [str(item.get("name") or item.get("feature_key") or "").strip() for item in workflows if isinstance(item, dict)]
    page_titles = [str(item.get("title") or item.get("page_type") or "").strip() for item in pages if isinstance(item, dict)]

    prompts = [
        "Autonomously discover the website structure and validate the critical business workflows.",
        "Build objectives from the discovered features and workflows.",
        "Generate scenarios for the primary user journeys, failure paths, and recovery paths.",
        "Prioritize important flows such as authentication, navigation, forms, search, inventory, and checkout when present.",
    ]

    if feature_names:
        prompts.append("Discovered features: " + ", ".join(dict.fromkeys(feature_names[:12])) + ".")
    if workflow_names:
        prompts.append("Discovered workflows: " + ", ".join(dict.fromkeys(workflow_names[:12])) + ".")
    if page_titles:
        prompts.append("Observed page types: " + ", ".join(dict.fromkeys(page_titles[:12])) + ".")

    return " ".join(prompts)


async def generate_autonomous_qa_plan(url: str) -> Dict[str, Any]:
    discovery_status = "ready"
    discovery_error = None

    try:
        discovery = await discover_website_features(url)
    except Exception as exc:
        discovery = {"feature_map": [], "workflows": [], "forms": [], "pages": [], "discovered_pages": []}
        discovery_status = "failed"
        discovery_error = str(exc)

    try:
        dom = await extract_page_elements(url)
    except Exception as exc:
        dom = {}
        discovery_status = "dom_only" if discovery_status != "failed" else "failed"
        discovery_error = discovery_error or str(exc)

    instruction = _build_autonomous_instruction(discovery)
    instruction_context = parse_instruction_context(instruction)
    if _is_security_checkpoint(dom, discovery):
        plan = _blocked_target_plan(url, instruction_context["sanitized_instruction"], dom, discovery)
        plan["mode"] = "autonomous_qa"
        plan["instruction"] = instruction
        plan["instruction_context"] = instruction_context
        plan["parsed_credentials"] = instruction_context.get("credentials") or {}
        plan["test_type"] = "autonomous_qa"
        return plan

    plan = expand_scenarios(url, instruction_context["sanitized_instruction"], dom, discovery)
    _cap_steps(plan, _plan_step_limit("autonomous_qa"))
    plan["mode"] = "autonomous_qa"
    plan["instruction"] = instruction
    plan["instruction_context"] = instruction_context
    plan["parsed_credentials"] = instruction_context.get("credentials") or {}
    plan["discovery"] = discovery
    plan["discovery_status"] = discovery_status
    plan["discovery_error"] = discovery_error
    plan["test_type"] = "autonomous_qa"
    return plan


def build_executable_test_case(plan: Dict[str, Any]) -> TestCase:
    test_case = plan.get("test_case") or plan
    steps = [Step(**step) for step in test_case.get("steps", [])]
    return TestCase(
        title=test_case.get("title"),
        expected=test_case.get("expected"),
        steps=steps,
        objective_id=test_case.get("objective_id") or plan.get("objective_id"),
        objective_name=test_case.get("objective_name") or plan.get("objective_name"),
        feature_key=test_case.get("feature_key") or plan.get("feature_key"),
        coverage_level=test_case.get("coverage_level") or plan.get("coverage_level"),
        coverage_profile=test_case.get("coverage_profile") or plan.get("coverage_profile"),
        objective_tracking=test_case.get("objective_tracking") or plan.get("objective_tracking"),
        plan_metrics=test_case.get("plan_metrics") or plan.get("plan_metrics"),
        scenario_id=test_case.get("scenario_id") or plan.get("scenario_id"),
        scenario_name=test_case.get("scenario_name") or plan.get("scenario_name"),
        scenario_tree=test_case.get("scenario_tree") or plan.get("scenario_tree"),
    )

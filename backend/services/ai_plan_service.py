from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

from backend.ai.schema.test_plan_schema import Step, TestCase
from backend.services.instruction_parser import parse_instruction_context
from backend.services.scenario_expansion_service import expand_scenarios
from backend.services.dom_service import extract_page_elements
from backend.services.website_discovery_service import discover_website_features

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)


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
    plan = expand_scenarios(url, instruction_context["sanitized_instruction"], dom, discovery)
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
    plan = expand_scenarios(url, instruction_context["sanitized_instruction"], dom, discovery)
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

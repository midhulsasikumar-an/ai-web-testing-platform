from __future__ import annotations

import os
import re
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional, Tuple


COVERAGE_LEVELS = ("minimal", "standard", "deep", "aggressive")
COVERAGE_DEPTH = {level: index + 1 for index, level in enumerate(COVERAGE_LEVELS)}
COVERAGE_PROFILE_ALIASES = {
    "minimal": "Smoke",
    "standard": "Standard",
    "deep": "Deep",
    "aggressive": "Exhaustive",
}

FEATURE_ALIASES: Dict[str, Tuple[str, ...]] = {
    "AUTHENTICATION": ("authentication", "login", "log in", "sign in", "session", "logout", "password", "credential"),
    "FORMS": ("form", "submit", "field", "input", "register", "signup", "contact"),
    "SEARCH": ("search", "find", "lookup", "query"),
    "INVENTORY": ("inventory", "product", "products", "item", "items", "catalog", "listing", "cart badge"),
    "CART": ("cart", "basket", "shopping cart", "cart page", "cart badge"),
    "TABLES": ("table", "grid", "pagination", "sorting", "filtering", "row"),
    "NAVIGATION": ("navigation", "menu", "link", "route", "breadcrumb", "sidebar", "deep link"),
    "CHECKOUT": ("checkout", "transaction", "payment", "purchase", "order", "cart", "basket"),
    "PAYMENT": ("payment", "card", "billing", "invoice", "refund", "charge"),
    "UPLOADS": ("upload", "file", "attachment", "import", "export", "csv", "pdf", "image"),
    "PERMISSIONS": ("permission", "role", "access", "rbac", "authorization", "admin"),
    "APIS": ("api", "endpoint", "request", "response", "webhook", "integration"),
    "DATA_MODIFICATION": ("create", "update", "delete", "edit", "save", "persist"),
    "SETTINGS": ("settings", "configuration", "preferences", "profile"),
    "GENERIC": (),
}

FEATURE_RISK_BASE = {
    "AUTHENTICATION": 74,
    "INVENTORY": 63,
    "CART": 68,
    "CHECKOUT": 78,
    "PAYMENT": 80,
    "UPLOADS": 74,
    "PERMISSIONS": 82,
    "APIS": 76,
    "DATA_MODIFICATION": 70,
    "SETTINGS": 52,
    "FORMS": 58,
    "SEARCH": 45,
    "TABLES": 42,
    "NAVIGATION": 48,
    "GENERIC": 54,
}

LEVEL_RISK_BONUS = {
    "minimal": 0,
    "standard": 6,
    "deep": 14,
    "aggressive": 24,
}

SCENARIO_CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "AUTHENTICATION": [
        {"category": "valid_input", "name": "Valid Input", "level": "minimal", "risk": 56, "validations": ["success_state", "session_created"]},
        {"category": "invalid_input", "name": "Invalid Input", "level": "standard", "risk": 68, "validations": ["error_message", "no_session"]},
        {"category": "empty_fields", "name": "Empty Fields", "level": "standard", "risk": 62, "validations": ["required_errors"]},
        {"category": "boundary_values", "name": "Boundary Values", "level": "deep", "risk": 70, "validations": ["field_limits", "safe_error"]},
        {"category": "locked_accounts", "name": "Locked Accounts", "level": "aggressive", "risk": 84, "validations": ["lockout_message", "no_session"]},
        {"category": "session_handling", "name": "Session Handling", "level": "deep", "risk": 82, "validations": ["session_persistence", "protected_route"]},
        {"category": "logout_validation", "name": "Logout Validation", "level": "standard", "risk": 72, "validations": ["session_destroyed", "protected_route_denied"]},
        {"category": "sql_injection", "name": "SQL Injection Attempts", "level": "aggressive", "risk": 92, "validations": ["input_rejected", "no_auth_bypass"]},
        {"category": "xss_attempts", "name": "XSS Attempts", "level": "aggressive", "risk": 90, "validations": ["payload_escaped", "no_script_execution"]},
    ],
    "FORMS": [
        {"category": "required_fields", "name": "Required Fields", "level": "minimal", "risk": 52, "validations": ["required_errors"]},
        {"category": "invalid_formats", "name": "Invalid Formats", "level": "standard", "risk": 58, "validations": ["format_errors"]},
        {"category": "boundary_lengths", "name": "Boundary Lengths", "level": "deep", "risk": 64, "validations": ["length_limits"]},
        {"category": "empty_submission", "name": "Empty Submission", "level": "standard", "risk": 60, "validations": ["submission_blocked"]},
        {"category": "partial_submission", "name": "Partial Submission", "level": "standard", "risk": 57, "validations": ["missing_field_errors"]},
        {"category": "duplicate_submission", "name": "Duplicate Submission", "level": "deep", "risk": 72, "validations": ["idempotency", "duplicate_prevention"]},
    ],
    "SEARCH": [
        {"category": "valid_searches", "name": "Valid Searches", "level": "minimal", "risk": 38, "validations": ["results_visible"]},
        {"category": "empty_searches", "name": "Empty Searches", "level": "standard", "risk": 40, "validations": ["safe_empty_state"]},
        {"category": "special_characters", "name": "Special Characters", "level": "deep", "risk": 55, "validations": ["input_sanitized"]},
        {"category": "large_input", "name": "Large Input", "level": "deep", "risk": 60, "validations": ["response_stable"]},
        {"category": "no_result_scenarios", "name": "No Result Scenarios", "level": "standard", "risk": 44, "validations": ["no_results_message"]},
    ],
    "INVENTORY": [
        {"category": "inventory_load", "name": "Inventory Load", "level": "minimal", "risk": 54, "validations": ["products_visible"]},
        {"category": "cart_progression", "name": "Add To Cart Progression", "level": "standard", "risk": 66, "validations": ["cart_badge", "state_preserved"]},
        {"category": "detail_view", "name": "Product Detail View", "level": "deep", "risk": 60, "validations": ["product_detail_visible"]},
    ],
    "CART": [
        {"category": "cart_load", "name": "Cart Load", "level": "minimal", "risk": 56, "validations": ["cart_items_visible"]},
        {"category": "state_preservation", "name": "Cart State Preservation", "level": "standard", "risk": 64, "validations": ["selected_item", "state_preserved"]},
        {"category": "checkout_progression", "name": "Checkout Progression", "level": "deep", "risk": 70, "validations": ["checkout_state", "continue_state"]},
    ],
    "TABLES": [
        {"category": "pagination", "name": "Pagination", "level": "standard", "risk": 42, "validations": ["page_changes", "row_count_stable"]},
        {"category": "sorting", "name": "Sorting", "level": "standard", "risk": 45, "validations": ["order_changes"]},
        {"category": "filtering", "name": "Filtering", "level": "deep", "risk": 50, "validations": ["filtered_results"]},
        {"category": "row_actions", "name": "Row Actions", "level": "deep", "risk": 65, "validations": ["row_action_result"]},
    ],
    "NAVIGATION": [
        {"category": "menu_consistency", "name": "Menu Consistency", "level": "minimal", "risk": 40, "validations": ["menu_visible", "active_state"]},
        {"category": "broken_links", "name": "Broken Links", "level": "standard", "risk": 58, "validations": ["no_404", "same_origin"]},
        {"category": "browser_back_forward", "name": "Browser Back/Forward", "level": "deep", "risk": 54, "validations": ["history_state"]},
        {"category": "deep_links", "name": "Deep Links", "level": "deep", "risk": 62, "validations": ["direct_route_loads"]},
    ],
    "CHECKOUT": [
        {"category": "complete_workflow", "name": "Complete Workflow", "level": "minimal", "risk": 72, "validations": ["order_confirmation", "checkout_state"]},
        {"category": "validation_failures", "name": "Validation Failures", "level": "standard", "risk": 76, "validations": ["payment_errors", "required_errors"]},
        {"category": "partial_completion", "name": "Partial Completion", "level": "deep", "risk": 82, "validations": ["state_preserved", "no_duplicate_order"]},
        {"category": "recovery_scenarios", "name": "Recovery Scenarios", "level": "deep", "risk": 86, "validations": ["resume_flow", "cart_preserved"]},
    ],
    "PAYMENT": [
        {"category": "complete_workflow", "name": "Successful Payment", "level": "minimal", "risk": 78, "validations": ["payment_success"]},
        {"category": "validation_failures", "name": "Card Validation Errors", "level": "standard", "risk": 83, "validations": ["payment_errors", "no_charge"]},
        {"category": "boundary_values", "name": "Boundary Amounts", "level": "deep", "risk": 80, "validations": ["amount_limits", "safe_error"]},
        {"category": "recovery_scenarios", "name": "Interrupted Payment Recovery", "level": "deep", "risk": 86, "validations": ["state_preserved", "no_duplicate_charge"]},
    ],
    "UPLOADS": [
        {"category": "valid_input", "name": "Supported File Upload", "level": "minimal", "risk": 66, "validations": ["upload_success"]},
        {"category": "invalid_formats", "name": "Unsupported File Type", "level": "standard", "risk": 74, "validations": ["format_errors"]},
        {"category": "boundary_values", "name": "File Size Boundaries", "level": "deep", "risk": 78, "validations": ["size_limits", "safe_error"]},
        {"category": "xss_attempts", "name": "Malicious File Name/Content", "level": "aggressive", "risk": 90, "validations": ["payload_escaped", "upload_blocked"]},
    ],
    "PERMISSIONS": [
        {"category": "valid_input", "name": "Authorized Access", "level": "minimal", "risk": 74, "validations": ["access_granted"]},
        {"category": "invalid_input", "name": "Unauthorized Access", "level": "standard", "risk": 86, "validations": ["access_denied"]},
        {"category": "session_handling", "name": "Role Transition Handling", "level": "deep", "risk": 82, "validations": ["role_refresh", "access_scope"]},
        {"category": "sql_injection", "name": "Privilege Escalation Injection", "level": "aggressive", "risk": 92, "validations": ["no_privilege_escalation"]},
    ],
    "APIS": [
        {"category": "valid_input", "name": "Valid API Requests", "level": "minimal", "risk": 70, "validations": ["success_status", "schema_valid"]},
        {"category": "invalid_input", "name": "Invalid Payload Handling", "level": "standard", "risk": 78, "validations": ["validation_error", "safe_error"]},
        {"category": "boundary_values", "name": "Rate/Size Boundaries", "level": "deep", "risk": 82, "validations": ["throttle_behavior", "safe_error"]},
        {"category": "recovery_scenarios", "name": "Transient Failure Recovery", "level": "deep", "risk": 84, "validations": ["retry_behavior", "idempotency"]},
    ],
    "DATA_MODIFICATION": [
        {"category": "complete_workflow", "name": "Create/Update/Delete Success", "level": "minimal", "risk": 68, "validations": ["state_updated"]},
        {"category": "validation_failures", "name": "Data Validation Failures", "level": "standard", "risk": 76, "validations": ["validation_error"]},
        {"category": "partial_completion", "name": "Interrupted Save Recovery", "level": "deep", "risk": 79, "validations": ["state_preserved", "no_data_loss"]},
        {"category": "recovery_scenarios", "name": "Conflict/Retry Handling", "level": "deep", "risk": 82, "validations": ["conflict_resolution"]},
    ],
    "SETTINGS": [
        {"category": "valid_input", "name": "Valid Preference Update", "level": "minimal", "risk": 52, "validations": ["setting_saved"]},
        {"category": "invalid_input", "name": "Invalid Preference Input", "level": "standard", "risk": 60, "validations": ["validation_error"]},
        {"category": "boundary_values", "name": "Boundary Preference Values", "level": "deep", "risk": 64, "validations": ["limits_enforced"]},
    ],
    "GENERIC": [
        {"category": "valid_input", "name": "Happy Path", "level": "minimal", "risk": 56, "validations": ["expected_state"]},
        {"category": "invalid_input", "name": "Invalid Input", "level": "standard", "risk": 62, "validations": ["safe_error"]},
        {"category": "boundary_values", "name": "Boundary Values", "level": "deep", "risk": 70, "validations": ["limits_enforced", "safe_error"]},
        {"category": "recovery_scenarios", "name": "Recovery Flow", "level": "deep", "risk": 72, "validations": ["state_recovered"]},
    ],
}

MAX_SCENARIOS = int(os.getenv("AI_PLAN_MAX_SCENARIOS", "20"))
MIN_SCENARIO_RISK_SCORE = int(os.getenv("AI_PLAN_MIN_SCENARIO_RISK_SCORE", "35"))


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().replace("_", " ").replace("-", " ").split())


def _title(value: Any) -> str:
    text = str(value or "").replace("_", " ").strip()
    return " ".join(part.capitalize() for part in text.split()) or "Feature"


def _slug(value: Any) -> str:
    normalized = _normalize_text(value)
    return normalized.replace(" ", "_") or "state"


def _scenario_dependency_profile(feature_type: str, scenario: Dict[str, Any], objective_name: str) -> Dict[str, Any]:
    feature_key = str(feature_type or "GENERIC").upper()
    scenario_category = str(scenario.get("category") or "").lower()
    feature_label = _slug(feature_key)
    objective_label = _slug(objective_name)

    profile: Dict[str, Any] = {
        "depends_on": [],
        "required_state": [],
        "produces_state": [],
        "required_page": None,
    }

    if feature_key == "AUTHENTICATION":
        profile["required_page"] = "login"
        if scenario_category in {"valid_input", "session_handling"}:
            profile["produces_state"] = ["authenticated_session", f"{feature_label}_success", f"{objective_label}_success"]
        elif scenario_category == "logout_validation":
            profile["depends_on"] = ["authenticated_session"]
            profile["required_state"] = ["authenticated_session"]
            profile["produces_state"] = ["logged_out_session", f"{feature_label}_logged_out"]
        else:
            profile["produces_state"] = ["authentication_rejected", f"{feature_label}_rejected"]

    elif feature_key == "INVENTORY":
        profile.update(
            {
                "depends_on": ["authenticated_session"],
                "required_state": ["authenticated_session"],
                "produces_state": ["inventory_loaded", f"{feature_label}_ready", f"{objective_label}_ready"],
                "required_page": "inventory",
            }
        )

    elif feature_key == "CART":
        profile.update(
            {
                "depends_on": ["authenticated_session", "inventory_loaded"],
                "required_state": ["authenticated_session", "inventory_loaded"],
                "produces_state": ["cart_ready", f"{feature_label}_ready", f"{objective_label}_ready"],
                "required_page": "cart",
            }
        )

    elif feature_key == "CHECKOUT":
        profile.update(
            {
                "depends_on": ["authenticated_session", "inventory_loaded", "cart_ready"],
                "required_state": ["authenticated_session", "inventory_loaded", "cart_ready"],
                "produces_state": ["checkout_ready", f"{feature_label}_ready", f"{objective_label}_ready"],
                "required_page": "checkout",
            }
        )

    elif feature_key == "PAYMENT":
        profile.update(
            {
                "depends_on": ["authenticated_session", "cart_ready", "checkout_ready"],
                "required_state": ["authenticated_session", "cart_ready", "checkout_ready"],
                "produces_state": ["payment_ready", f"{feature_label}_ready", f"{objective_label}_ready"],
                "required_page": "payment",
            }
        )

    elif feature_key in {"PERMISSIONS", "DATA_MODIFICATION", "UPLOADS", "APIS", "SETTINGS"}:
        profile["produces_state"] = [f"{feature_label}_ready", f"{objective_label}_ready"]
        if feature_key == "SETTINGS":
            profile["required_page"] = "settings"

    else:
        profile["produces_state"] = [f"{feature_label}_ready", f"{objective_label}_ready"]

    return profile


def _coverage_depth(level: str) -> int:
    return COVERAGE_DEPTH.get(str(level or "standard").lower(), COVERAGE_DEPTH["standard"])


def _coverage_profile(level: str) -> str:
    return COVERAGE_PROFILE_ALIASES.get(str(level or "standard").lower(), "Standard")


def _coverage_for_instruction(instruction: str) -> str:
    normalized = _normalize_text(instruction)
    if any(term in normalized for term in ["smoke", "quick", "sanity"]):
        return "minimal"
    for level in reversed(COVERAGE_LEVELS):
        if level in normalized:
            return level
    if any(term in normalized for term in ["exhaustive", "attack", "security", "sql", "xss", "abuse"]):
        return "aggressive"
    if any(term in normalized for term in ["deep", "thorough", "heavily", "edge case", "boundary"]):
        return "deep"
    return "standard"


_WORKFLOW_RISK_KEYWORDS = (
    "comprehensive", "exhaustive", "risk based", "risk-based",
    "edge case", "edge cases", "negative scenario", "negative scenarios",
    "validation scenario", "validation scenarios", "security testing",
    "robustness", "full testing", "all scenarios", "all features",
    "complete coverage", "thorough testing", "sql injection", "xss",
    "boundary", "locked account", "session handling", "logout validation",
)

_CHECKOUT_INSTRUCTION_TOKENS = (
    "checkout", "purchase", "payment", "order", "transaction",
)

_WORKFLOW_POSITIVE_CATEGORIES = {
    "AUTHENTICATION": "valid_input",
    "INVENTORY": "cart_progression",
    "CART": "cart_load",
    "CHECKOUT": "complete_workflow",
    "SEARCH": "valid_searches",
    "NAVIGATION": "menu_consistency",
    "FORMS": "valid_input",
    "TABLES": "pagination",
    "SETTINGS": "valid_input",
    "PAYMENT": "complete_workflow",
    "UPLOADS": "valid_input",
    "PERMISSIONS": "valid_input",
    "APIS": "valid_input",
    "DATA_MODIFICATION": "complete_workflow",
}


def _is_workflow_instruction(instruction: str) -> bool:
    normalized = _normalize_text(instruction)
    return not any(kw in normalized for kw in _WORKFLOW_RISK_KEYWORDS)


def _expand_workflow_scenarios(
    url: str,
    instruction: str,
    dom: Dict[str, Any],
    discovery: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    normalized = _normalize_text(instruction)

    detected_features: List[str] = []
    seen_features: set[str] = set()
    for feature_type, aliases in FEATURE_ALIASES.items():
        if feature_type == "GENERIC":
            continue
        if any(re.search(r'\b' + re.escape(alias) + r'\b', normalized) for alias in aliases):
            if feature_type not in seen_features:
                detected_features.append(feature_type)
                seen_features.add(feature_type)

    if not detected_features:
        return None

    has_checkout_intent = any(
        token in normalized for token in _CHECKOUT_INSTRUCTION_TOKENS
    )
    if "CHECKOUT" in detected_features and not has_checkout_intent:
        detected_features.remove("CHECKOUT")

    if "INVENTORY" in detected_features and "CART" in detected_features:
        detected_features.remove("CART")

    feature_order = {
        "AUTHENTICATION": 0, "INVENTORY": 1, "CART": 2, "CHECKOUT": 3,
        "PAYMENT": 4, "SEARCH": 5, "NAVIGATION": 6, "FORMS": 7,
        "TABLES": 8, "SETTINGS": 9, "UPLOADS": 10, "PERMISSIONS": 11,
        "APIS": 12, "DATA_MODIFICATION": 13,
    }
    detected_features.sort(key=lambda ft: feature_order.get(ft, 99))

    all_steps: List[Dict[str, Any]] = []
    seen_step_keys: set[tuple[str, str]] = set()

    for feature_type in detected_features:
        objective_name = _title(feature_type)
        positive_category = _WORKFLOW_POSITIVE_CATEGORIES.get(feature_type, "valid_input")

        catalog_items = SCENARIO_CATALOG.get(feature_type, [])
        catalog_match = None
        for item in catalog_items:
            if item["category"] == positive_category:
                catalog_match = item
                break
        if catalog_match is None and catalog_items:
            catalog_match = catalog_items[0]
        if catalog_match is None:
            continue

        feature = {
            "feature_type": feature_type,
            "feature_key": feature_type,
            "feature_name": objective_name,
            "evidence": ["instruction"],
            "sources": ["instruction"],
        }

        metadata = {
            "feature_type": feature_type,
            "evidence": ["instruction"],
            "sources": ["instruction"],
            "available_actions": [],
            "forms": [],
            "tables": [],
            "workflows": [],
            "validation_requirements": [],
        }

        coverage_level = "minimal"
        dummy_scenario = {
            "scenario_id": "wf_s1",
            "scenario_name": "Workflow Test Plan",
            "category": catalog_match["category"],
            "feature_type": feature_type,
            "coverage_level": coverage_level,
            "risk_score": 0,
            "risk_level": "low",
            "validation_requirements": [],
            "execution_status": "pending",
            "depends_on": [],
            "required_state": [],
            "produces_state": [],
            "required_page": None,
        }

        steps = _scenario_steps(
            feature, metadata, "obj_1", objective_name,
            dummy_scenario, coverage_level, url,
        )

        for step in steps:
            s = step
            if s.get("action") == "verify":
                target_lower = str(s.get("target", "")).lower()
                verify_remap = {
                    "inventory page": "Products visible",
                    "cart badge": "Products added",
                }
                if target_lower in verify_remap:
                    s = dict(s)
                    remapped_target = verify_remap[target_lower]
                    s["target"] = remapped_target
                    s["selector"] = remapped_target
            step_key = (str(s.get("action", "")), str(s.get("target", "")))
            if step_key not in seen_step_keys:
                seen_step_keys.add(step_key)
                all_steps.append(s)

    if not all_steps:
        return None

    workflow_scenario_case = {
        "title": "Workflow Test Plan",
        "expected": "All workflow steps executed successfully.",
        "objective_id": "obj_1",
        "objective_name": "Workflow Test Plan",
        "feature_key": "WORKFLOW",
        "coverage_level": "minimal",
        "scenario_id": "wf_s1",
        "scenario_name": "Workflow Test Plan",
        "category": "workflow",
        "scenario_category": "workflow",
        "generated_steps": len(all_steps),
        "coverage_profile": "Smoke",
        "risk_score": 0,
        "risk_level": "low",
        "depends_on": [],
        "required_state": [],
        "produces_state": [],
        "required_page": None,
        "steps": all_steps,
    }

    workflow_objective = {
        "objective_id": "obj_1",
        "objective_name": "Workflow Test Plan",
        "feature_key": "WORKFLOW",
        "feature_name": "Workflow Test Plan",
        "feature_type": "WORKFLOW",
        "coverage_level": "minimal",
        "coverage_profile": "Smoke",
        "priority_score": 0,
        "risk_score": 0,
        "risk_level": "low",
        "risk_factors": ["workflow_mode"],
        "generated_scenarios": 1,
        "generated_steps": len(all_steps),
        "execution_status": "pending",
        "scenarios": [{
            "scenario_id": "wf_s1",
            "scenario_name": "Workflow Test Plan",
            "category": "workflow",
            "coverage_level": "minimal",
            "risk_score": 0,
            "risk_level": "low",
            "generated_steps": len(all_steps),
            "execution_status": "pending",
            "depends_on": [],
            "required_state": [],
            "produces_state": [],
            "required_page": None,
        }],
    }

    workflow_feature_profile = {
        "objective_id": "obj_1",
        "feature_key": "WORKFLOW",
        "feature_name": "Workflow Test Plan",
        "feature_type": "WORKFLOW",
        "coverage_level": "minimal",
        "coverage_profile": "Smoke",
        "priority_score": 0,
        "risk_score": 0,
        "risk_level": "low",
        "risk_factors": ["workflow_mode"],
    }

    combined_case = {
        "title": "Workflow Test Plan",
        "expected": "All workflow steps executed successfully.",
        "steps": all_steps,
        "objective_tracking": [workflow_objective],
        "plan_metrics": {
            "requested_objectives": 1,
            "planned_objectives": 1,
            "generated_scenarios": 1,
            "generated_steps": len(all_steps),
            "coverage_profile_counts": {"minimal": 1},
            "feature_type_counts": {"WORKFLOW": 1},
            "risk_level_counts": {"low": 1},
            "focused_features": [],
            "max_scenarios": 1,
            "min_scenario_risk_score": 0,
            "scenario_cap_applied": False,
            "risk_summary": {
                "critical_features": 0,
                "high_features": 0,
                "medium_features": 0,
                "low_features": 1,
                "critical_scenarios": 0,
                "high_scenarios": 0,
                "medium_scenarios": 0,
                "low_scenarios": 1,
            },
        },
        "scenario_tree": {
            "coverage_levels": list(COVERAGE_LEVELS),
            "coverage_profiles": {level: _coverage_profile(level) for level in COVERAGE_LEVELS},
            "default_coverage_level": "minimal",
            "focus_overrides": {},
            "features": [workflow_feature_profile],
            "summary": {
            "requested_objectives": 1,
                "planned_objectives": 1,
                "generated_scenarios": 1,
                "generated_steps": len(all_steps),
            },
        },
    }

    return {
        "url": url,
        "instruction": instruction,
        "page_title": str(dom.get("title") or "AI Generated Test"),
        "summary": "Workflow test plan generated successfully.",
        "source": "workflow_mode",
        "status": "ready" if all_steps else "failed",
        "failure_reason": None if all_steps else "workflow_steps_empty",
        "discovery": discovery,
        "requested_objectives": ["Workflow Test Plan"],
        "planned_objectives": ["Workflow Test Plan"],
        "feature_profiles": [workflow_feature_profile],
        "objective_tracking": [workflow_objective],
        "scenario_tree": combined_case["scenario_tree"],
        "plan_metrics": combined_case["plan_metrics"],
        "test_case": combined_case,
        "test_cases": [workflow_scenario_case],
        "scenario_cases": [workflow_scenario_case],
        "raw_plan": {"dom": dom, "discovery": discovery},
    }


def _focused_feature_types(instruction: str) -> List[str]:
    normalized = _normalize_text(instruction)
    focus_terms = ["focus heavily on", "prioritize heavily", "deep focus on", "aggressively test"]
    focused: List[str] = []
    for feature_type, aliases in FEATURE_ALIASES.items():
        if any(f"{phrase} {alias}" in normalized for phrase in focus_terms for alias in aliases):
            focused.append(feature_type)
    return focused


def _feature_type_from_text(*values: Any) -> Optional[str]:
    text = _normalize_text(" ".join(str(value or "") for value in values))
    for feature_type, aliases in FEATURE_ALIASES.items():
        if any(alias in text for alias in aliases):
            return feature_type
    return None


def _instruction_objectives(instruction: str) -> List[str]:
    normalized = _normalize_text(instruction)
    markers = ["objective", "objectives", "test", "validate", "verify", "cover", "include", "focus on"]
    split_source = normalized
    for marker in markers:
        if marker in normalized:
            split_source = normalized.split(marker, 1)[1]
            break
    chunks = re.split(r"\n|;|\.|,| and | then | also ", split_source)
    objectives: List[str] = []
    seen = set()
    for raw in chunks:
        text = _normalize_text(raw)
        if len(text) < 4:
            continue
        if text in {"the", "a", "an", "for", "with"}:
            continue
        if text in seen:
            continue
        seen.add(text)
        objectives.append(_title(text))
    return objectives


def _field_text(fields: Iterable[Dict[str, Any]]) -> str:
    chunks: List[str] = []
    for field in fields or []:
        if isinstance(field, dict):
            chunks.extend(str(field.get(key) or "") for key in ["name", "type", "placeholder", "aria_label", "id"])
    return " ".join(chunks)


def _forms_for_feature(feature_type: str, discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    forms = [form for form in discovery.get("forms", []) or [] if isinstance(form, dict)]
    if feature_type == "AUTHENTICATION":
        return [form for form in forms if _feature_type_from_text(form.get("name"), form.get("action"), form.get("page_title"), _field_text(form.get("fields", []))) == "AUTHENTICATION"] or forms[:1]
    if feature_type == "CHECKOUT":
        return [form for form in forms if _feature_type_from_text(form.get("name"), form.get("action"), form.get("page_title"), _field_text(form.get("fields", []))) == "CHECKOUT"]
    if feature_type == "FORMS":
        return forms
    return []


def _tables_for_feature(feature_type: str, discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    tables: List[Dict[str, Any]] = []
    for page in discovery.get("discovered_pages", []) or []:
        if isinstance(page, dict):
            tables.extend(table for table in page.get("tables", []) or [] if isinstance(table, dict))
    return tables if feature_type == "TABLES" else []


def _actions_for_feature(feature_type: str, dom: Dict[str, Any], discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions: List[Dict[str, Any]] = []
    for button in dom.get("buttons", []) or []:
        if isinstance(button, dict):
            actions.append({"type": "button", **button})
    for link in dom.get("links", []) or []:
        if isinstance(link, dict):
            actions.append({"type": "link", **link})
    for page in discovery.get("discovered_pages", []) or []:
        if not isinstance(page, dict):
            continue
        for workflow in page.get("workflows", []) or []:
            if isinstance(workflow, dict):
                actions.append({"type": "workflow", **workflow})
    if feature_type == "NAVIGATION":
        return [action for action in actions if action.get("type") in {"link", "workflow"}] or actions
    return actions


def _validation_requirements(feature_type: str, forms: List[Dict[str, Any]], workflows: List[Dict[str, Any]]) -> List[str]:
    requirements = set()
    if forms:
        requirements.update(["required_fields", "format_validation", "error_messages"])
    if workflows:
        requirements.update(["state_transition", "workflow_completion"])
    feature_requirements = {
        "AUTHENTICATION": ["session_state", "authorization_boundary", "logout_state"],
        "CHECKOUT": ["transaction_integrity", "recovery_state"],
        "CART": ["selection_state", "cart_integrity"],
        "SEARCH": ["result_state", "empty_state"],
        "TABLES": ["data_order", "row_state"],
        "NAVIGATION": ["route_integrity", "history_state"],
    }
    requirements.update(feature_requirements.get(feature_type, []))
    return sorted(requirements)


def _workflow_matches(feature_type: str, discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    matches = []
    for workflow in discovery.get("workflows", []) or []:
        if not isinstance(workflow, dict):
            continue
        workflow_type = _feature_type_from_text(workflow.get("feature_key"), workflow.get("name"), workflow.get("entry_point"))
        if workflow_type == feature_type:
            matches.append(workflow)
    return matches


def _discovered_features(instruction: str, dom: Dict[str, Any], discovery: Dict[str, Any]) -> List[Dict[str, Any]]:
    features: Dict[str, Dict[str, Any]] = {}

    def add(feature_type: str, name: Optional[str] = None, evidence: Any = None, source: str = "inferred") -> None:
        catalog_key = feature_type if feature_type in SCENARIO_CATALOG else "GENERIC"
        dedupe_key = _normalize_text(name or feature_type)
        key = catalog_key
        if catalog_key == "GENERIC" or source == "instruction_requested":
            key = f"{catalog_key}:{dedupe_key}"
        current = features.setdefault(
            key,
            {
                "feature_type": catalog_key,
                "feature_key": feature_type,
                "feature_name": name or _title(feature_type),
                "evidence": [],
                "sources": [],
            },
        )
        if evidence:
            current["evidence"].append(str(evidence))
        current["sources"].append(source)

    for item in discovery.get("feature_map", []) or []:
        if isinstance(item, dict):
            feature_type = _feature_type_from_text(item.get("feature_key"), item.get("feature_name"), item.get("evidence"))
            if feature_type:
                add(feature_type, item.get("feature_name") or _title(feature_type), item.get("evidence"), "discovery_feature_map")

    for workflow in discovery.get("workflows", []) or []:
        if isinstance(workflow, dict):
            feature_type = _feature_type_from_text(workflow.get("feature_key"), workflow.get("name"), workflow.get("entry_point"))
            if feature_type:
                add(feature_type, workflow.get("name") or _title(feature_type), workflow.get("entry_point"), "workflow")

    forms = discovery.get("forms", []) or []
    if forms:
        add("FORMS", "Forms", f"{len(forms)} form(s)", "forms")
        for form in forms:
            if isinstance(form, dict):
                form_type = _feature_type_from_text(form.get("name"), form.get("action"), form.get("page_title"), _field_text(form.get("fields", [])))
                if form_type:
                    add(form_type, _title(form_type), form.get("name") or form.get("page_title"), "form_metadata")

    table_count = sum(int(page.get("tables", 0) or 0) for page in discovery.get("pages", []) or [] if isinstance(page, dict))
    if table_count:
        add("TABLES", "Tables", f"{table_count} table(s)", "tables")

    if dom.get("links") or any((page.get("links", 0) or 0) for page in discovery.get("pages", []) or [] if isinstance(page, dict)):
        add("NAVIGATION", "Navigation", "links discovered", "links")

    normalized_instruction = _normalize_text(instruction)
    for feature_type, aliases in FEATURE_ALIASES.items():
        if feature_type == "GENERIC":
            continue
        if any(alias in normalized_instruction for alias in aliases):
            add(feature_type, _title(feature_type), "instruction", "instruction")

    for objective in _instruction_objectives(instruction):
        inferred_type = _feature_type_from_text(objective) or "GENERIC"
        add(inferred_type, objective, objective, "instruction_requested")

    if not features:
        add("NAVIGATION", "Navigation", "fallback", "fallback")

    return list(features.values())


def _risk_level(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 70:
        return "high"
    if score >= 50:
        return "medium"
    return "low"


def _feature_risk(feature_type: str, coverage_level: str, metadata: Dict[str, Any], focused: bool) -> Tuple[int, List[str]]:
    score = FEATURE_RISK_BASE.get(feature_type, 45) + LEVEL_RISK_BONUS.get(coverage_level, 6)
    factors = [f"base_{feature_type.lower()}_risk", f"coverage_{coverage_level}"]
    if focused:
        score += 12
        factors.append("user_focus_override")
    if "instruction_requested" in (metadata.get("sources") or []):
        score += 8
        factors.append("explicit_objective_requested")
    if metadata.get("forms"):
        score += min(8, len(metadata["forms"]) * 2)
        factors.append("forms_present")
    if metadata.get("workflows"):
        score += min(6, len(metadata["workflows"]) * 2)
        factors.append("workflow_present")
    if metadata.get("validation_requirements"):
        score += min(6, len(metadata["validation_requirements"]))
        factors.append("validation_requirements_present")
    return min(100, score), factors


def _field_hint(metadata: Dict[str, Any], index: int, fallback: str) -> str:
    for form in metadata.get("forms") or []:
        fields = form.get("fields", []) if isinstance(form, dict) else []
        if len(fields) > index and isinstance(fields[index], dict):
            field = fields[index]
            return str(field.get("placeholder") or field.get("name") or field.get("aria_label") or field.get("type") or fallback)
    return fallback


def _primary_action(metadata: Dict[str, Any], fallback: str) -> str:
    for action in metadata.get("available_actions", []) or []:
        label = action.get("text") or action.get("aria_label") or action.get("name") or action.get("href") or action.get("entry_point")
        if label:
            return str(label)
    return fallback


def _nav_link_target(metadata: Dict[str, Any], fallback: str) -> str:
    """Pick a real navigation link label from discovered page actions.

    Prefers links with visible text over generic submit buttons.
    Falls back to *fallback* only when nothing concrete was discovered.
    """
    for action in metadata.get("available_actions", []) or []:
        action_type = action.get("type", "")
        text = (action.get("text") or action.get("aria_label") or "").strip()
        # Skip empty, icon-only, or trivially short labels
        if not text or len(text) < 2:
            continue
        # Prefer actual navigation links and workflow anchors
        if action_type in {"link", "workflow"}:
            return text
    # Second pass: accept any action with usable text
    for action in metadata.get("available_actions", []) or []:
        text = (action.get("text") or action.get("aria_label") or "").strip()
        if text and len(text) >= 2:
            return text
    return fallback


def _step(action: str, target: str, *, value: Optional[str], feature: Dict[str, Any], objective_id: str, objective_name: str, scenario: Dict[str, Any], coverage_level: str) -> Dict[str, Any]:
    return {
        "action": action,
        "target": target,
        "selector": target,
        "value": value,
        "feature_key": feature["feature_type"],
        "objective_id": objective_id,
        "objective_name": objective_name,
        "scenario_id": scenario["scenario_id"],
        "scenario_name": scenario["scenario_name"],
        "scenario_category": scenario["category"],
        "coverage_level": coverage_level,
        "coverage_profile": _coverage_profile(coverage_level),
        "risk_score": scenario["risk_score"],
        "risk_level": scenario["risk_level"],
    }


def _scenario_steps(feature: Dict[str, Any], metadata: Dict[str, Any], objective_id: str, objective_name: str, scenario: Dict[str, Any], coverage_level: str, url: str) -> List[Dict[str, Any]]:
    category = scenario["category"]
    feature_type = feature["feature_type"]
    primary = _field_hint(metadata, 0, f"{feature_type.lower()} primary field")
    secondary = _field_hint(metadata, 1, f"{feature_type.lower()} secondary field")
    action = _primary_action(metadata, f"{feature_type.lower()} submit action")

    is_sauce_demo = "saucedemo" in _normalize_text(url)
    if is_sauce_demo:
        if feature_type == "AUTHENTICATION":
            if category == "invalid_input":
                steps = [
                    ("input", "username input", "locked_out_user"),
                    ("input", "password input", "secret_sauce"),
                    ("click", "login button", None),
                    ("verify", "error message", None),
                ]
            else:
                steps = [
                    ("input", "username input", "standard_user"),
                    ("input", "password input", "secret_sauce"),
                    ("click", "login button", None),
                    ("verify", "inventory page", None),
                ]
            return [_step(action_name, target, value=value, feature=feature, objective_id=objective_id, objective_name=objective_name, scenario=scenario, coverage_level=coverage_level) for action_name, target, value in steps]
        if feature_type == "INVENTORY":
            steps = [
                ("click", "add to cart", None),
                ("verify", "cart badge", None),
                ("click", "cart link", None),
                ("verify", "cart page", None),
            ]
            return [_step(action_name, target, value=value, feature=feature, objective_id=objective_id, objective_name=objective_name, scenario=scenario, coverage_level=coverage_level) for action_name, target, value in steps]
        if feature_type == "CHECKOUT":
            steps = [
                ("click", "cart link", None),
                ("click", "checkout button", None),
                ("input", "first name input", "Test"),
                ("input", "last name input", "User"),
                ("input", "zip/postal input", "12345"),
                ("click", "continue button", None),
                ("click", "finish button", None),
                ("verify", "order confirmation", None),
            ]
            return [_step(action_name, target, value=value, feature=feature, objective_id=objective_id, objective_name=objective_name, scenario=scenario, coverage_level=coverage_level) for action_name, target, value in steps]
        if feature_type == "CART":
            steps = [
                ("click", "cart link", None),
                ("verify", "cart page", None),
                ("verify", "selected item", None),
            ]
            return [_step(action_name, target, value=value, feature=feature, objective_id=objective_id, objective_name=objective_name, scenario=scenario, coverage_level=coverage_level) for action_name, target, value in steps]

    common: Dict[str, List[Tuple[str, str, Optional[str]]]] = {
        "valid_input": [("input", primary, "valid_user"), ("input", secondary, "valid_password"), ("click", action, None), ("verify", "successful state", None)],
        "invalid_input": [("input", primary, "invalid_user"), ("input", secondary, "invalid_password"), ("click", action, None), ("verify", "validation error", None)],
        "empty_fields": [("click", action, None), ("verify", "required field validation", None)],
        "boundary_values": [("input", primary, "a"), ("input", secondary, "x" * 128), ("click", action, None), ("verify", "safe validation response", None)],
        "locked_accounts": [("input", primary, "locked_user"), ("input", secondary, "locked_password"), ("click", action, None), ("verify", "locked account message", None)],
        "session_handling": [("click", action, None), ("verify", "session is maintained", None), ("navigate", "protected route", None), ("verify", "protected route state", None)],
        "logout_validation": [("click", "logout action", None), ("verify", "logged out state", None), ("navigate", "protected route", None), ("verify", "access denied after logout", None)],
        "sql_injection": [("input", primary, "' OR '1'='1"), ("input", secondary, "password"), ("click", action, None), ("verify", "injection rejected", None)],
        "xss_attempts": [("input", primary, "<script>alert(1)</script>"), ("input", secondary, "password"), ("click", action, None), ("verify", "script payload escaped", None)],
        "required_fields": [("click", action, None), ("verify", "required field validation", None)],
        "invalid_formats": [("input", primary, "invalid-format"), ("click", action, None), ("verify", "format validation", None)],
        "boundary_lengths": [("input", primary, "x" * 128), ("click", action, None), ("verify", "length validation", None)],
        "empty_submission": [("click", action, None), ("verify", "empty submission blocked", None)],
        "partial_submission": [("input", primary, "partial value"), ("click", action, None), ("verify", "missing field validation", None)],
        "duplicate_submission": [("input", primary, "duplicate value"), ("click", action, None), ("click", action, None), ("verify", "duplicate submission prevented", None)],
        "valid_searches": [("input", primary, "test"), ("click", action, None), ("verify", "search results", None)],
        "empty_searches": [("input", primary, ""), ("click", action, None), ("verify", "empty search state", None)],
        "special_characters": [("input", primary, "!@#$%^&*"), ("click", action, None), ("verify", "safe search response", None)],
        "large_input": [("input", primary, "query" * 64), ("click", action, None), ("verify", "stable search response", None)],
        "no_result_scenarios": [("input", primary, "zzzz-no-result-value"), ("click", action, None), ("verify", "no results state", None)],
        "pagination": [("click", "next page control", None), ("verify", "table page changed", None)],
        "sorting": [("click", "sortable column header", None), ("verify", "table sorted state", None)],
        "filtering": [("input", "table filter", "active"), ("verify", "filtered table rows", None)],
        "row_actions": [("click", "first row action", None), ("verify", "row action result", None)],
        "menu_consistency": [("click", _nav_link_target(metadata, action), None), ("verify", "page title", "visible")],
        "broken_links": [("click", _nav_link_target(metadata, "primary navigation link"), None), ("verify", "page title", "visible")],
        "browser_back_forward": [("click", _nav_link_target(metadata, "primary navigation link"), None), ("navigate", "browser back", None), ("verify", "page title", "visible")],
        "deep_links": [("navigate", "deep link route", None), ("verify", "page title", "visible")],
        "complete_workflow": [("click", action, None), ("input", primary, "Test"), ("input", secondary, "User"), ("click", "continue action", None), ("verify", "transaction confirmation", None)],
        "validation_failures": [("click", action, None), ("verify", "checkout validation error", None)],
        "partial_completion": [("click", action, None), ("input", primary, "Partial"), ("verify", "checkout progress preserved", None)],
        "recovery_scenarios": [("click", action, None), ("click", "browser back", None), ("verify", "checkout recovery state", None)],
        "positive_path": [("click", action, None), ("verify", "expected state achieved", None)],
    }
    steps = common.get(category, [("verify", f"{feature_type.lower()} state", None)])
    return [_step(action_name, target, value=value, feature=feature, objective_id=objective_id, objective_name=objective_name, scenario=scenario, coverage_level=coverage_level) for action_name, target, value in steps]


def _scenario_applies(scenario: Dict[str, Any], coverage_level: str, metadata: Dict[str, Any]) -> bool:
    if _coverage_depth(scenario["level"]) > _coverage_depth(coverage_level):
        return False
    if scenario["category"] in {"pagination", "sorting", "filtering", "row_actions"}:
        return bool(metadata.get("tables")) or coverage_level in {"deep", "aggressive"}
    if scenario["category"] in {"required_fields", "invalid_formats", "boundary_lengths", "empty_submission", "partial_submission", "duplicate_submission"}:
        return bool(metadata.get("forms")) or coverage_level in {"deep", "aggressive"}
    return True


def _scenario_priority_tuple(item: Dict[str, Any]) -> tuple[int, int, str]:
    feature_key = str(item.get("feature_key") or item.get("feature_type") or "").upper()
    auth_priority = 0 if feature_key == "AUTHENTICATION" else 1
    risk_score = int(item.get("risk_score", 0) or 0)
    name = str(item.get("scenario_name") or "")
    return (auth_priority, -risk_score, name)


def _objective_priority_tuple(item: Dict[str, Any]) -> tuple[int, int, str]:
    feature_key = str(item.get("feature_key") or "").upper()
    auth_priority = 0 if feature_key == "AUTHENTICATION" else 1
    risk_score = int(item.get("risk_score", 0) or 0)
    name = str(item.get("objective_name") or "")
    return (auth_priority, -risk_score, name)


def _apply_scenario_budget(
    scenario_cases: List[Dict[str, Any]],
    objective_tracking: List[Dict[str, Any]],
    max_scenarios: int,
    min_risk_score: int,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], bool]:
    if max_scenarios <= 0:
        max_scenarios = 20

    filtered = [case for case in scenario_cases if int(case.get("risk_score", 0) or 0) >= min_risk_score]
    if not filtered:
        filtered = list(scenario_cases)

    filtered.sort(key=_scenario_priority_tuple)
    if len(filtered) <= max_scenarios:
        return filtered, objective_tracking, False

    by_objective: Dict[str, List[Dict[str, Any]]] = {}
    for case in filtered:
        objective_id = str(case.get("objective_id") or "")
        by_objective.setdefault(objective_id, []).append(case)

    selected: List[Dict[str, Any]] = []
    selected_ids: set[str] = set()
    for objective in sorted(objective_tracking, key=_objective_priority_tuple):
        if len(selected) >= max_scenarios:
            break
        objective_id = str(objective.get("objective_id") or "")
        candidates = by_objective.get(objective_id) or []
        if not candidates:
            continue
        candidate = sorted(candidates, key=_scenario_priority_tuple)[0]
        scenario_id = str(candidate.get("scenario_id") or "")
        if scenario_id in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(scenario_id)

    for case in filtered:
        if len(selected) >= max_scenarios:
            break
        scenario_id = str(case.get("scenario_id") or "")
        if scenario_id in selected_ids:
            continue
        selected.append(case)
        selected_ids.add(scenario_id)

    selected_by_objective: Dict[str, List[Dict[str, Any]]] = {}
    for case in selected:
        selected_by_objective.setdefault(str(case.get("objective_id") or ""), []).append(case)

    updated_tracking: List[Dict[str, Any]] = []
    for objective in objective_tracking:
        objective_id = str(objective.get("objective_id") or "")
        picked = selected_by_objective.get(objective_id, [])
        scenario_rows = [
            {
                "scenario_id": scenario.get("scenario_id"),
                "scenario_name": scenario.get("scenario_name"),
                "category": scenario.get("category") or scenario.get("scenario_category"),
                "coverage_level": scenario.get("coverage_level"),
                "risk_score": scenario.get("risk_score"),
                "risk_level": scenario.get("risk_level"),
                "generated_steps": int(
                    scenario.get("generated_steps", len(scenario.get("steps") or []))
                    or len(scenario.get("steps") or [])
                ),
                "execution_status": scenario.get("execution_status", "pending"),
                "depends_on": scenario.get("depends_on") or [],
                "required_state": scenario.get("required_state") or [],
                "produces_state": scenario.get("produces_state") or [],
                "required_page": scenario.get("required_page"),
            }
            for scenario in picked
        ]
        updated = dict(objective)
        updated["scenarios"] = scenario_rows
        updated["generated_scenarios"] = len(scenario_rows)
        updated["generated_steps"] = sum(
            int(case.get("generated_steps", len(case.get("steps") or [])) or len(case.get("steps") or []))
            for case in picked
        )
        updated_tracking.append(updated)

    return selected, updated_tracking, True


def expand_scenarios(url: str, instruction: str, dom: Dict[str, Any], discovery: Dict[str, Any] | None = None) -> Dict[str, Any]:
    discovery = discovery or {"feature_map": [], "workflows": [], "forms": [], "pages": [], "discovered_pages": []}
    if _is_workflow_instruction(instruction):
        workflow_plan = _expand_workflow_scenarios(url, instruction, dom, discovery)
        if workflow_plan is not None:
            return workflow_plan
    default_coverage = _coverage_for_instruction(instruction)
    focused_features = set(_focused_feature_types(instruction))
    features = _discovered_features(instruction, dom, discovery)

    scenario_cases: List[Dict[str, Any]] = []
    objective_tracking: List[Dict[str, Any]] = []
    feature_profiles: List[Dict[str, Any]] = []
    combined_steps: List[Dict[str, Any]] = []
    tree_features: List[Dict[str, Any]] = []

    for index, feature in enumerate(features, start=1):
        feature_type = feature["feature_type"]
        objective_id = f"obj_{index}"
        objective_name = feature.get("feature_name") or _title(feature_type)
        explicitly_requested = "instruction_requested" in (feature.get("sources") or [])
        coverage_level = "aggressive" if feature_type in focused_features else default_coverage
        if explicitly_requested and _coverage_depth(coverage_level) < _coverage_depth("deep"):
            coverage_level = "deep"
        if feature_type in {"AUTHENTICATION", "CHECKOUT", "PAYMENT", "PERMISSIONS", "UPLOADS", "APIS"} and _coverage_depth(coverage_level) < _coverage_depth("deep"):
            coverage_level = "deep"
        workflows = _workflow_matches(feature_type, discovery)
        forms = _forms_for_feature(feature_type, discovery)
        tables = _tables_for_feature(feature_type, discovery)
        actions = _actions_for_feature(feature_type, dom, discovery)
        metadata = {
            "feature_type": feature_type,
            "evidence": list(dict.fromkeys(feature.get("evidence", [])))[:8],
            "sources": list(dict.fromkeys(feature.get("sources", [])))[:8],
            "available_actions": actions[:12],
            "forms": forms[:6],
            "tables": tables[:6],
            "workflows": workflows[:6],
            "validation_requirements": _validation_requirements(feature_type, forms, workflows),
        }
        feature_risk_score, risk_factors = _feature_risk(feature_type, coverage_level, metadata, feature_type in focused_features)

        scenarios: List[Dict[str, Any]] = []
        scenario_tracking: List[Dict[str, Any]] = []
        objective_steps: List[Dict[str, Any]] = []
        for catalog_item in SCENARIO_CATALOG[feature_type]:
            if not _scenario_applies(catalog_item, coverage_level, metadata):
                continue
            scenario_risk = min(100, int(round((feature_risk_score * 0.45) + (int(catalog_item["risk"]) * 0.55))))
            scenario_id = f"{objective_id}_s{len(scenarios) + 1}"
            scenario = {
                "scenario_id": scenario_id,
                "scenario_name": f"{objective_name} - {catalog_item['name']}",
                "category": catalog_item["category"],
                "feature_type": feature_type,
                "coverage_level": coverage_level,
                "coverage_profile": _coverage_profile(coverage_level),
                "min_coverage_level": catalog_item["level"],
                "risk_score": scenario_risk,
                "risk_level": _risk_level(scenario_risk),
                "validation_requirements": catalog_item.get("validations", []),
                "execution_status": "pending",
            }
            scenario.update(_scenario_dependency_profile(feature_type, scenario, objective_name))
            steps = _scenario_steps(feature, metadata, objective_id, objective_name, scenario, coverage_level, url)
            scenario["generated_steps"] = len(steps)
            scenarios.append(scenario)
            scenario_tracking.append({key: scenario[key] for key in ["scenario_id", "scenario_name", "category", "coverage_level", "risk_score", "risk_level", "generated_steps", "execution_status", "depends_on", "required_state", "produces_state", "required_page"]})
            objective_steps.extend(steps)
            combined_steps.extend(steps)
            scenario_cases.append(
                {
                    "title": scenario["scenario_name"],
                    "expected": f"{scenario['scenario_name']} validates: {', '.join(scenario['validation_requirements'])}.",
                    "objective_id": objective_id,
                    "objective_name": objective_name,
                    "feature_key": feature_type,
                    "coverage_level": coverage_level,
                    "scenario_id": scenario_id,
                    "scenario_name": scenario["scenario_name"],
                    "category": scenario["category"],
                    "scenario_category": scenario["category"],
                    "generated_steps": len(steps),
                    "coverage_profile": scenario["coverage_profile"],
                    "risk_score": scenario["risk_score"],
                    "risk_level": scenario["risk_level"],
                    "depends_on": scenario["depends_on"],
                    "required_state": scenario["required_state"],
                    "produces_state": scenario["produces_state"],
                    "required_page": scenario["required_page"],
                    "steps": steps,
                }
            )

        objective_tracking.append(
            {
                "objective_id": objective_id,
                "objective_name": objective_name,
                "feature_key": feature_type,
                "feature_name": objective_name,
                "feature_type": feature_type,
                "coverage_level": coverage_level,
                "coverage_profile": _coverage_profile(coverage_level),
                "priority_score": feature_risk_score,
                "risk_score": feature_risk_score,
                "risk_level": _risk_level(feature_risk_score),
                "risk_factors": risk_factors,
                "generated_scenarios": len(scenarios),
                "generated_steps": len(objective_steps),
                "execution_status": "pending",
                "scenarios": scenario_tracking,
            }
        )
        feature_profiles.append(
            {
                "objective_id": objective_id,
                "feature_key": feature_type,
                "feature_name": objective_name,
                "feature_type": feature_type,
                "coverage_level": coverage_level,
                "coverage_profile": _coverage_profile(coverage_level),
                "priority_score": feature_risk_score,
                "risk_score": feature_risk_score,
                "risk_level": _risk_level(feature_risk_score),
                "risk_factors": risk_factors,
            }
        )
        tree_features.append(
            {
                "objective_id": objective_id,
                "feature_key": feature_type,
                "feature_name": objective_name,
                "feature_type": feature_type,
                "coverage_level": coverage_level,
                "coverage_profile": _coverage_profile(coverage_level),
                "risk_score": feature_risk_score,
                "risk_level": _risk_level(feature_risk_score),
                "metadata": metadata,
                "scenarios": scenarios,
            }
        )

    objective_tracking.sort(key=_objective_priority_tuple)
    feature_profiles.sort(key=lambda item: (0 if str(item.get("feature_key") or "").upper() == "AUTHENTICATION" else 1, -int(item.get("risk_score", 0) or 0), str(item.get("feature_name") or "")))
    tree_features.sort(key=lambda item: (0 if str(item.get("feature_key") or "").upper() == "AUTHENTICATION" else 1, -int(item.get("risk_score", 0) or 0), str(item.get("feature_name") or "")))
    scenario_cases.sort(key=_scenario_priority_tuple)

    scenario_cases, objective_tracking, scenario_cap_applied = _apply_scenario_budget(
        scenario_cases,
        objective_tracking,
        max_scenarios=MAX_SCENARIOS,
        min_risk_score=MIN_SCENARIO_RISK_SCORE,
    )

    selected_scenario_ids = {str(item.get("scenario_id") or "") for item in scenario_cases}
    combined_steps = [
        step
        for step in combined_steps
        if str(step.get("scenario_id") or "") in selected_scenario_ids
    ]

    coverage_counts = Counter(item["coverage_level"] for item in objective_tracking)
    feature_type_counts = Counter(item["feature_type"] for item in feature_profiles)
    risk_counts = Counter(item["risk_level"] for item in feature_profiles)
    scenario_risk_counts = Counter(item.get("risk_level") for item in scenario_cases if item.get("risk_level"))
    risk_summary = {
        "critical_features": risk_counts.get("critical", 0),
        "high_features": risk_counts.get("high", 0),
        "medium_features": risk_counts.get("medium", 0),
        "low_features": risk_counts.get("low", 0),
        "critical_scenarios": scenario_risk_counts.get("critical", 0),
        "high_scenarios": scenario_risk_counts.get("high", 0),
        "medium_scenarios": scenario_risk_counts.get("medium", 0),
        "low_scenarios": scenario_risk_counts.get("low", 0),
    }
    metrics = {
        "requested_objectives": len(features),
        "planned_objectives": len(objective_tracking),
        "generated_scenarios": sum(item.get("generated_scenarios", 0) for item in objective_tracking),
        "generated_steps": len(combined_steps),
        "coverage_profile_counts": {level: coverage_counts.get(level, 0) for level in COVERAGE_LEVELS},
        "feature_type_counts": dict(feature_type_counts),
        "risk_level_counts": dict(risk_counts),
        "focused_features": sorted(focused_features),
        "max_scenarios": MAX_SCENARIOS,
        "min_scenario_risk_score": MIN_SCENARIO_RISK_SCORE,
        "scenario_cap_applied": scenario_cap_applied,
        "risk_summary": risk_summary,
        "dependency_graph": {
            "nodes": [scenario.get("scenario_id") for scenario in scenario_cases],
            "edges": [
                {
                    "from": dependency,
                    "to": scenario.get("scenario_id"),
                }
                for scenario in scenario_cases
                for dependency in scenario.get("depends_on", [])
            ],
        },
    }
    scenario_tree = {
        "coverage_levels": list(COVERAGE_LEVELS),
        "coverage_profiles": {level: _coverage_profile(level) for level in COVERAGE_LEVELS},
        "default_coverage_level": default_coverage,
        "focus_overrides": {feature_type: "aggressive" for feature_type in sorted(focused_features)},
        "features": tree_features,
        "summary": metrics,
    }
    combined_case = {
        "title": "Risk-Based Feature Scenario Suite",
        "expected": "All generated scenarios are executed with continue-on-failure behavior.",
        "steps": combined_steps,
        "objective_tracking": objective_tracking,
        "plan_metrics": metrics,
        "scenario_tree": scenario_tree,
    }
    return {
        "url": url,
        "instruction": instruction,
        "page_title": str(dom.get("title") or "AI Generated Test"),
        "summary": "Dynamic risk-based scenario suite generated successfully.",
        "source": "dynamic_risk_scenario_expansion",
        "status": "ready" if metrics["generated_scenarios"] else "failed",
        "failure_reason": "scenario_expansion_empty" if not metrics["generated_scenarios"] else None,
        "discovery": discovery,
        "requested_objectives": [feature.get("feature_name") or feature.get("feature_type") for feature in features],
        "planned_objectives": [item.get("objective_name") for item in objective_tracking],
        "feature_profiles": feature_profiles,
        "objective_tracking": objective_tracking,
        "scenario_tree": scenario_tree,
        "plan_metrics": metrics,
        "test_case": combined_case,
        "test_cases": scenario_cases,
        "scenario_cases": scenario_cases,
        "raw_plan": {"dom": dom, "discovery": discovery},
    }

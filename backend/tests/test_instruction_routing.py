"""
Tests for AI-Workspace intent routing.

Covers:
  - _is_instruction_request (service-layer classifier)
  - _is_instruction_intent  (intelligence-layer routing guard)
  - resolve_entity_query does NOT route instruction queries to test_run_analysis

Run with:
    python -m pytest backend/tests/test_instruction_routing.py -v
"""
from __future__ import annotations

import sys
import os
from typing import Any, Dict
from unittest.mock import MagicMock, patch

import pytest

# ── make sure the project root is on sys.path ───────────────────────────────
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers: import the real modules, but stub out MongoDB so tests are offline.
# ─────────────────────────────────────────────────────────────────────────────

def _make_empty_collection():
    col = MagicMock()
    col.find.return_value = []
    col.find_one.return_value = None
    return col


_MONGO_STUBS = {
    "backend.database.mongo": MagicMock(
        collection=_make_empty_collection(),
        bug_collection=_make_empty_collection(),
        ai_memory_collection=_make_empty_collection(),
        users_collection=_make_empty_collection(),
        ai_chat_sessions=_make_empty_collection(),
        ai_chat_messages=_make_empty_collection(),
        ai_knowledge_index=_make_empty_collection(),
        report_export_collection=_make_empty_collection(),
        selector_cache_collection=_make_empty_collection(),
    ),
    "backend.database.report_repository": MagicMock(
        get_report=MagicMock(return_value=None),
        list_reports_for_user=MagicMock(return_value=[]),
    ),
    "backend.services.run_comparison_service": MagicMock(
        compare_runs=MagicMock(return_value={"summary": "ok"}),
    ),
    "backend.ai_workspace.memory": MagicMock(
        memory_engine=MagicMock(
            list_sessions=MagicMock(return_value=[]),
            get_or_create_session=MagicMock(),
            get_session_history=MagicMock(return_value=[]),
            list_memories=MagicMock(return_value=[]),
            save_message=MagicMock(),
        ),
    ),
    "backend.ai_workspace.retrieval": MagicMock(
        retrieval_system=MagicMock(
            get_context=MagicMock(return_value={"intent": "general_chat", "data": [], "summary": ""}),
            retrieve_reports=MagicMock(return_value=[]),
            retrieve_bugs=MagicMock(return_value=[]),
        ),
    ),
    "openai": MagicMock(),
    "groq": MagicMock(),
}

for _mod, _stub in _MONGO_STUBS.items():
    sys.modules[_mod] = _stub


# ── Now it is safe to import the real modules ────────────────────────────────
from backend.ai_workspace.service import AIWorkspaceService      # noqa: E402
from backend.ai_workspace.intelligence import (                  # noqa: E402
    _is_instruction_intent,
    resolve_entity_query,
)

svc = AIWorkspaceService()


# ─────────────────────────────────────────────────────────────────────────────
# Part 1 – service-layer classifier: _is_instruction_request
# ─────────────────────────────────────────────────────────────────────────────

INSTRUCTION_TRUE_CASES = [
    # Required by the specification
    "Generate instructions for SauceDemo",
    "Generate me an instruction",
    "Create AI testing instructions",
    "Write test instructions for login flow",
    "Generate a Run Test prompt",
    # Additional natural-language variants
    "Create test instructions",
    "Write testing instructions",
    "Build a test plan",
    "Generate a prompt",
    "Create test scenarios",
    # Legacy phrases
    "generate instruction",
    "generate instructions",
    "create instruction",
    "test objective",
    # Case-insensitive
    "GENERATE Instructions FOR login",
    "BUILD A TEST PLAN",
    # Extra filler words
    "Please generate me some testing instructions",
    "Can you draft a test scenario for checkout?",
    "Make a prompt for SauceDemo",
    "Compose an instruction template for authentication",
    "Write a plan for regression testing",
    "Give me an instruction for the login page",
    "produce a test plan for checkout",
]

INSTRUCTION_FALSE_CASES = [
    # Run-analysis queries – must NOT be classified as instruction requests
    "Show me the latest run",
    "What is the status of the last test run?",
    "Summarize the latest test run",
    "Show me test run details",
    "Analyze the most recent test",
    # Bug queries
    "Show me critical bugs",
    "List open bugs",
    # Screenshot / report
    "Show latest screenshot",
    "Give me the report",
    # Memory
    "remember that my project is SauceDemo",
    "show my memories",
    # Generic
    "hello",
    "what can you do?",
    # Workflow (should NOT be classified as instruction)
    "generate a workflow for login",
    "build a workflow",
]


@pytest.mark.parametrize("query", INSTRUCTION_TRUE_CASES)
def test_service_classifier_true(query: str):
    assert svc._is_instruction_request(query) is True, (
        f"Expected True for: {query!r}"
    )


@pytest.mark.parametrize("query", INSTRUCTION_FALSE_CASES)
def test_service_classifier_false(query: str):
    assert svc._is_instruction_request(query) is False, (
        f"Expected False for: {query!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Part 2 – intelligence-layer guard: _is_instruction_intent
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("query", INSTRUCTION_TRUE_CASES)
def test_intelligence_guard_true(query: str):
    assert _is_instruction_intent(query.lower()) is True, (
        f"_is_instruction_intent expected True for: {query!r}"
    )


@pytest.mark.parametrize("query", INSTRUCTION_FALSE_CASES)
def test_intelligence_guard_false(query: str):
    assert _is_instruction_intent(query.lower()) is False, (
        f"_is_instruction_intent expected False for: {query!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Part 3 – resolve_entity_query routing correctness
# ─────────────────────────────────────────────────────────────────────────────

ROUTING_INSTRUCTION_CASES = [
    "Generate instructions for SauceDemo",
    "Generate me an instruction",
    "Create AI testing instructions",
    "Write test instructions for login flow",
    "Generate a Run Test prompt",
    "Build a test plan",
    "Create test scenarios",
]

ROUTING_RUN_CASES = [
    "Show me the latest run",
    "What is the status of the last test run?",
    "Analyze the most recent test",
]

ROUTING_BUG_CASES = [
    "Show me critical bugs",
    "List open bugs",
]

ROUTING_SCREENSHOT_CASES = [
    "Show latest screenshot",
    "Show me the visual for run 3",
]


_FAKE_USER = "test-user-routing"


@pytest.mark.parametrize("query", ROUTING_INSTRUCTION_CASES)
def test_routing_instruction_never_goes_to_run_analysis(query: str):
    """Instruction queries must NOT route to test_run_analysis."""
    result = resolve_entity_query(_FAKE_USER, query)
    assert result["intent"] != "test_run_analysis", (
        f"Instruction query routed incorrectly as test_run_analysis: {query!r}"
    )
    assert result["intent"] == "general_chat", (
        f"Expected general_chat for instruction query, got {result['intent']!r}: {query!r}"
    )


@pytest.mark.parametrize("query", ROUTING_RUN_CASES)
def test_routing_run_analysis_still_works(query: str):
    """Run-analysis queries must still reach test_run_analysis."""
    result = resolve_entity_query(_FAKE_USER, query)
    assert result["intent"] == "test_run_analysis", (
        f"Expected test_run_analysis, got {result['intent']!r}: {query!r}"
    )


@pytest.mark.parametrize("query", ROUTING_BUG_CASES)
def test_routing_bug_analysis_still_works(query: str):
    """Bug queries must still reach query_bugs."""
    result = resolve_entity_query(_FAKE_USER, query)
    assert result["intent"] == "query_bugs", (
        f"Expected query_bugs, got {result['intent']!r}: {query!r}"
    )


@pytest.mark.parametrize("query", ROUTING_SCREENSHOT_CASES)
def test_routing_screenshot_analysis_still_works(query: str):
    """Screenshot queries must still reach screenshot_analysis."""
    result = resolve_entity_query(_FAKE_USER, query)
    assert result["intent"] == "screenshot_analysis", (
        f"Expected screenshot_analysis, got {result['intent']!r}: {query!r}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# Part 4 – _instruction_topic_from_query extracts a clean topic
# ─────────────────────────────────────────────────────────────────────────────

TOPIC_CASES = [
    ("Generate instructions for SauceDemo", "SauceDemo"),
    ("Write test instructions for login flow", "login flow"),
    ("Create AI testing instructions for checkout", "checkout"),
    ("Build a test plan for authentication", "authentication"),
]


@pytest.mark.parametrize("query,expected_topic", TOPIC_CASES)
def test_topic_extraction(query: str, expected_topic: str):
    topic = svc._instruction_topic_from_query(query)
    assert expected_topic.lower() in topic.lower(), (
        f"Expected topic to contain {expected_topic!r}, got {topic!r}"
    )

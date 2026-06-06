import unittest
from unittest.mock import AsyncMock, patch

from backend.ai.schema.test_plan_schema import Step, TestCase
from backend.services import execution_service
from backend.services import test_services
from backend.services.scoring.health_score import calculate_health_score
from backend.routes import autonomous_agent_route


class FakeLocator:
    async def count(self):
        return 0


class FakePage:
    def __init__(self):
        self.url = "https://example.com/start"
        self.events = {}

    def on(self, name, handler):
        self.events[name] = handler

    async def goto(self, url, **kwargs):
        self.url = url

    def locator(self, selector):
        return FakeLocator()

    async def screenshot(self, **kwargs):
        return b"fake-png"

    async def title(self):
        return "Example"

    async def inner_text(self, selector):
        return "Example body"


class FakeBrowser:
    def __init__(self):
        self.page = FakePage()

    async def new_context(self, **kwargs):
        return self

    async def new_page(self):
        return self.page

    async def close(self):
        return None


class FakeChromium:
    def __init__(self):
        self.browser = FakeBrowser()

    async def launch(self, **kwargs):
        return self.browser


class FakePlaywright:
    def __init__(self):
        self.chromium = FakeChromium()

    async def start(self):
        return self

    async def stop(self):
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class ContinueOnFailureExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_five_step_workflow_continues_after_step_three_failure(self):
        executed_selectors = []
        progress_events = []

        async def progress_callback(event):
            progress_events.append(event)

        async def fake_safe_click(page, selector, **kwargs):
            executed_selectors.append(selector)
            if selector == "#step-3":
                raise RuntimeError("intentional step 3 failure")

        async def fake_recovery(page, **kwargs):
            selector = kwargs.get("selector")
            return {
                "recovery_attempted": True,
                "recovery_success": False,
                "recovery_type": "generic_retry",
                "recovery_actions": [
                    {
                        "type": "generic_retry",
                        "method": "selector",
                        "selector": selector,
                        "detail": f"Retried {selector}",
                        "success": False,
                    }
                ],
                "validation": None,
                "error": kwargs.get("error_text") or "intentional step 3 failure",
            }

        test_case = TestCase(
            title="Continue on failure regression",
            expected=None,
            steps=[
                Step(action="click", target=f"Step {index}", selector=f"#step-{index}")
                for index in range(1, 6)
            ],
        )

        patches = [
            patch.object(execution_service, "async_playwright", lambda: FakePlaywright()),
            patch.object(execution_service, "safe_click", fake_safe_click),
            patch.object(execution_service, "_attempt_step_recovery", fake_recovery),
            patch.object(execution_service, "check_error_messages", AsyncMock(return_value=False)),
            patch.object(execution_service, "check_url_change", AsyncMock(return_value=False)),
            patch.object(
                execution_service,
                "get_page_snapshot",
                AsyncMock(return_value={"title": "Example", "url": "https://example.com/start"}),
            ),
            patch.object(execution_service, "is_same_domain", lambda *_args, **_kwargs: True),
        ]

        for active_patch in patches:
            active_patch.start()
            self.addCleanup(active_patch.stop)

        result = await execution_service.run_test_steps(
            url="https://example.com/start",
            test_case=test_case,
            dom={},
            progress_callback=progress_callback,
        )

        self.assertEqual(executed_selectors, ["#step-1", "#step-2", "#step-3", "#step-4", "#step-5"])
        self.assertEqual([item["status"] for item in result["results"]], ["passed", "passed", "failed", "passed", "passed"])
        self.assertEqual(result["run_status"], "completed_with_failures")
        self.assertEqual(result["total_tasks"], 5)
        self.assertEqual(result["completed_tasks"], 4)
        self.assertEqual(result["failed_tasks"], 1)
        self.assertEqual(result["skipped_tasks"], 0)
        self.assertEqual(result["recovery_attempts"], 1)
        self.assertEqual(result["successful_recoveries"], 0)
        self.assertTrue(any(event.get("type") == "screenshot" for event in progress_events))


class ScenarioReplanningEngineTests(unittest.IsolatedAsyncioTestCase):
    async def test_scenario_retries_with_alternate_selector_before_failing(self):
        scenario_case = TestCase(
            title="Login scenario",
            expected="Reach the dashboard",
            objective_id="objective-login",
            objective_name="Login objective",
            feature_key="LOGIN",
            scenario_id="scenario-login",
            scenario_name="Login scenario",
            steps=[
                Step(action="navigate", target="Login page", value="https://example.com/login"),
                Step(action="click", target="Submit", selector="#submit"),
            ],
        )

        dom = {
            "buttons": [{"text": "Sign in", "aria_label": "", "id": "signin", "name": "signin"}],
            "inputs": [{"placeholder": "Email", "name": "email", "id": "email"}],
            "links": [{"text": "Forgot password"}],
            "headings": ["Sign in"],
        }
        discovery = {
            "workflows": [{"name": "Authentication Flow", "feature_key": "LOGIN", "entry_point": "https://example.com/login"}],
            "pages": [{"url": "https://example.com/login"}],
        }

        failed_run = {
            "results": [
                {
                    "status": "fail",
                    "error": "selector not found",
                    "failure_category": "SELECTOR",
                    "root_cause": "ELEMENT_NOT_FOUND",
                    "recovery_attempted": False,
                    "recovery_actions": [],
                }
            ],
            "run_status": "failed",
        }
        recovered_run = {
            "results": [
                {"status": "passed", "recovery_attempted": False, "recovery_actions": []},
                {"status": "passed", "recovery_attempted": False, "recovery_actions": []},
            ],
            "run_status": "completed",
        }

        with patch.object(test_services, "run_test_steps", AsyncMock(side_effect=[failed_run, recovered_run])) as mocked_run:
            result = await test_services._run_scenario_with_replanning(
                url="https://example.com/login",
                scenario_case=scenario_case,
                dom=dom,
                discovery=discovery,
                progress_callback=None,
            )

        self.assertTrue(result["recovered"])
        self.assertEqual(result["recovery_attempts"], 1)
        self.assertEqual(result["recovery_strategy"]["status"], "recovered")
        self.assertEqual(result["recovery_strategy"]["selected_strategy"], "alternate_selectors")
        retry_case = mocked_run.call_args_list[1].kwargs["test_case"]
        self.assertEqual(retry_case.steps[1].target, "Sign in")


class ObjectiveCoverageScoringTests(unittest.TestCase):
    def test_critical_objective_failure_reduces_score_more_than_action_counts(self):
        objective_coverage = [
            {
                "objective_id": "obj_login",
                "objective_name": "Login",
                "feature_key": "LOGIN",
                "coverage_level": "STANDARD",
                "priority_score": 5,
                "executed_scenarios": 2,
                "passed_scenarios": 0,
                "failed_scenarios": 2,
                "execution_status": "failed",
                "critical": True,
            },
            {
                "objective_id": "obj_report",
                "objective_name": "Reports",
                "feature_key": "REPORT",
                "coverage_level": "BASIC",
                "priority_score": 1,
                "executed_scenarios": 2,
                "passed_scenarios": 2,
                "failed_scenarios": 0,
                "execution_status": "passed",
                "critical": False,
            },
        ]

        score_data = calculate_health_score([], objective_coverage=objective_coverage)

        self.assertEqual(score_data["objective_pass_rate"], 0.5)
        self.assertEqual(score_data["scenario_pass_rate"], 0.5)
        self.assertEqual(score_data["critical_objective_failures"], 1)
        self.assertLess(score_data["health_score"], score_data["coverage_score"])
        self.assertLess(score_data["health_score"], 50)


class AutonomousQaModeTests(unittest.IsolatedAsyncioTestCase):
    async def test_url_only_request_uses_autonomous_qa_pipeline(self):
        plan = {
            "discovery": {
                "feature_map": [{"feature_key": "LOGIN", "feature_name": "Login"}],
                "workflows": [{"name": "Authentication Flow", "feature_key": "LOGIN"}],
                "forms": [],
                "pages": [],
            }
        }
        run_data = {
            "status": "completed",
            "discovery": plan["discovery"],
            "objective_coverage": [],
            "insights": {"critical": [], "moderate": [], "minor": []},
            "bugs": [],
            "recommendations": [],
            "report": "Autonomous QA report",
            "ai_summary": "Autonomous QA summary",
            "screenshot_paths": [],
            "health_score": 88,
            "coverage_score": 91,
            "confidence_score": 0.82,
            "objective_pass_rate": 1.0,
            "scenario_pass_rate": 1.0,
            "critical_objective_failures": 0,
        }

        with patch.object(autonomous_agent_route, "generate_autonomous_qa_plan", AsyncMock(return_value=plan)), patch.object(
            autonomous_agent_route, "create_test_run", return_value={"test_id": "test-1", "user_id": "user-1", "project": "Autonomous QA", "url": "https://example.com"}
        ), patch.object(autonomous_agent_route, "run_ai_plan_and_update", AsyncMock(return_value=run_data)):
            response = await autonomous_agent_route.autonomous_test(
                autonomous_agent_route.AgentRunRequest(url="https://example.com", goal=None),
                current_user={"user_id": "user-1"},
            )

        self.assertEqual(response["mode"], "autonomous_qa")
        self.assertEqual(response["status"], "completed")
        self.assertEqual(response["discovered_features"][0]["feature_key"], "LOGIN")
        self.assertEqual(response["test_coverage"]["coverage_score"], 91)


if __name__ == "__main__":
    unittest.main()

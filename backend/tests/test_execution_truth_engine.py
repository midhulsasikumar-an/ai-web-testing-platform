from backend.services.execution_truth_engine import STATUS_FAIL, STATUS_PASS, evaluate_test_run


def test_failed_zero_step_scenario_stays_failed():
    truth = evaluate_test_run(
        {
            "results": [
                {
                    "test": "Workflow Test Plan",
                    "status": "fail",
                    "details": "Scenario failed before any steps executed",
                    "step_results": [],
                }
            ]
        }
    )

    assert truth["overall_status"] == STATUS_FAIL
    assert truth["scenario_results"][0]["status"] == STATUS_FAIL
    assert truth["scenario_results"][0]["executed_steps"] == 0


def test_completed_zero_step_scenario_can_still_pass():
    truth = evaluate_test_run(
        {
            "results": [
                {
                    "test": "No-op Scenario",
                    "status": "completed",
                    "step_results": [],
                }
            ]
        }
    )

    assert truth["overall_status"] == STATUS_PASS
    assert truth["scenario_results"][0]["status"] == STATUS_PASS

"""
Direct harness to run the 4-step SauceDemo login scenario
and capture exactly where execution stops.

Usage: python debug_login_step_harness.py
"""
import asyncio
import json
import logging
import sys
import os
from time import perf_counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.execution_service import run_test_steps
from backend.ai.schema.test_plan_schema import TestCase, Step

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_login_harness_output.log")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s.%(msecs)03d [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8"),
    ],
)
logger = logging.getLogger("LOGIN_HARNESS")

URL = "https://www.saucedemo.com/"

LOGIN_STEPS = [
    Step(
        action="input",
        target="username input",
        selector="#user-name",
        value="standard_user",
    ),
    Step(
        action="input",
        target="password input",
        selector="#password",
        value="secret_sauce",
    ),
    Step(
        action="click",
        target="login button",
        selector="#login-button",
    ),
    Step(
        action="verify",
        target="inventory page",
        selector="inventory_list",
    ),
]

login_scenario = TestCase(
    title="Login Success - Valid Input",
    expected="Successful login redirects to inventory page",
    steps=LOGIN_STEPS,
    objective_id="obj_7",
    objective_name="Login Success",
    feature_key="AUTHENTICATION",
    scenario_id="obj_7_s1",
    scenario_name="Login Success - Valid Input",
    scenario_category="valid_input",
    coverage_level="deep",
)


async def progress_collector(msg):
    t = perf_counter()
    msg_type = msg.get("type", "")
    m = msg.get("message", "")
    status = msg.get("status", "")
    step_action = ""
    step_status = ""
    if "step" in msg and isinstance(msg["step"], dict):
        step_action = msg["step"].get("action", "")
        step_status = msg.get("status", "")

    line = f"[{msg_type}] {m}"
    if status:
        line += f"  status={status}"
    if step_action:
        line += f"  step_action={step_action} step_status={step_status}"
    logger.info(line)


async def main():
    logger.info("=" * 70)
    logger.info("SauceDemo Login Scenario - Direct Execution Harness")
    logger.info("=" * 70)
    logger.info("URL: %s", URL)
    logger.info("Steps: %d", len(login_scenario.steps))
    for i, s in enumerate(login_scenario.steps, 1):
        logger.info("  Step %d: %s  target=%s  selector=%s  value=%s",
                     i, s.action, s.target, s.selector, s.value)
    logger.info("-" * 70)

    overall_start = perf_counter()

    try:
        result = await run_test_steps(
            url=URL,
            test_case=login_scenario,
            dom=None,
            credentials=None,
            progress_callback=progress_collector,
            shared_state={},
            session_manager=None,
        )
    except Exception as exc:
        logger.exception("run_test_steps raised an exception")
        return

    elapsed = perf_counter() - overall_start
    logger.info("=" * 70)
    logger.info("EXECUTION COMPLETE  (%.2fs)", elapsed)
    logger.info("=" * 70)

    run_status = result.get("run_status", "?")
    total_steps = result.get("total_steps", 0)
    results = result.get("results", [])
    completed_tasks = result.get("completed_tasks", 0)
    failed_tasks = result.get("failed_tasks", 0)
    skipped_tasks = result.get("skipped_tasks", 0)
    final_url = result.get("final_url", "?")
    authenticated = result.get("artifacts", {}).get("authenticated", False)

    logger.info("run_status:      %s", run_status)
    logger.info("total_steps:     %d", total_steps)
    logger.info("results count:   %d", len(results))
    logger.info("completed_tasks: %d", completed_tasks)
    logger.info("failed_tasks:    %d", failed_tasks)
    logger.info("skipped_tasks:   %d", skipped_tasks)
    logger.info("final_url:       %s", final_url)
    logger.info("authenticated:   %s", authenticated)

    logger.info("-" * 70)
    logger.info("STEP RESULTS:")
    for i, r in enumerate(results, 1):
        step = r.get("step", {})
        logger.info(
            "  Step %d: action=%s target=%s  status=%s  selector_used=%s  error=%s",
            i,
            step.get("action", "?"),
            step.get("target", "?"),
            r.get("status", "?"),
            r.get("selector_used", "?"),
            (r.get("error") or "")[:100],
        )

    if skipped_tasks > 0:
        logger.warning("!! SKIPPED TASKS DETECTED: %d of %d steps were not executed", skipped_tasks, total_steps)

    if len(results) < len(login_scenario.steps):
        logger.warning(
            "!! INCOMPLETE EXECUTION: expected %d results, got %d",
            len(login_scenario.steps),
            len(results),
        )

    report = {
        "run_status": run_status,
        "total_steps": total_steps,
        "results_count": len(results),
        "completed_tasks": completed_tasks,
        "failed_tasks": failed_tasks,
        "skipped_tasks": skipped_tasks,
        "final_url": final_url,
        "elapsed_seconds": round(elapsed, 2),
        "step_statuses": [
            {
                "action": r.get("step", {}).get("action"),
                "target": r.get("step", {}).get("target"),
                "status": r.get("status"),
                "error": (r.get("error") or "")[:200],
            }
            for r in results
        ],
    }
    report_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_login_harness_report.json")
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    logger.info("Report written to %s", report_path)
    logger.info("Full log written to %s", LOG_FILE)


if __name__ == "__main__":
    asyncio.run(main())

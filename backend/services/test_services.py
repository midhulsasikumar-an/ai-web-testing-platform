import uuid
import os
import base64
from datetime import datetime
from typing import Any, Dict, List
from backend.database.mongo import collection, db
from backend.database.report_repository import save_report
from backend.models.schema import TestRequest
from backend.services.test_runner import run_test
from backend.services.execution_service import run_test_steps
from backend.services.scoring.health_score import calculate_health_score
from backend.services.scoring.insights import generate_insights
from backend.services.scoring.recommendations import generate_recommendations
from backend.services.scoring.report_generator import generate_report
from backend.services.scoring.ai_summary import generate_summary_line
from backend.services.scoring.overall_status import calculate_overall_status
from backend.services.bug_services import create_bugs_from_test
from backend.ai.schema.test_plan_schema import TestCase
from backend.services.dom_service import extract_page_elements
from backend.services.action_translation_service import translate_test_case

def create_test_run(req: TestRequest, user_id: str):
    test_id = str(uuid.uuid4())

    test_data = {
        "user_id": user_id,
        "execution_id": test_id,
        "test_id": test_id,
        "url": req.url,
        "project": req.project_name,
        "test_type": req.test_type,
        "status": "running",
        "results": [],
        "stream_logs": [],
        "screenshot": None,
        "summary": None,
        "health_score": None,
        "overall_status": None,
        "insights": None,
        "priority_issues": [],
        "recommendations": [],
        "report": None,
        "ai_summary": None,
        "bugs": [],
        "ai_plan": req.ai_plan,
        "created_at": datetime.utcnow().isoformat()
    }

    collection.insert_one(test_data)
    db["artifacts"].insert_one({
        "user_id": user_id,
        "execution_id": test_id,
        "test_id": test_id,
        "kind": "test_run",
        "created_at": datetime.utcnow().isoformat(),
    })

    return test_data

def run_test_and_update(test_data, url, user_id: str):
    try:
        results, artifacts = run_test(url, test_data["test_id"], user_id=user_id)

        # attach results
        test_data["results"] = results
        test_data["artifacts"] = artifacts
        test_data["status"] = "completed"

        # integrate existing scoring/reporting pipeline but prefer WebsiteHealthService output if present
        # generate legacy score as fallback
        try:
            score_data = calculate_health_score(results)
            test_data["summary"] = score_data["summary"]
            test_data["health_score"] = score_data["score"]
        except Exception:
            test_data["summary"] = None
            test_data["health_score"] = 0

        # Run AI layer insights and report generation (existing helpers)
        insights = generate_insights(results)
        test_data["insights"] = insights

        overall_status = calculate_overall_status(results, insights, test_data.get("health_score", 0))
        test_data["overall_status"] = overall_status

        # --- Recommendations, report, summary line ---
        recommendations = generate_recommendations(insights)
        test_data["recommendations"] = recommendations

        report = generate_report(
            test_data.get("health_score", 0),
            test_data.get("summary"),
            insights
        )
        test_data["report"] = report

        summary_line = generate_summary_line(
            test_data.get("health_score", 0),
            test_data.get("summary"),
            insights
        )
        test_data["ai_summary"] = summary_line

        # Create bug documents from insights
        created_bugs = create_bugs_from_test(test_data)
        test_data["bugs"] = [bug["bug_id"] for bug in created_bugs]

        # Build a frontend-friendly ai_report (ensure screenshots are accessible via /artifacts)
        artifacts_folder = f"artifacts/{test_data['test_id']}"
        screenshot_urls = []
        for path in (artifacts.get("screenshots") or []):
            filename = os.path.basename(path)
            screenshot_urls.append(f"/artifacts/{test_data['test_id']}/{filename}")

        ai_report = {
            "user_id": user_id,
            "execution_id": test_data["test_id"],
            "website_health_score": test_data.get("health_score", 0),
            "workflow_completion": overall_status,
            "critical_issues": len(insights.get("critical", [])),
            "warnings": len(insights.get("moderate", [])) + len(insights.get("minor", [])),
            "screenshots": screenshot_urls,
            "report": report,
            "insights": insights,
        }

        test_data["ai_report"] = ai_report
        test_data["screenshot_paths"] = screenshot_urls

        #database update
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data}
        )

        save_report(
            test_data,
            report_type="legacy",
            user_id=user_id,
            test_run_id=test_data["test_id"],
            title=test_data.get("project") or test_data.get("test_name") or test_data["test_id"],
            summary=test_data.get("ai_summary") or test_data.get("report") or "Legacy test execution report.",
            status=test_data.get("status"),
        )

    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]
        test_data["summary"] = None
        test_data["health_score"] = 0
        test_data["ai_summary"] = "Test execution failed."
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data}
        )


def _flatten_plan_results(plan_results: List[Dict[str, Any]], case_title: str) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for index, step_result in enumerate(plan_results, start=1):
        step = step_result.get("step", {}) if isinstance(step_result, dict) else {}
        flattened.append({
            "test": f"{case_title} - Step {index}",
            "status": "pass" if step_result.get("status") != "failed" else "fail",
            "details": step_result.get("error") or step_result.get("validation") or step.get("action") or "AI step executed",
        })
    return flattened


async def run_ai_plan_and_update(test_data: Dict[str, Any], url: str, user_id: str, plan: Dict[str, Any]):
    try:
        test_case_data = plan.get("test_case") or {}
        raw_test_case = TestCase.model_validate(test_case_data)
        test_case, translation_logs = translate_test_case(raw_test_case)
        test_data["raw_ai_plan"] = test_case_data
        test_data["normalized_ai_plan"] = test_case.model_dump()
        dom = await extract_page_elements(url)
        stream_logs: List[Dict[str, Any]] = []
        screenshot_paths: List[str] = []

        def _track_screenshot_path(raw: str) -> None:
            if not raw:
                return
            normalized = raw if raw.startswith("/") else f"/{raw.lstrip('/')}"
            if normalized not in screenshot_paths:
                screenshot_paths.append(normalized)

        async def progress_callback(event: Dict[str, Any]) -> None:
            # Handle screenshot payloads specially: persist to artifacts and
            # replace base64 payload with a file path for downstream reports.
            evt = dict(event)
            if evt.get("type") == "screenshot" and evt.get("screenshot_b64"):
                try:
                    folder = f"artifacts/{test_data['test_id']}"
                    os.makedirs(folder, exist_ok=True)
                    filename = f"step-{len(stream_logs)+1}-{int(datetime.utcnow().timestamp()*1000)}.png"
                    path = os.path.join(folder, filename)
                    with open(path, "wb") as fh:
                        fh.write(base64.b64decode(evt.get("screenshot_b64")))
                    # Replace payload with a reference URL path used by frontend
                    evt["screenshot"] = f"/artifacts/{test_data['test_id']}/{filename}"
                    _track_screenshot_path(evt["screenshot"])
                    # remove the heavy base64 content
                    evt.pop("screenshot_b64", None)
                except Exception as e:
                    evt["screenshot_error"] = str(e)
            elif isinstance(evt.get("screenshot"), str):
                _track_screenshot_path(str(evt.get("screenshot")))

            stream_logs.append({
                "time": datetime.utcnow().isoformat(),
                "level": "error" if evt.get("type") == "bug_detected" else "info",
                "msg": evt.get("message", ""),
                "type": evt.get("type"),
                "details": evt,
            })
            collection.update_one(
                {"test_id": test_data["test_id"], "user_id": user_id},
                {"$set": {"stream_logs": stream_logs, "status": "running", "ai_plan": plan, "screenshot_paths": screenshot_paths}},
                upsert=True,
            )

        for entry in translation_logs:
            await progress_callback(
                {
                    "type": "action_translation",
                    "message": f"Original Action: {entry['original_action']} -> Normalized Action: {entry['normalized_action']}",
                    "details": entry,
                }
            )

        results_data = await run_test_steps(url=url, test_case=test_case, dom=dom, progress_callback=progress_callback)
        plan_results = results_data.get("results", [])
        flattened_results = _flatten_plan_results(plan_results, test_case.title or "AI Plan")

        test_data["results"] = flattened_results
        test_data["status"] = "completed"
        test_data["summary"] = {
            "total": len(flattened_results),
            "passed": sum(1 for item in flattened_results if item.get("status") == "pass"),
            "failed": sum(1 for item in flattened_results if item.get("status") == "fail"),
            "info": sum(1 for item in flattened_results if item.get("status") == "info"),
        }

        try:
            score_data = calculate_health_score(flattened_results)
            test_data["health_score"] = score_data["score"]
            test_data["summary"] = score_data["summary"]
        except Exception:
            test_data["health_score"] = 0

        insights = generate_insights(flattened_results)
        test_data["insights"] = insights
        test_data["overall_status"] = calculate_overall_status(flattened_results, insights, test_data.get("health_score", 0))
        test_data["recommendations"] = generate_recommendations(insights)
        test_data["report"] = generate_report(test_data.get("health_score", 0), test_data.get("summary"), insights)
        test_data["ai_summary"] = generate_summary_line(test_data.get("health_score", 0), test_data.get("summary"), insights)
        created_bugs = create_bugs_from_test(test_data)
        test_data["bugs"] = [bug["bug_id"] for bug in created_bugs]
        test_data["screenshot_paths"] = screenshot_paths
        test_data["ai_report"] = {
            "user_id": user_id,
            "execution_id": test_data["test_id"],
            "website_health_score": test_data.get("health_score", 0),
            "workflow_completion": test_data.get("overall_status"),
            "critical_issues": len(insights.get("critical", [])),
            "warnings": len(insights.get("moderate", [])) + len(insights.get("minor", [])),
            "screenshots": screenshot_paths,
            "report": test_data["report"],
            "insights": insights,
            "generated_plan": plan,
            "raw_ai_plan": test_case_data,
            "normalized_ai_plan": test_case.model_dump(),
        }
        test_data["stream_logs"] = stream_logs

        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data},
            upsert=True,
        )

        save_report(
            test_data,
            report_type="ai",
            user_id=user_id,
            test_run_id=test_data["test_id"],
            title=test_data.get("project") or test_case.title or test_data["test_id"],
            summary=test_data.get("ai_summary") or test_data.get("report") or "AI execution report.",
            status=test_data.get("status"),
        )
    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data},
            upsert=True,
        )
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data}
        )
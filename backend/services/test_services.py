import uuid
import os
from datetime import datetime
from backend.database.mongo import collection, db
from backend.models.schema import TestRequest
from backend.services.test_runner import run_test
from backend.services.scoring.health_score import calculate_health_score
from backend.services.scoring.insights import generate_insights
from backend.services.scoring.recommendations import generate_recommendations
from backend.services.scoring.report_generator import generate_report
from backend.services.scoring.ai_summary import generate_summary_line
from backend.services.scoring.overall_status import calculate_overall_status
from backend.services.bug_services import create_bugs_from_test

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

        #database update
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data}
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
        collection.update_one(
            {"test_id": test_data["test_id"], "user_id": user_id},
            {"$set": test_data}
        )
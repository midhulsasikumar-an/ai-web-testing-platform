import uuid
from datetime import datetime
from backend.database.mongo import collection
from backend.server import TestRequest
from backend.services.test_runner import run_test
from backend.services.scoring.health_score import calculate_health_score
from backend.services.scoring.insights import generate_insights
from backend.services.scoring.recommendations import generate_recommendations
from backend.services.scoring.report_generator import generate_report
from backend.services.scoring.ai_summary import generate_summary_line
from backend.services.scoring.overall_status import calculate_overall_status
from backend.services.bug_services import create_bugs_from_test

def create_test_run(req: TestRequest):
    test_id = str(uuid.uuid4())

    test_data = {
        "user_id": "demo-user",
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

    return test_data

def run_test_and_update(test_data, url):
    try:
        results, screenshot = run_test(url, test_data["test_id"])

        # --- Basic Results ---
        test_data["results"] = results
        test_data["screenshot"] = screenshot if screenshot else None
        test_data["status"] = "completed"

        # --- Score Calculation ---
        score_data = calculate_health_score(results)
        test_data["summary"] = score_data["summary"]
        test_data["health_score"] = score_data["score"]

        # --- AI Layer ---
        insights = generate_insights(results)
        test_data["insights"] = insights

        overall_status = calculate_overall_status(results, insights, score_data["score"])
        test_data["overall_status"] = overall_status

        # Priority Issues (flattened)
        priority_issues = []

        for issue in insights.get("critical", []):
            priority_issues.append({"level": "critical", "issue": issue})

        for issue in insights.get("moderate", []):
            priority_issues.append({"level": "moderate", "issue": issue})

        for issue in insights.get("minor", []):
            priority_issues.append({"level": "minor", "issue": issue})

        test_data["priority_issues"] = priority_issues

        # --- Recommendations ---
        recommendations = generate_recommendations(insights)
        test_data["recommendations"] = recommendations

        # --- Report ---
        report = generate_report(
            test_data["health_score"],
            test_data["summary"],
            insights
        )
        test_data["report"] = report

        # --- AI Summary Line ---
        summary_line = generate_summary_line(
            test_data["health_score"],
            test_data["summary"],
            insights
        )
        test_data["ai_summary"] = summary_line
        created_bugs = create_bugs_from_test(test_data)

        test_data["bugs"] = [
            bug["bug_id"] for bug in created_bugs
        ]

        #database update
        collection.update_one(
            {"test_id": test_data["test_id"]},
            {"$set": test_data}
        )

    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]
        test_data["summary"] = None
        test_data["health_score"] = 0
        test_data["ai_summary"] = "Test execution failed."
        collection.update_one(
            {"test_id": test_data["test_id"]},
            {"$set": test_data}
        )
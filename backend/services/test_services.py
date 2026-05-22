import uuid
from datetime import datetime
from backend.database.mongo import collection
from backend.models.schema import TestRequest
from backend.services.test_runner import run_test
from backend.services.health_score import calculate_health_score
from backend.services.insights import generate_insights
from backend.services.recommendations import generate_recommendations
from backend.services.report_generator import generate_report
from backend.services.ai_summary import generate_summary_line
from backend.services.activity_services import create_activity_event
from backend.services.collaboration_services import get_or_create_thread
from backend.database.mongo import bugs_collection

def create_test_run(req: TestRequest):
    test_id = str(uuid.uuid4())

    test_data = {
        "test_id": test_id,
        "url": req.url,
        "project": req.project_name,
        "status": "running",
        "results": [],
        "screenshot": None,
        "summary": None,
        "health_score": None,
        "insights": None,
        "priority_issues": [],
        "recommendations": [],
        "report": None,
        "ai_summary": None,
        "created_at": datetime.utcnow().isoformat()
    }

    collection.insert_one(test_data)

    user_id = "mock_user_123"  # In real app, extract from req or context
    create_activity_event(
        event_type="test_run.created",
        object_type="test_run",
        object_id=test_id,
        actor_id=user_id,
        metadata={
            "url": req.url,
            "project": req.project_name
        }
    )

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

        # --- Bug Generation ---
        user_id = "mock_user_123"
        created_bugs = []
        for res in results:
            if res.get("status") == "fail" or res.get("status") == "error":
                bug = {
                    "bug_id": str(uuid.uuid4()),
                    "test_id": test_data["test_id"],
                    "user_id": user_id,
                    "title": res.get("test", "Unknown Failure"),
                    "description": res.get("details", "No details provided"),
                    "severity": "medium",
                    "status": "open",
                    "labels": ["auto-generated", "test-failure"],
                    "assignee_id": None,
                    "watchers": [user_id],
                    "url": test_data["url"],
                    "thread_id": None,
                    "created_at": datetime.utcnow().isoformat(),
                    "updated_at": datetime.utcnow().isoformat()
                }
                
                # Auto-create thread
                thread = get_or_create_thread(
                    object_type="bug",
                    object_id=bug["bug_id"],
                    created_by=user_id
                )
                bug["thread_id"] = thread["thread_id"]
                bugs_collection.insert_one(bug)
                created_bugs.append(bug)

                create_activity_event(
                    event_type="bug.created",
                    object_type="bug",
                    object_id=bug["bug_id"],
                    actor_id=user_id,
                    metadata={
                        "title": bug["title"],
                        "severity": bug["severity"],
                        "test_id": bug["test_id"]
                    }
                )

        #database update
        collection.update_one(
            {"test_id": test_data["test_id"]},
            {"$set": test_data}
        )

        create_activity_event(
            event_type="test_run.completed",
            object_type="test_run",
            object_id=test_data["test_id"],
            actor_id=user_id,
            metadata={
                "overall_status": test_data["status"],
                "health_score": test_data.get("health_score", 0),
                "bug_count": len(created_bugs)
            }
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

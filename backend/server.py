from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import threading
from fastapi import HTTPException
from fastapi.staticfiles import StaticFiles
from backend.services.test_runner import run_test
from backend.services.health_score import calculate_health_score
from backend.services.insights import generate_insights
from backend.services.recommendations import generate_recommendations
from backend.services.report_generator import generate_report
from backend.services.ai_summary import generate_summary_line

app = FastAPI()
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

class TestRequest(BaseModel):
    url: str
    project_name: str

test_runs = []

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
        "health_score": None
    }

    test_runs.append(test_data)
    return test_data


def run_test_and_update(test_data, url):
    try:
        results, screenshot = run_test(url, test_data["test_id"])

        # --- Basic Results ---
        test_data["results"] = results
        test_data["screenshot"] = f"/{screenshot}" if screenshot else None
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

    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]
        test_data["summary"] = None
        test_data["health_score"] = 0
        test_data["ai_summary"] = "Test execution failed."
@app.get("/")
def home():
    return {"message": "Server is running 🚀"}


@app.post("/api/tests/start")
def start_test(req: TestRequest):
    test_data = create_test_run(req)
    # Run in background thread
    thread = threading.Thread(
        target=run_test_and_update,
        args=(test_data, req.url)
    )
    thread.start()

    return {
        "message": "Test started successfully",
        "data": test_data
    }


@app.get("/api/tests")
def get_tests():
    return test_runs

@app.get("/api/tests/{test_id}")
def get_test_by_id(test_id: str):
    for test in test_runs:
        if test["test_id"] == test_id:
            return test

    raise HTTPException(status_code=404, detail="Test not found")
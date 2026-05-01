from fastapi import FastAPI
from pydantic import BaseModel
import uuid
import threading
from fastapi import HTTPException
from backend.services.test_runner import run_test

app = FastAPI()

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
        "results": []
    }

    test_runs.append(test_data)
    return test_data

def run_test_and_update(test_data, url):
    try:
        results = run_test(url)
        test_data["results"] = results
        test_data["status"] = "completed"
    except Exception as e:
        test_data["status"] = "failed"
        test_data["results"] = [{"error": str(e)}]

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
from fastapi import FastAPI
from pydantic import BaseModel
import uuid
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
        "status": "started"
    }

    test_runs.append(test_data)
    return test_data


@app.get("/")
def home():
    return {"message": "Server is running 🚀"}


@app.post("/api/tests/start")
def start_test(req: TestRequest):
    test_data = create_test_run(req)
    test_results = run_test(req.url)

    test_data["results"] = test_results
    test_data["status"] = "completed"

    return {
        "message": "Test started successfully",
        "data": test_data
    }


@app.get("/api/tests")
def get_tests():
    return test_runs
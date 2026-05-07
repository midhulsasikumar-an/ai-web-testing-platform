from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schema import TestRequest

from backend.services.test_services import create_test_run, run_test_and_update
from backend.database.mongo import collection


app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later replace with frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")



@app.get("/")
def home():
    return {"message": "Server is running 🚀"}


@app.post("/api/tests/start")
def start_test(req: TestRequest, background_tasks: BackgroundTasks):
    test_data = create_test_run(req)

    background_tasks.add_task(
        run_test_and_update,
        test_data.copy(),   # to prevent mutation issues
        req.url
    )

    return {
        "message": "Test started successfully",
        "test_id": test_data["test_id"],
        "status": "running"
    }


@app.get("/api/tests")
def get_tests():
    tests = list(collection.find({}, {"_id": 0}))
    return tests

@app.get("/api/tests/{test_id}")
def get_test_by_id(test_id: str):
    test = collection.find_one({"test_id": test_id}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

    raise HTTPException(status_code=404, detail="Test not found")
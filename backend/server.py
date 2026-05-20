import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schema import TestRequest

from backend.services.test_services import create_test_run, run_test_and_update
from backend.database.mongo import collection, bug_collection
from backend.routes.dashboard import router as dashboard_router
from backend.routes.ai import router as ai_router
from backend.routes.autonomous_agent_route import router as autonomous_agent_router
from backend.routes.multi_agent import router as multi_agent_router
from backend.routes.live_execution import router as live_execution_router
from backend.routes.runtime import router as runtime_router
from backend.routes.intelligence import router as intelligence_router
from backend.ai_workspace.routes import router as ai_workspace_router

app = FastAPI()
allowed_origins = [
    origin.strip()
    for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")
app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")



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
    tests = list(collection.find({"user_id": "demo-user"}, {"_id": 0}))
    return tests

@app.get("/api/tests/{test_id}")
def get_test_by_id(test_id: str):
    test = collection.find_one({"test_id": test_id, "user_id": "demo-user"}, {"_id": 0})
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    return test

@app.get("/api/bugs")
def get_bugs():
    bugs = list(
        bug_collection.find(
            {"user_id": "demo-user"},
            {"_id": 0}
        )
    )

    return bugs

@app.get("/api/bugs/{bug_id}")
def get_bug_by_id(bug_id: str):

    bug = bug_collection.find_one(
        {
            "bug_id": bug_id,
            "user_id": "demo-user"
        },
        {"_id": 0}
    )

    if not bug:
        raise HTTPException(
            status_code=404,
            detail="Bug not found"
        )

    return bug

app.include_router(dashboard_router,prefix="/api/dashboard",tags=["Dashboard"])

app.include_router(ai_router, prefix="/ai", tags=["AI"])

app.include_router(autonomous_agent_router, prefix="/api/agent", tags=["Autonomous Agent"])
app.include_router(live_execution_router, prefix="/api/agent", tags=["Autonomous Agent Live"])
app.include_router(multi_agent_router, prefix="/api/agent", tags=["Multi-Agent Runtime"])
app.include_router(runtime_router)
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["Historical Intelligence"])
app.include_router(ai_workspace_router, prefix="/ai", tags=["AI Workspace"])

@app.on_event("startup")
async def startup_event():
    # Warm up Playwright browser for faster first request and ensure clean shutdown later
    from backend.agent.browser_session import BrowserSessionManager

    manager = BrowserSessionManager(headless=True)
    try:
        await manager.start()
    except Exception:
        pass


@app.on_event("shutdown")
async def shutdown_event():
    from backend.agent.browser_session import BrowserSessionManager

    manager = BrowserSessionManager(headless=True)
    try:
        await manager.shutdown()
    except Exception:
        pass

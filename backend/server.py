import asyncio
import os
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(
        asyncio.WindowsProactorEventLoopPolicy()
    )

from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from backend.models.schema import TestRequest

from backend.services.test_services import create_test_run, run_test_and_update
from backend.services.test_services import run_ai_plan_and_update
from backend.database.mongo import collection, bug_collection
from backend.services.bug_services import normalize_bug_record
from bson.objectid import ObjectId
from backend.services.auth import get_current_user
from backend.routes.auth_routes import router as auth_router
from backend.routes.dashboard import router as dashboard_router
from backend.routes.ai import router as ai_router
from backend.routes.autonomous_agent_route import router as autonomous_agent_router
from backend.routes.multi_agent import router as multi_agent_router
from backend.routes.live_execution import router as live_execution_router
from backend.routes.runtime import router as runtime_router
from backend.routes.intelligence import router as intelligence_router
from backend.routes.reports import router as reports_router

app = FastAPI()
allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "FRONTEND_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
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


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "ai-testing-platform-backend",
    }


@app.get("/api/health")
def api_health_check():
    return {
        "status": "ok",
        "service": "ai-testing-platform-backend",
    }


@app.post("/api/tests/start")
def start_test(req: TestRequest, background_tasks: BackgroundTasks, current_user: dict = Depends(get_current_user)):
    test_data = create_test_run(req, current_user["user_id"])

    if req.ai_plan:
        # run_ai_plan_and_update is async; ensure it is executed reliably from
        # BackgroundTasks by wrapping it in a synchronous callable that runs
        # the coroutine using asyncio.run.
        def _run_plan_sync(td=test_data.copy(), url=req.url, uid=current_user["user_id"], plan=req.ai_plan):
            import asyncio
            asyncio.run(run_ai_plan_and_update(td, url, uid, plan))

        background_tasks.add_task(_run_plan_sync)
    else:
        background_tasks.add_task(
            run_test_and_update,
            test_data.copy(),   # to prevent mutation issues
            req.url,
            current_user["user_id"]
        )

    return {
        "message": "Test started successfully",
        "test_id": test_data["test_id"],
        "status": "running"
    }


@app.get("/api/tests")
def get_tests(current_user: dict = Depends(get_current_user)):
    tests = list(collection.find({"user_id": current_user["user_id"]}, {"_id": 0}))
    return tests

@app.get("/api/tests/{test_id}")
def get_test_by_id(test_id: str, current_user: dict = Depends(get_current_user)):
    # Primary lookup by test_id
    test = collection.find_one({"test_id": test_id, "user_id": current_user["user_id"]}, {"_id": 0})

    # Fallback: some legacy records may have only _id stored; try ObjectId lookup
    if not test:
        try:
            obj = ObjectId(test_id)
            raw = collection.find_one({"_id": obj, "user_id": current_user["user_id"]})
            if raw:
                raw.pop("_id", None)
                test = raw
        except Exception:
            # not a valid ObjectId or not found — continue
            test = None

    if not test:
        raise HTTPException(status_code=404, detail="Test not found")

    return test

@app.get("/api/bugs")
def get_bugs(current_user: dict = Depends(get_current_user)):
    bugs = list(
        bug_collection.find(
            {"user_id": current_user["user_id"]},
            {"_id": 0}
        )
    )

    # Ensure all returned bugs are normalized so frontend can rely on consistent fields
    normalized = [normalize_bug_record(b) for b in bugs]
    return normalized

@app.get("/api/bugs/{bug_id}")
def get_bug_by_id(bug_id: str, current_user: dict = Depends(get_current_user)):
    # Primary lookup: bug_id field
    bug = bug_collection.find_one(
        {"bug_id": bug_id, "user_id": current_user["user_id"]}
    )

    # Fallback: try to resolve by ObjectId if bug_id was not populated
    if not bug:
        try:
            obj = ObjectId(bug_id)
            bug = bug_collection.find_one({"_id": obj, "user_id": current_user["user_id"]})
        except Exception:
            bug = None

    if not bug:
        # Last resort: try matching stringified _id field (some records store string ids)
        bug = bug_collection.find_one({"_id": bug_id, "user_id": current_user["user_id"]})

    if not bug:
        raise HTTPException(status_code=404, detail="Bug not found")

    # Normalize record shape for consistent frontend consumption
    normalized = normalize_bug_record(bug)
    return normalized

app.include_router(dashboard_router,prefix="/api/dashboard",tags=["Dashboard"])
app.include_router(auth_router)

app.include_router(ai_router, prefix="/ai", tags=["AI"])

app.include_router(autonomous_agent_router, prefix="/api/agent", tags=["Autonomous Agent"])
app.include_router(live_execution_router, prefix="/api/agent", tags=["Autonomous Agent Live"])
app.include_router(multi_agent_router, prefix="/api/agent", tags=["Multi-Agent Runtime"])
app.include_router(runtime_router)
app.include_router(intelligence_router, prefix="/api/intelligence", tags=["Historical Intelligence"])
app.include_router(reports_router, prefix="/api", tags=["Reports"])


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

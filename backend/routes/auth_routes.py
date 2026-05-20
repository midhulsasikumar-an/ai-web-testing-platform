from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid

from backend.models.schema import SignupRequest, LoginRequest
from backend.services.auth import hash_password, verify_password, create_access_token, get_current_user
from backend.database.mongo import users_collection

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/signup")
def signup(req: SignupRequest):
    """Register a new user with hashed password."""

    # Validate input
    if not req.name or len(req.name.strip()) < 2:
        raise HTTPException(status_code=400, detail="Name must be at least 2 characters")
    if not req.email or "@" not in req.email:
        raise HTTPException(status_code=400, detail="Invalid email address")
    if not req.password or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Check if email already exists
    existing = users_collection.find_one({"email": req.email.lower().strip()})
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")

    # Create user document
    user_doc = {
        "user_id": str(uuid.uuid4()),
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "password_hash": hash_password(req.password),
        "role": "user",
        "created_at": datetime.utcnow().isoformat(),
    }

    users_collection.insert_one(user_doc)
    user_id = user_doc["user_id"]

    # Generate JWT
    token = create_access_token({"sub": user_id, "user_id": user_id, "email": user_doc["email"], "name": user_doc["name"], "role": user_doc["role"]})

    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user_doc["name"],
            "email": user_doc["email"],
            "role": user_doc["role"],
        }
    }


@router.post("/login")
def login(req: LoginRequest):
    """Authenticate user and return JWT."""

    user = users_collection.find_one({"email": req.email.lower().strip()})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user_id = str(user.get("user_id") or user.get("_id"))
    token = create_access_token({"sub": user_id, "user_id": user_id, "email": user["email"], "name": user["name"], "role": user.get("role", "user")})

    return {
        "token": token,
        "user": {
            "id": user_id,
            "name": user["name"],
            "email": user["email"],
            "role": user.get("role", "user"),
        }
    }


@router.get("/me")
@router.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    """Return the current user profile from JWT."""

    return {"user": {"id": current_user["user_id"], "name": current_user["name"], "email": current_user["email"], "role": current_user.get("role", "user")}}
from fastapi import APIRouter, HTTPException, Header
from typing import Optional
from datetime import datetime

from backend.models.schema import SignupRequest, LoginRequest
from backend.services.auth import hash_password, verify_password, create_access_token, decode_access_token
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
        "name": req.name.strip(),
        "email": req.email.lower().strip(),
        "password_hash": hash_password(req.password),
        "role": "user",
        "created_at": datetime.utcnow().isoformat(),
    }

    result = users_collection.insert_one(user_doc)
    user_id = str(result.inserted_id)

    # Generate JWT
    token = create_access_token({"sub": user_id, "email": user_doc["email"], "name": user_doc["name"]})

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

    user_id = str(user["_id"])
    token = create_access_token({"sub": user_id, "email": user["email"], "name": user["name"]})

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
def get_current_user(authorization: Optional[str] = Header(None)):
    """Return the current user profile from JWT."""

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)

    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    return {
        "user": {
            "id": payload.get("sub"),
            "name": payload.get("name"),
            "email": payload.get("email"),
        }
    }

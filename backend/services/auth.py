import os
from datetime import datetime, timedelta
from passlib.context import CryptContext
from jose import JWTError, jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.database.mongo import users_collection

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# ── Password Hashing ────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

security = HTTPBearer()

def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


# ── JWT Tokens ───────────────────────────────────────────────────────

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "fallback-dev-secret-change-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
EXPIRY_HOURS = int(os.getenv("JWT_EXPIRY_HOURS", "24"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=EXPIRY_HOURS))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    return get_current_user_from_token(credentials.credentials)


def get_current_user_from_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )

        user_id = payload.get("sub") or payload.get("user_id")
        email = payload.get("email")
        if not user_id and not email:
            raise HTTPException(status_code=401, detail="Invalid token")

        query = {"user_id": user_id} if user_id else {"email": email}
        user = users_collection.find_one(query, {"_id": 0, "password_hash": 0})
        if not user:
            raise HTTPException(status_code=401, detail="Invalid token")

        if not user.get("user_id"):
            user["user_id"] = str(user.get("_id") or user_id)

        return {
            "user_id": str(user.get("user_id") or user_id or ""),
            "email": str(user.get("email") or email or ""),
            "name": str(user.get("name") or payload.get("name") or ""),
            "role": str(user.get("role") or payload.get("role") or "user"),
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Invalid token"
        )


def decode_access_token(token: str) -> dict | None:
    """Decode and validate a JWT token. Returns payload or None."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
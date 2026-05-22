from datetime import datetime, timedelta
import jwt
import bcrypt
from backend.database.mongo import users_collection
from backend.models.schema import UserCreate, UserLogin
import uuid

# Secret key for JWT (Should be in env vars in production)
SECRET_KEY = "SUPER_SECRET_PLACEHOLDER_KEY"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7 # 7 days

def verify_password(plain_password: str, hashed_password: str):
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def register_user(user: UserCreate):
    # Check if user exists
    if users_collection.find_one({"email": user.email}):
        return {"error": "Email already registered"}
    
    # Hash password and save
    hashed_password = get_password_hash(user.password)
    user_dict = {
        "user_id": str(uuid.uuid4()),
        "full_name": user.full_name,
        "email": user.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }
    users_collection.insert_one(user_dict)
    
    # Generate token
    access_token = create_access_token(
        data={"sub": user.email, "name": user.full_name}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

def authenticate_user(user: UserLogin):
    db_user = users_collection.find_one({"email": user.email})
    if not db_user:
        return {"error": "Invalid email or password"}
    if not verify_password(user.password, db_user["hashed_password"]):
        return {"error": "Invalid email or password"}
        
    access_token = create_access_token(
        data={"sub": user.email, "name": db_user["full_name"]}, expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer"}

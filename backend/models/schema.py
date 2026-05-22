from pydantic import BaseModel, EmailStr

class TestRequest(BaseModel):
    url: str
    project_name: str

class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str


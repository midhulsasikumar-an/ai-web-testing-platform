from pydantic import BaseModel, EmailStr

class TestRequest(BaseModel):
    url: str
    project_name: str
    test_type: str


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str
from pydantic import BaseModel

class TestRequest(BaseModel):
    url: str
    project_name: str
    test_type: str
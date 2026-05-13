from pydantic import BaseModel

class AIChatRequest(BaseModel):
    message: str
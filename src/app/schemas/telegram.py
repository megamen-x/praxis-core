from pydantic import BaseModel

class SendMessageRequest(BaseModel):
    user_id: int
    message: str


class SendMessageResponse(BaseModel):
    success: bool
    message: str
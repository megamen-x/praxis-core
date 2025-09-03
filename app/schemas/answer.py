# app/schemas/answer.py
from pydantic import BaseModel
from typing import Any, Dict


class SaveAnswersIn(BaseModel):
    csrf_token: str
    answers: Dict[str, Any]
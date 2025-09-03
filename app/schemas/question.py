# app/schemas/question.py
from pydantic import BaseModel
from typing import Any


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str
    is_required: bool = False
    position: int = 0
    meta: dict[str, Any] | None = None


class QuestionUpdate(BaseModel):
    question_text: str | None = None
    question_type: str | None = None
    is_required: bool | None = None
    position: int | None = None
    meta: dict | None = None
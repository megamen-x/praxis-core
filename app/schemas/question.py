# app/schemas/question.py
from pydantic import BaseModel, Field


class QuestionOptionSchema(BaseModel):
    option_text: str
    position: int = 0

class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, description="Текст вопроса не может быть пустым")
    question_type: str
    is_required: bool = False
    position: int = 0
    options: list[QuestionOptionSchema] | None = None

class QuestionUpdate(BaseModel):
    question_text: str | None = Field(None, min_length=1, description="Текст вопроса не может быть пустым")
    question_type: str | None = None 
    options: list[QuestionOptionSchema] | None = None

class ReviewQuestionLinkUpdate(BaseModel):
    is_required: bool | None = None
    position: int | None = None
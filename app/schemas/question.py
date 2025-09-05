# app/schemas/question.py
from pydantic import BaseModel
from typing import Any


class QuestionOptionSchema(BaseModel):
    option_text: str
    value: str | None = None
    position: int = 0

class QuestionCreate(BaseModel):
    question_text: str
    question_type: str
    # Эти поля теперь в связи, а не в вопросе, но они нужны при создании
    is_required: bool = False
    position: int = 0
    # Вместо meta передаем структурированные опции
    options: list[QuestionOptionSchema] | None = None

class QuestionUpdate(BaseModel):
    question_text: str | None = None
    # Тип вопроса менять не стоит после создания, но оставим на всякий случай
    question_type: str | None = None 
    options: list[QuestionOptionSchema] | None = None

class ReviewQuestionLinkUpdate(BaseModel):
    is_required: bool | None = None
    position: int | None = None
"""Pydantic-schemes for respondents' responses.
"""
# app/schemas/answer.py
from pydantic import BaseModel
from typing import List

class AnswerIn(BaseModel):
    question_id: str
    response_text: str | None = None
    selected_option_ids: List[str] | None = None

class SaveAnswersIn(BaseModel):
    csrf_token: str
    answers: List[AnswerIn]
# app/schemas/survey.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class CreateSurveysIn(BaseModel):
    evaluator_user_ids: List[str]


class SurveyStatusOut(BaseModel):
    survey_id: str
    status: str


class SurveyWithUserOut(BaseModel):
    """Survey с дополнительной информацией о пользователе и ревью"""
    survey_id: str
    review_id: str
    evaluator_user_id: str | None = None
    status: str
    is_declined: bool
    declined_reason: str | None = None
    next_reminder_at: datetime | None = None
    submitted_at: datetime | None = None
    respondent_key: str | None = None
    evaluator_name: str | None = None
    review_title: str
    review_description: str | None = None
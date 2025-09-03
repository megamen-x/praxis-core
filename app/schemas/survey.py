# app/schemas/survey.py
from pydantic import BaseModel
from typing import List


class CreateSurveysIn(BaseModel):
    evaluator_user_ids: List[str]


class SurveyStatusOut(BaseModel):
    survey_id: str
    status: str
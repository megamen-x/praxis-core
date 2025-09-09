# app/schemas/report.py
from pydantic import BaseModel
from typing import Optional


class ReportOut(BaseModel):
    report_id: str
    review_id: str
    strengths: str | None = None
    growth_points: str | None = None
    dynamics: str | None = None
    prompt: str | None = None
    analytics_for_reviewers: str | None = None
    recommendations: str | None = None


class ReportWithReviewOut(ReportOut):
    """Report с дополнительной информацией о Review"""
    review_title: str
    review_description: str | None = None
    review_status: str
    review_created_at: str
    subject_user_name: str

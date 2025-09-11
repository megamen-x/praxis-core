"""Pydantic schemes for reviews.
"""
# app/schemas/review.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateReviewIn(BaseModel):
    created_by_user_id: str
    subject_user_id: Optional[str] = None
    title: str = Field(min_length=1)
    description: Optional[str] = None
    anonymity: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ReviewOut(BaseModel):
    review_id: str
    subject_user_id: str | None = None
    title: str
    description: str | None = None
    anonymity: bool
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None
    review_link: str | None = None


class UpdateReviewIn(BaseModel):
    subject_user_id: str | None = None
    title: str | None = None
    description: str | None = None
    anonymity: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None

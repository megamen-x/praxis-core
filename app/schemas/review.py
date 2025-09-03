# app/schemas/review.py
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class CreateReviewIn(BaseModel):
    created_by_user_id: str
    subject_user_id: str
    title: str = Field(min_length=1)
    description: Optional[str] = None
    anonymity: bool = True
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None


class ReviewOut(BaseModel):
    review_id: str
    title: str
    description: str | None = None
    anonymity: bool
    status: str
    start_at: datetime | None = None
    end_at: datetime | None = None


class UpdateReviewIn(BaseModel):
    title: str | None = None
    description: str | None = None
    anonymity: bool | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
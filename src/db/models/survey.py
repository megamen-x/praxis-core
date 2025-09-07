# db/models/survey.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Enum, ForeignKey, Boolean, func
from src.db import Base
import enum
import uuid


class SurveyStatus(str, enum.Enum):
    not_started = "not_started"
    in_progress = "in_progress"
    completed = "completed"
    declined = "declined"
    expired = "expired"


class Survey(Base):
    __tablename__ = "surveys"

    survey_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String, ForeignKey("reviews.review_id"), nullable=False)
    evaluator_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=True)
    status: Mapped[SurveyStatus] = mapped_column(Enum(SurveyStatus), default=SurveyStatus.not_started, nullable=False)
    is_declined: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    declined_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    next_reminder_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    submitted_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)

    review = relationship("Review", back_populates="surveys")
    evaluator = relationship("User")
    answers = relationship("Answer", back_populates="survey", cascade="all, delete-orphan")
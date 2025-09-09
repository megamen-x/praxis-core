# db/models/review.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, Integer, func
from src.db import Base
import enum
import uuid


class ReviewStatus(str, enum.Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"

class Review(Base):
    __tablename__ = "reviews"

    review_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    created_by_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    subject_user_id: Mapped[str] = mapped_column(String, ForeignKey("users.user_id"), nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    anonymity: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[ReviewStatus] = mapped_column(Enum(ReviewStatus), default=ReviewStatus.draft, nullable=False)
    start_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped["DateTime | None"] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    review_link: Mapped[str] = mapped_column(String, nullable=True)

    created_by = relationship("User", back_populates="created_reviews", foreign_keys=[created_by_user_id])
    subject_user = relationship("User", back_populates="subject_reviews", foreign_keys=[subject_user_id])
    questions = relationship("Question", back_populates="review", cascade="all, delete-orphan", order_by="Question.position")
    surveys = relationship("Survey", back_populates="review", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="review", uselist=False, cascade="all, delete-orphan")
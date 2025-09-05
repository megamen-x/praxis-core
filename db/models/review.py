# db/models/review.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy import String, Text, Boolean, DateTime, Enum, ForeignKey, Integer, func
from db import Base
import enum
import uuid


class ReviewStatus(str, enum.Enum):
    draft = "draft"
    in_progress = "in_progress"
    completed = "completed"
    archived = "archived"

class ReviewQuestionLink(Base):
    __tablename__ = 'review_question_link'

    review_id: Mapped[str] = mapped_column(String, ForeignKey('reviews.review_id'), primary_key=True)
    question_id: Mapped[str] = mapped_column(String, ForeignKey('questions.question_id'), primary_key=True)

    is_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    review = relationship("Review", back_populates="question_associations")
    question = relationship("Question", back_populates="review_associations")

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

    created_by = relationship("User", back_populates="created_reviews", foreign_keys=[created_by_user_id])
    subject_user = relationship("User", back_populates="subject_reviews", foreign_keys=[subject_user_id])
    question_associations = relationship(
        "ReviewQuestionLink",
        back_populates="review",
        cascade="all, delete-orphan",
        order_by="ReviewQuestionLink.position"
    )
    questions = association_proxy("question_associations", "question")
    
    surveys = relationship("Survey", back_populates="review", cascade="all, delete-orphan")
    report = relationship("Report", back_populates="review", uselist=False, cascade="all, delete-orphan")
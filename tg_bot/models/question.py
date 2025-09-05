# app/models/question.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Enum, ForeignKey
from db.session import Base
import enum
import uuid


class QuestionType(str, enum.Enum):
    radio = "radio"
    checkbox = "checkbox"
    text = "text"
    textarea = "textarea"
    scale = "scale"
    rating = "rating"


class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    review_id: Mapped[str] = mapped_column(String, ForeignKey("reviews.review_id"), index=True, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    is_required: Mapped[bool] = mapped_column(Integer, default=0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    review = relationship("Review", back_populates="questions")
    answers = relationship("Answer", back_populates="question", cascade="all, delete-orphan")
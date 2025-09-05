# db/models/question.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, Integer, Enum, ForeignKey
from db import Base
import enum
import uuid


class QuestionType(str, enum.Enum):
    radio = "radio"
    checkbox = "checkbox"
    text = "text"
    textarea = "textarea"

class QuestionOption(Base):
    __tablename__ = "question_options"

    option_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.question_id"), nullable=False, index=True)
    option_text: Mapped[str] = mapped_column(Text, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    question = relationship("Question", back_populates="options")

class Question(Base):
    __tablename__ = "questions"

    question_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(Enum(QuestionType), nullable=False)
    category: Mapped[str | None] = mapped_column(String, index=True, nullable=True)
    meta_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    answers = relationship("Answer", back_populates="question")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan", order_by="QuestionOption.position")
    review_associations = relationship("ReviewQuestionLink", back_populates="question", cascade="all, delete-orphan")
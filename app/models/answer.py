# app/models/answer.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey
from app.db.session import Base
import uuid


class Answer(Base):
    __tablename__ = "answers"

    answer_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.question_id"), nullable=False, index=True)
    survey_id: Mapped[str] = mapped_column(String, ForeignKey("surveys.survey_id"), nullable=False, index=True)
    response_data: Mapped[str] = mapped_column(Text, nullable=False)
    evaluator_user_id: Mapped[str | None] = mapped_column(String, nullable=True)

    question = relationship("Question", back_populates="answers")
    survey = relationship("Survey", back_populates="answers")
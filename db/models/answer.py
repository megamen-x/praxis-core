# db/models/answer.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Text, ForeignKey, PrimaryKeyConstraint
from db import Base
import uuid

class AnswerSelection(Base):
    __tablename__ = "answer_selections"

    answer_id: Mapped[str] = mapped_column(String, ForeignKey("answers.answer_id"), nullable=False)
    option_id: Mapped[str] = mapped_column(String, ForeignKey("question_options.option_id"), nullable=False)

    __table_args__ = (PrimaryKeyConstraint('answer_id', 'option_id'),)

class Answer(Base):
    __tablename__ = "answers"

    answer_id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String, ForeignKey("questions.question_id"), nullable=False, index=True)
    survey_id: Mapped[str] = mapped_column(String, ForeignKey("surveys.survey_id"), nullable=False, index=True)
    
    response_text: Mapped[str | None] = mapped_column(Text, nullable=True) 
    
    question = relationship("Question", back_populates="answers")
    survey = relationship("Survey", back_populates="answers")

    selected_options = relationship("QuestionOption", secondary="answer_selections",
        backref="answers"
    )
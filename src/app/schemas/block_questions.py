"""Pydantic-schemes for block questions.
"""
# app/schemas/block_questions.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class BlockQuestionsCreate(BaseModel):
    block_name: str = Field(..., min_length=1, description="Название блока вопросов не может быть пустым")
    public: bool = False
    question_ids: List[str] = Field(default_factory=list, description="Список ID вопросов для добавления в блок")


class BlockQuestionsUpdate(BaseModel):
    block_name: Optional[str] = Field(None, min_length=1, description="Название блока вопросов не может быть пустым")
    public: Optional[bool] = None
    question_ids: Optional[List[str]] = Field(None, description="Список ID вопросов для добавления в блок")


class BlockQuestionsOut(BaseModel):
    block_questions_id: str
    user_id: str
    block_name: str
    public: bool
    created_at: datetime
    questions_count: int = 0

    class Config:
        from_attributes = True


class BlockQuestionsWithQuestions(BaseModel):
    block_questions_id: str
    user_id: str
    block_name: str
    public: bool
    created_at: datetime
    questions: List[dict] = Field(default_factory=list)

    class Config:
        from_attributes = True


class QuestionSelectionRequest(BaseModel):
    selected_question_ids: List[str] = Field(..., description="Список ID выбранных вопросов для копирования в Review")

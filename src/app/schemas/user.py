# app/schemas/user.py
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserOut(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: int | None = None
    can_create_review: bool
    created_at: datetime


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    middle_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: int | None = None
    can_create_review: bool = False


class UserUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    middle_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    email: str | None = None
    telegram_username: str | None = None
    telegram_chat_id: int | None = None
    can_create_review: bool | None = None
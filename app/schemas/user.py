# app/schemas/user.py
from pydantic import BaseModel


class UserOut(BaseModel):
    user_id: str
    first_name: str
    last_name: str
    middle_name: str | None = None
    job_title: str | None = None
    department: str | None = None
    email: str | None = None
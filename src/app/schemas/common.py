# app/schemas/common.py
from pydantic import BaseModel


class MsgOut(BaseModel):
    ok: bool = True
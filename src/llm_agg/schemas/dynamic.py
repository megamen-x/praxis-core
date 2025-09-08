from typing import Literal, Annotated
from pydantic import BaseModel, Field, StringConstraints
from src.llm_agg.schemas.sides import Side, Sides

class Changed(BaseModel):
    side: Side
    summary: str # описание того, как поменялось качество человека
    old_mark: str # описание качества человека от респондента в прошлый раз
    new_mark: str # описание качества человека от респондента в этот раз

class New(BaseModel):
    pass

# class 
from typing import Literal, Annotated
from pydantic import BaseModel, Field, StringConstraints
from src.llm_agg.schemas.sides import Side, Sides

class Changed(BaseModel):
    pass

class New(BaseModel):
    pass

# class 
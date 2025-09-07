from typing import Optional, Union, List
from pydantic import BaseModel, Field
from db.models.question import QuestionType

class QuestionOptionIn(BaseModel):
    option_text: str
    position: Optional[int] = None

class RangeMeta(BaseModel):
    min: int = 1
    max: int = 10
    step: int = 1

class QuestionCreate(BaseModel):
    question_text: str
    question_type: QuestionType | str
    is_required: bool = False
    position: int = Field(default=0, ge=0)
    options: Optional[Union[List[QuestionOptionIn], RangeMeta]] = None

class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    question_type: Optional[QuestionType | str] = None
    is_required: Optional[bool] = None
    position: Optional[int] = Field(default=None, ge=1)
    options: Optional[Union[List[QuestionOptionIn], RangeMeta]] = None

# Dummy body for block-add route (kept for symmetry, can be empty)
class BlockRefIn(BaseModel):
    pass
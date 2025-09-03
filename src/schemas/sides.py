from typing import Literal
from pydantic import BaseModel, Field


class Side(BaseModel):
    side: Literal['strong', 'weak'] = Field(..., description="Defining the person's side: whether this quality is their strong or weak side")
    side_description: str = Field(..., description="Description of which specific quality is being considered")
    side_pick_explanation: str = Field(..., description="Explanation of why, based on the user's answers, this quality is considered strong or weak")

class Recommendation(BaseModel):
    side: Side = Field(..., description="execute first remaining step")
    brief_explanation: str = Field(..., description="execute first remaining step")
    recommendation: str = Field(..., description="execute first remaining step")

class Sides(BaseModel):
    sides: list[Side]
    overall: str = Field(..., description="execute first remaining step") # краткое описание всех моментов с сильными и слабыми сторонами

class Recommendations(BaseModel):
    recommendations: list[Recommendation]
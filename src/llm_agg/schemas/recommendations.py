from typing import Literal, Annotated
from pydantic import BaseModel, Field
from src.llm_agg.schemas.sides import SideRef


class RecommendationItem(BaseModel):
    kind: Literal['recommended'] = Field('recommended', description="Type discriminator")
    side_ref: SideRef = Field(..., description="Target quality reference")
    brief_explanation: str = Field(..., description="Short why-this matters")
    recommendation: str = Field(..., description="Main advice (1–3 sentences)")

class Recommendations(BaseModel):
    items: list[RecommendationItem]
    note: str | None = Field(None, description="Optional global note")
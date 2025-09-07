from typing import Literal, Annotated
from annotated_types import MinLen
from pydantic import BaseModel, Field, StringConstraints


class Side(BaseModel):
    side: Literal['strong', 'weak'] = Field(..., description="Defining the person's side: whether this quality is their strong or weak side")
    side_description: str = Field(..., description="Description of which specific quality is being considered")
    side_pick_explanation: str = Field(..., description="Explanation of why, based on the user's answers, this quality is considered strong or weak")
    respondents_count: int = Field(..., ge=0, description="Number of unique respondents who identified this side (strong/weak) in the candidate")
    # proofs: Annotated[list[str], MinLen(1)] = Field(..., description="Specific phrases/sections of phrases from the reviewers' reviews that speak to the person's quality")

class AmbiguousSide(BaseModel):
    side_description: str = Field(..., description="Description of the specific quality being considered")
    side_pick_explanation: str = Field(..., description="Explanation of why feedback is mixed: at least one respondent marked it as strong and at least one as weak")
    strong_count: int = Field(..., ge=1, description="Number of respondents who identified this quality as a strong side")
    weak_count: int = Field(..., ge=1, description="Number of respondents who identified this quality as a weak side")
    # proofs: Annotated[list[str], MinLen(2)] = Field(..., description="Specific phrases/sections of phrases from the reviewers' reviews that say the opposite things about a candidate's quality")

class Sides(BaseModel):
    sides: list[Side | AmbiguousSide]
    summary: Annotated[str, StringConstraints(max_length=120)] = Field(..., description="Concise summary of the candidate based on all non-ambiguous strengths and weaknesses noted by reviewers; ambiguous sides must be excluded")

class Recommendation(BaseModel):
    side: Side = Field(..., description="execute first remaining step")
    brief_explanation: str = Field(..., description="execute first remaining step")
    recommendation: str = Field(..., description="execute first remaining step")

class Recommendations(BaseModel):
    recommendations: list[Recommendation]
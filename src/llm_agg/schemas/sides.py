from typing import Literal, Annotated
from annotated_types import MinLen, Gt
from pydantic import BaseModel, Field, StringConstraints


class Side(BaseModel):
    kind: Literal['unambiguous'] = Field('unambiguous', description="Type discriminator")
    side: Literal['strong', 'weak'] = Field(..., description="Defining the person's side: whether this quality is their strong or weak side")
    side_description: str = Field(..., description="Description of which specific quality is being considered")
    side_pick_explanation: str = Field(..., description="Explanation of why, based on the user's answers, this quality is considered strong or weak")
    respondents_count: Annotated[int, Gt(0)] = Field(..., description="Number of unique respondents who identified this side (strong/weak) in the candidate")
    proofs: Annotated[list[str], MinLen(1)] = Field(..., description="Specific phrases/sections of phrases from the reviewers' reviews that speak to the person's quality")

class AmbiguousSide(BaseModel):
    kind: Literal['ambiguous'] = Field('ambiguous', description="Type discriminator")
    side_description: str = Field(..., description="Description of the specific quality being considered")
    side_pick_explanation: str = Field(..., description="Explanation of why feedback is mixed: at least one respondent marked it as strong and at least one as weak")
    strong_count: Annotated[int, Gt(0)] = Field(..., description="Number of respondents who identified this quality as a strong side")
    weak_count: Annotated[int, Gt(0)] = Field(..., description="Number of respondents who identified this quality as a weak side")
    proofs_strong: Annotated[list[str], MinLen(1)] = Field(..., description="Specific quotes/excerpts from reviews that support this quality as a strength.")
    proofs_weak: Annotated[list[str], MinLen(1)] = Field(..., description="Specific quotes/excerpts from reviews that indicate this quality as a weakness.")

class Sides(BaseModel):
    sides: list[Annotated[Side | AmbiguousSide, Field(discriminator='kind')]]
    summary: Annotated[str, StringConstraints(max_length=120)] = Field(..., description="Concise summary of the candidate based on all non-ambiguous strengths and weaknesses noted by reviewers; ambiguous sides must be excluded")

class SideRef(BaseModel):
    side_description: str = Field(..., description="Description of the specific quality being considered")
    side: Literal['strong', 'weak'] = Field(..., description="Defining the person's side: whether this quality is their strong or weak side")
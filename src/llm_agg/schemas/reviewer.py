from typing import Literal, Annotated
from pydantic import BaseModel, Field, StringConstraints

# смотрит, что ревьюер отмечает чаще всего в своих ревью
class ReviewerTrends(BaseModel):
    trend: str
    trend_counter: int
    trend_examples: list[str] # вообще тут должна быть конкретная строка, дата резюме и прочая инфа


# class ReviewerTrends
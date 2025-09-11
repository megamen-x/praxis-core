from pydantic import BaseModel
from typing import List

# Новая, более строгая схема для сохранения ответа
class AnswerIn(BaseModel):
    question_id: str
    response_text: str | None = None # Для text/textarea
    selected_option_ids: List[str] | None = None # Для radio/checkbox

class SaveAnswersIn(BaseModel):
    csrf_token: str
    answers: List[AnswerIn]
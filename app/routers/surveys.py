# app/routers/surveys.py
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.session import get_db
from db.models import Survey, Review, Question, Answer, SurveyStatus, ReviewQuestionLink, QuestionType, QuestionOption
from sqlalchemy.orm import joinedload
from app.schemas.answer import SaveAnswersIn
from app.core.security import issue_csrf, verify_csrf
from app.services.links import verify_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/form/{survey_id}", response_class=HTMLResponse)
def form_page(survey_id: str, request: Request, t: str = Query(...), db: Session = Depends(get_db)):
    payload = verify_token(t)
    if not payload or payload.get("role") != "respondent" or payload.get("sub") != survey_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    review = db.query(Review).options(
        joinedload(Review.question_associations).joinedload(ReviewQuestionLink.question).joinedload(Question.options)
    ).filter(Review.review_id == survey.review_id).one()

    questions = []
    for assoc in review.question_associations:
        q = assoc.question
        options = [{"option_id": o.option_id, "option_text": o.option_text, "value": o.value} for o in q.options]
        questions.append({
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "is_required": assoc.is_required,
            "options": options,
        })

    response = templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "survey": survey,
            "review": review,
            "questions": questions,
            "api_url": f"/api/surveys/{survey_id}/answers?t={t}",
            "done_url": "/thanks",
        },
    )
    csrf = issue_csrf(response, scope=f"survey:{survey_id}")
    response.set_cookie("survey_csrf", csrf, samesite="lax")
    return response


@router.post("/api/surveys/{survey_id}/answers")
def save_answers(
    survey_id: str,
    payload: SaveAnswersIn,
    request: Request,
    db: Session = Depends(get_db),
    t: str = Query(...),
    draft: bool = Query(False),
    final: bool = Query(False),
):
    token = verify_token(t)
    if not token or token.get("sub") != survey_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, payload.csrf_token, scope=f"survey:{survey_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")
    review = db.get(Review, survey.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    # if final and review.end_at and review.end_at < utcnow():
    #     raise HTTPException(status_code=410, detail="Deadline passed")

    # Upsert answers
    db.query(Answer).filter(Answer.survey_id == survey_id).delete()
    db.flush()

    for answer_data in payload.answers:
        question = db.get(Question, answer_data.question_id)
        if not question:
            continue # Пропускаем ответ на несуществующий вопрос

        # Создаем основной объект ответа
        new_answer = Answer(
            survey_id=survey_id,
            question_id=question.question_id,
        )

        if question.question_type in (QuestionType.text, QuestionType.textarea):
            new_answer.response_text = answer_data.response_text
        
        elif question.question_type in (QuestionType.radio, QuestionType.checkbox):
            if answer_data.selected_option_ids:
                # Находим объекты опций по ID
                options = db.scalars(
                    select(QuestionOption).where(QuestionOption.option_id.in_(answer_data.selected_option_ids))
                ).all()
                # SQLAlchemy сама создаст записи в AnswerSelection
                new_answer.selected_options.extend(options)
        
        db.add(new_answer)

    # Update survey status
    if final:
        survey.status = SurveyStatus.completed
        survey.submitted_at = utcnow()
    else:
        if survey.status == SurveyStatus.not_started:
            survey.status = SurveyStatus.in_progress

    db.commit()
    return {"ok": True, "final": final}

from fastapi.responses import HTMLResponse

@router.get("/thanks", response_class=HTMLResponse)
def thanks_page(request: Request):
    return templates.TemplateResponse("thanks.html", {"request": request, "title": "Спасибо"})
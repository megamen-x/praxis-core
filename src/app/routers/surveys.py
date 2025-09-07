# app/routers/surveys.py
from datetime import datetime, timezone
import json
from random import randint
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import select
from src.db.session import get_db
from src.db.models import Survey, Review, Question, Answer, SurveyStatus, QuestionType, QuestionOption
from src.app.schemas.answer import SaveAnswersIn
from src.app.core.security import issue_csrf, verify_csrf
from src.app.services.links import verify_token
from sqlalchemy import delete as sa_delete, select
from src.db.models.answer import AnswerSelection

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/form/{survey_id}", response_class=HTMLResponse)
async def form_page(survey_id: str, request: Request, t: str = Query(...), db: Session = Depends(get_db)):
    payload = verify_token(t)
    if not payload or payload.get("role") != "respondent" or payload.get("sub") != survey_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    survey = db.get(Survey, survey_id)
    if not survey:
        raise HTTPException(status_code=404, detail="Survey not found")

    # Load review with its questions and question options
    review = db.query(Review).options(
        joinedload(Review.questions).joinedload(Question.options)
    ).filter(Review.review_id == survey.review_id).one()

    # Build questions context for template
    questions = []
    for q in review.questions:  # ordered by Question.position in relationship
        if q.question_type in (QuestionType.radio, QuestionType.checkbox):
            opts = [{"option_id": o.option_id, "option_text": o.option_text} for o in q.options]
            meta = {"options": opts}
        elif q.question_type == QuestionType.range_slider:
            try:
                meta = json.loads(q.meta_json) if q.meta_json else {"min": 1, "max": 10, "step": 1}
            except Exception:
                meta = {"min": 1, "max": 10, "step": 1}
        else:
            meta = {}

        questions.append({
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "is_required": q.is_required,
            "meta": meta,
        })

    random_bg_img = randint(1, 5)
    response = templates.TemplateResponse(
        "form.html",
        {
            "request": request,
            "survey": survey,
            "review": review,
            "background_image": f'assets/site_bg_{random_bg_img}.png',
            "questions": questions,
            "api_url": f"/api/surveys/{survey_id}/answers?t={t}",
            "done_url": "/thanks",
        },
    )
    csrf = issue_csrf(response, scope=f"survey:{survey_id}")
    response.set_cookie("survey_csrf", csrf, samesite="lax")
    return response


@router.post("/api/surveys/{survey_id}/answers")
async def save_answers(
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
    db.execute(
        sa_delete(AnswerSelection).where(
            AnswerSelection.answer_id.in_(
                select(Answer.answer_id).where(Answer.survey_id == survey_id)
            )
        )
    )
    db.execute(sa_delete(Answer).where(Answer.survey_id == survey_id))
    db.flush()

    for answer_data in payload.answers:
        question = db.get(Question, answer_data.question_id)
        if not question or question.review_id != review.review_id:
            # Skip answers to nonexistent or unrelated questions
            continue

        new_answer = Answer(survey_id=survey_id, question_id=question.question_id)

        if question.question_type in (QuestionType.text, QuestionType.textarea, QuestionType.range_slider):
            # Store any free-text or scalar value (including slider value) as text
            # Expecting the client to send response_text for these types
            if getattr(answer_data, "response_text", None) is not None:
                new_answer.response_text = str(answer_data.response_text)

        elif question.question_type in (QuestionType.radio, QuestionType.checkbox):
            sel_ids = getattr(answer_data, "selected_option_ids", None) or []
            if sel_ids:
                # Only attach options that belong to this question
                options = db.scalars(
                    select(QuestionOption).where(
                        QuestionOption.option_id.in_(sel_ids),
                        QuestionOption.question_id == question.question_id
                    )
                ).all()
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


@router.get("/thanks", response_class=HTMLResponse)
async def thanks_page(request: Request):
    return templates.TemplateResponse("thanks.html", {"request": request, "title": "Спасибо"})
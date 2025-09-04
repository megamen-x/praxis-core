# app/routers/surveys.py
import json
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, update
from app.db.session import get_db
from app.models import Survey, Review, Question, Answer, SurveyStatus
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
    review = db.get(Review, survey.review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    # if review.end_at and review.end_at < utcnow():
    #     raise HTTPException(status_code=410, detail="Deadline passed")

    rows = db.scalars(select(Question).where(Question.review_id == survey.review_id).order_by(Question.position)).all()
    questions = []
    for q in rows:
        meta = {}
        if q.meta_json:
            try:
                meta = json.loads(q.meta_json)
            except Exception:
                meta = {}
        questions.append(
            {
                "question_id": q.question_id,
                "question_text": q.question_text,
                "question_type": q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type),
                "is_required": bool(q.is_required),
                "position": q.position,
                "meta": meta,
            }
        )

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
    qids = set(payload.answers.keys())
    existing = db.scalars(
        select(Answer).where(Answer.survey_id == survey_id, Answer.question_id.in_(list(qids)))
    ).all()
    existing_map = {(a.question_id): a for a in existing}

    for qid, val in payload.answers.items():
        data_json = json.dumps(val, ensure_ascii=False)
        if qid in existing_map:
            existing_map[qid].response_data = data_json
            existing_map[qid].evaluator_user_id = survey.evaluator_user_id
        else:
            a = Answer(
                question_id=qid,
                survey_id=survey_id,
                evaluator_user_id=survey.evaluator_user_id,
                response_data=data_json,
            )
            db.add(a)

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
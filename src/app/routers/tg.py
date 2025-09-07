# app/routers/tg.py
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from src.db.session import get_db
from src.app.core.security import require_bot_auth
from src.app.core.config import settings
from src.db.models import User, Review, ReviewStatus, Survey, SurveyStatus
from src.app.schemas.review import CreateReviewIn, ReviewOut
from src.app.schemas.survey import CreateSurveysIn, SurveyStatusOut
from src.app.services.links import sign_token

router = APIRouter()

@router.post("/api/review/create")
# , _: None = Depends(require_bot_auth)
def tg_create_review(
    payload: CreateReviewIn, request: Request, db: Session = Depends(get_db)
):
    
    created_by = db.get(User, payload.created_by_user_id)
    subject = db.get(User, payload.subject_user_id)
    if not created_by or not subject:
        raise HTTPException(status_code=404, detail=f"User not found: {payload.created_by_user_id}, {payload.subject_user_id}.")
    review = Review(
        created_by_user_id=payload.created_by_user_id,
        subject_user_id=payload.subject_user_id,
        title=payload.title,
        description=payload.description,
        anonymity=payload.anonymity,
        start_at=payload.start_at,
        end_at=payload.end_at,
        status=ReviewStatus.draft,
    )
    db.add(review)
    db.commit()
    db.refresh(review)

    t = sign_token({"role": "admin", "sub": review.review_id}, ttl_sec=settings.ADMIN_LINK_TTL)
    admin_link = f"/admin/reviews/{review.review_id}?t={t}"
    return {"review_id": review.review_id, "admin_link": admin_link}

"""
curl -X POST "http://localhost:8000/api/tg/reviews/create" -H "Content-Type: application/json" -d '{"created_by_user_id":"b98d88fd-f4d5-4aff-b51c-43a27f75cfda","subject_user_id":"8e10f80d-e58a-4c81-8723-cee5f9b1261c","title":"Demo 360","description":"Test","anonymity":true}'
"""

@router.get("/api/tg/users/search")
def tg_user_search(query: str = Query(""), request: Request = None, db: Session = Depends(get_db), _: None = Depends(require_bot_auth)):
    q = f"%{query.lower()}%"
    stmt = select(User).where(
        func.lower(User.first_name + " " + User.last_name).like(q) | func.lower(User.email).like(q)
    ).limit(50)
    rows = db.scalars(stmt).all()
    return [
        {
            "user_id": u.user_id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "department": u.department,
            "email": u.email,
        }
        for u in rows
    ]


@router.post("/api/tg/reviews/{review_id}/surveys")
# _: None = Depends(require_bot_auth)
def tg_create_surveys(
    review_id: str, payload: CreateSurveysIn, request: Request, db: Session = Depends(get_db), 
):
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    created = []
    for uid in payload.evaluator_user_ids:
        s = Survey(review_id=review_id, evaluator_user_id=uid, status=SurveyStatus.not_started)
        db.add(s)
        db.flush()
        t = sign_token({"role": "respondent", "sub": s.survey_id}, ttl_sec=settings.RESPONDENT_LINK_TTL)
        created.append({"survey_id": s.survey_id, "form_link": f"/form/{s.survey_id}?t={t}"})
    db.commit()
    return created


@router.post("/api/tg/surveys/{survey_id}/accept")
def tg_survey_accept(survey_id: str, request: Request, db: Session = Depends(get_db), _: None = Depends(require_bot_auth)):
    s = db.get(Survey, survey_id)
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    if s.status == SurveyStatus.declined:
        s.is_declined = False
        s.declined_reason = None
    if s.status == SurveyStatus.not_started:
        # keep not_started until user opens form
        pass
    db.commit()
    return {"ok": True}


@router.post("/api/tg/surveys/{survey_id}/decline")
def tg_survey_decline(survey_id: str, reason: str = "", request: Request = None, db: Session = Depends(get_db), _: None = Depends(require_bot_auth)):
    s = db.get(Survey, survey_id)
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    s.status = SurveyStatus.declined
    s.is_declined = True
    s.declined_reason = reason
    db.commit()
    return {"ok": True}


@router.get("/api/tg/surveys/{survey_id}/status", response_model=SurveyStatusOut)
def tg_survey_status(survey_id: str, request: Request, db: Session = Depends(get_db), _: None = Depends(require_bot_auth)):
    s = db.get(Survey, survey_id)
    if not s:
        raise HTTPException(status_code=404, detail="Survey not found")
    return {"survey_id": survey_id, "status": s.status.value}


@router.get("/api/tg/reviews/{review_id}/progress")
def tg_review_progress(review_id: str, request: Request, db: Session = Depends(get_db), _: None = Depends(require_bot_auth)):
    total = db.query(Survey).filter(Survey.review_id == review_id).count()
    completed = db.query(Survey).filter(Survey.review_id == review_id, Survey.status == SurveyStatus.completed).count()
    declined = db.query(Survey).filter(Survey.review_id == review_id, Survey.status == SurveyStatus.declined).count()
    return {"review_id": review_id, "total": total, "completed": completed, "declined": declined}
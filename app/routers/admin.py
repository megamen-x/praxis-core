# app/routers/admin.py
import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.db.session import get_db
from app.core.config import settings
from app.core.security import verify_csrf, issue_csrf
from app.models import Review, Question, QuestionType, ReviewStatus
from app.schemas.review import UpdateReviewIn
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.services.links import verify_token

router = APIRouter()


templates = Jinja2Templates(directory="app/templates")


@router.get("/admin/reviews/{review_id}", response_class=HTMLResponse)
def admin_review_page(review_id: str, request: Request, t: str = Query(...), db: Session = Depends(get_db)):
    payload = verify_token(t)
    if not payload or payload.get("role") != "admin" or payload.get("sub") != review_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    questions = db.scalars(select(Question).where(Question.review_id == review_id).order_by(Question.position)).all()
    qctx = []
    for q in questions:
        meta = {}
        if q.meta_json:
            try:
                meta = json.loads(q.meta_json)
            except Exception:
                meta = {}
        qctx.append(
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
        "admin_edit.html",
        {
            "request": request,
            "review": review,
            "questions": qctx,
            "token": t,
        },
    )
    csrf = issue_csrf(response, scope=f"admin:{review_id}")
    response.set_cookie("admin_csrf", csrf, samesite="lax")
    return response


@router.patch("/api/reviews/{review_id}")
def update_review(review_id: str, payload: UpdateReviewIn, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    stmt = (
        update(Review)
        .where(Review.review_id == review_id)
        .values({k: v for k, v in payload.model_dump(exclude_unset=True).items()})
        .returning(Review.review_id)
    )
    res = db.execute(stmt).first()
    db.commit()
    if not res:
        raise HTTPException(status_code=404, detail="Not found")
    return {"ok": True}


@router.post("/api/reviews/{review_id}/questions")
def create_questions(review_id: str, items: list[QuestionCreate], request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    created = []
    for it in items:
        q = Question(
            review_id=review_id,
            question_text=it.question_text,
            question_type=QuestionType(it.question_type),
            is_required=1 if it.is_required else 0,
            position=it.position or 0,
            meta_json=json.dumps(it.meta) if it.meta else None,
        )
        db.add(q)
        created.append(q)
    db.commit()
    return {"ok": True, "count": len(created)}


@router.patch("/api/questions/{question_id}")
def update_question(question_id: str, patch: QuestionUpdate, request: Request, db: Session = Depends(get_db), t: str = Query(...), review_id: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    data = patch.model_dump(exclude_unset=True)
    if "meta" in data:
        data["meta_json"] = json.dumps(data.pop("meta"))
    if "question_type" in data:
        data["question_type"] = QuestionType(data["question_type"])
    stmt = update(Question).where(Question.question_id == question_id).values(data)
    res = db.execute(stmt)
    db.commit()
    return {"ok": True}


@router.delete("/api/questions/{question_id}")
def delete_question(question_id: str, request: Request, db: Session = Depends(get_db), t: str = Query(...), review_id: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    stmt = delete(Question).where(Question.question_id == question_id)
    db.execute(stmt)
    db.commit()
    return {"ok": True}
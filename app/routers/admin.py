# app/routers/admin.py
import json
from random import randint
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from app.db.session import get_db
from app.core.security import verify_csrf, issue_csrf
from app.models import Review, Question, QuestionType, ReviewStatus
from app.schemas.review import UpdateReviewIn
from app.schemas.question import QuestionCreate, QuestionUpdate
from app.services.links import verify_token

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

ALLOWED_QTYPES = {"text", "textarea", "radio", "checkbox"}

def _validate_qtype(qt: str) -> str:
    if qt not in ALLOWED_QTYPES:
        raise HTTPException(status_code=422, detail=f"Unsupported question_type '{qt}'")
    return qt


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
        qtype_str = q.question_type.value if hasattr(q.question_type, "value") else str(q.question_type)
        qctx.append(
            {
                "question_id": q.question_id,
                "question_text": q.question_text,
                "question_type": qtype_str,
                "is_required": bool(q.is_required),
                "position": q.position,
                "meta": meta,
            }
        )

    random_bg_img = randint(1, 5)
    response = templates.TemplateResponse(
        "admin_edit.html",
        {
            "request": request,
            "review": review,
            "background_image": f'assets/site_bg_{random_bg_img}.png',
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


@router.delete("/api/reviews/{review_id}")
def delete_review(review_id: str, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    # ORM cascade will remove questions, surveys and their answers (configured in models)
    db.delete(review)
    db.commit()
    return {"ok": True}


@router.post("/api/reviews/{review_id}/questions")
def create_questions(review_id: str, items: list[QuestionCreate], request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    created = 0
    for it in items:
        qtype = _validate_qtype(it.question_type)
        meta = it.meta or {}
        # sanitize meta: only keep options for radio/checkbox
        if qtype in {"radio", "checkbox"}:
            opts = meta.get("options") or []
            # normalize to {label, value}
            norm = []
            for o in opts:
                if isinstance(o, dict):
                    lbl = (o.get("label") or o.get("value") or "").strip()
                    val = (o.get("value") or o.get("label") or "").strip()
                    if lbl:
                        norm.append({"label": lbl, "value": val})
                elif isinstance(o, str) and o.strip():
                    s = o.strip()
                    norm.append({"label": s, "value": s})
            meta_json = json.dumps({"options": norm}, ensure_ascii=False) if norm else json.dumps({"options": []})
        else:
            meta_json = None

        q = Question(
            review_id=review_id,
            question_text=it.question_text,
            question_type=QuestionType(qtype),
            is_required=1 if it.is_required else 0,
            position=it.position or 0,
            meta_json=meta_json,
        )
        db.add(q)
        created += 1
    db.commit()
    return {"ok": True, "count": created}


@router.patch("/api/questions/{question_id}")
def update_question(question_id: str, patch: QuestionUpdate, request: Request, db: Session = Depends(get_db), t: str = Query(...), review_id: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    data = patch.model_dump(exclude_unset=True)
    if "question_type" in data:
        data["question_type"] = QuestionType(_validate_qtype(data["question_type"]))

    meta_json = None
    if "meta" in data:
        qtype = (data.get("question_type").value if hasattr(data.get("question_type"), "value") else data.get("question_type"))
        meta = data.pop("meta") or {}
        if qtype in {"radio", "checkbox"}:
            opts = meta.get("options") or []
            norm = []
            for o in opts:
                if isinstance(o, dict):
                    lbl = (o.get("label") or o.get("value") or "").strip()
                    val = (o.get("value") or o.get("label") or "").strip()
                    if lbl:
                        norm.append({"label": lbl, "value": val})
                elif isinstance(o, str) and o.strip():
                    s = o.strip()
                    norm.append({"label": s, "value": s})
            meta_json = json.dumps({"options": norm}, ensure_ascii=False)
        else:
            meta_json = None

    values = {k: v for k, v in data.items() if k != "meta_json"}
    if meta_json is not None:
        values["meta_json"] = meta_json

    stmt = update(Question).where(Question.question_id == question_id).values(values)
    db.execute(stmt)
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
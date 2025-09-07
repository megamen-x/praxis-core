import json
from random import randint
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete, func
from src.app.core.config import settings
from src.db.session import get_db
from src.app.core.security import verify_csrf, issue_csrf
from src.app.schemas.review import UpdateReviewIn
from src.app.schemas.question import QuestionCreate, QuestionUpdate, BlockRefIn
from src.app.services.links import verify_token

# models
from src.db.models.review import Review
from src.db.models.question import Question, QuestionType, QuestionOption
from src.db.models.question_bank import QuestionBlock

# service to materialize a block
from src.app.services.review_blocks import add_block_to_review

router = APIRouter()
templates = Jinja2Templates(directory=settings.JINJA2_TEMPLATES)

@router.get("/admin/reviews/{review_id}", response_class=HTMLResponse)
async def admin_review_page(review_id: str, request: Request, t: str = Query(...), db: Session = Depends(get_db)):
    payload = verify_token(t)
    if not payload or payload.get("role") != "admin" or payload.get("sub") != review_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # review.questions already ordered by Question.position (see relationship)
    qctx = []
    for q in review.questions:
        if q.question_type in (QuestionType.radio, QuestionType.checkbox):
            opts = [{"option_id": o.option_id, "option_text": o.option_text} for o in q.options]
            meta = {"options": opts}
        elif q.question_type == QuestionType.range_slider:
            try:
                meta = json.loads(q.meta_json or "{}")
            except Exception:
                meta = {"min": 1, "max": 10, "step": 1}
            opts = []
        else:
            meta, opts = {}, []

        qctx.append({
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "options": opts,     # used to prefill choices in UI
            "meta": meta,        # used to render range settings
            "is_required": q.is_required,
            "position": q.position,
        })

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
async def update_review(review_id: str, payload: UpdateReviewIn, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
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
async def delete_review(review_id: str, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return {"ok": True}


# Create questions directly in this review
@router.post("/api/reviews/{review_id}/questions")
async def create_review_questions(review_id: str, items: list[QuestionCreate], request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # ensure positions do not collide
    existing_positions = set(p for (p,) in db.execute(
        select(Question.position).where(Question.review_id == review_id)
    ).all())

    def next_free_pos(start=1):
        pos = max(existing_positions) + 1 if existing_positions else 1
        return max(pos, start)

    created = 0
    for it in items:
        try:
            qtype = QuestionType(it.question_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported question type: {it.question_type}")

        # Pick a non-conflicting position
        desired = max(1, it.position or 0)
        position = desired if desired not in existing_positions else next_free_pos(desired)
        existing_positions.add(position)

        q = Question(
            review_id=review_id,
            question_text=it.question_text,
            question_type=qtype,
            is_required=bool(it.is_required),
            position=position,
        )

        # meta/options
        if qtype in (QuestionType.radio, QuestionType.checkbox):
            # it.options is list[OptionIn]
            for i, opt in enumerate(it.options or []):
                db.add(QuestionOption(
                    question=q,
                    option_text=opt.option_text,
                    position=opt.position if opt.position is not None else i,
                ))
        elif qtype == QuestionType.range_slider:
            # it.options is RangeMeta dict
            q.meta_json = json.dumps(it.options or {"min": 1, "max": 10, "step": 1})
        else:
            q.meta_json = None  # text/textarea

        db.add(q)
        created += 1

    db.commit()
    return {"ok": True, "count": created}


# Update a question that belongs to this review
@router.patch("/api/questions/{question_id}")
async def update_question(question_id: str, patch: QuestionUpdate, request: Request, db: Session = Depends(get_db), t: str = Query(...), review_id: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    question = db.get(Question, question_id)
    if not question or question.review_id != review_id:
        raise HTTPException(status_code=404, detail="Question not found")

    # Basic updates
    if patch.question_text is not None:
        question.question_text = patch.question_text
    if patch.is_required is not None:
        question.is_required = patch.is_required

    # Position uniqueness inside review
    if patch.position is not None and patch.position > 0:
        desired = patch.position
        if desired != question.position:
            used = set(p for (p,) in db.execute(
                select(Question.position).where(
                    Question.review_id == review_id,
                    Question.question_id != question_id
                )
            ).all())
            if desired in used:
                desired = (max(used) + 1) if used else 1
            question.position = desired

    # Type and options/meta updates
    if patch.question_type is not None:
        try:
            new_type = QuestionType(patch.question_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unsupported question type: {patch.question_type}")
        question.question_type = new_type

    if patch.options is not None:
        # Clear previous options if any
        if question.options:
            for opt in list(question.options):
                db.delete(opt)
        question.meta_json = None

        if question.question_type in (QuestionType.radio, QuestionType.checkbox):
            for i, opt in enumerate(patch.options or []):
                db.add(QuestionOption(
                    question_id=question.question_id,
                    option_text=opt.option_text,
                    position=opt.position if getattr(opt, "position", None) is not None else i
                ))
        elif question.question_type == QuestionType.range_slider:
            # patch.options is RangeMeta dict
            question.meta_json = json.dumps(patch.options)

    db.commit()
    return {"ok": True}


# Delete a question from the review (question is review-owned)
@router.delete("/api/reviews/{review_id}/questions/{question_id}")
async def delete_review_question(review_id: str, question_id: str, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    q = db.get(Question, question_id)
    if not q or q.review_id != review_id:
        raise HTTPException(status_code=404, detail="Question not found in this review")

    db.delete(q)
    db.commit()
    return {"ok": True}


# List available blocks for this review's creator (and public)
@router.get("/api/question-blocks")
async def list_blocks_for_review(review_id: str = Query(...), t: str = Query(...), db: Session = Depends(get_db)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)

    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    # Blocks created by the same user or public
    blocks = db.execute(
        select(QuestionBlock).where(
            (QuestionBlock.created_by_user_id == review.created_by_user_id) | (QuestionBlock.is_public == True)  # noqa: E712
        ).order_by(QuestionBlock.name.asc())
    ).scalars().all()

    out = []
    for b in blocks:
        out.append({
            "block_id": b.block_id,
            "name": b.name,
            "description": b.description,
            "items_count": len(b.items),
            "is_public": b.is_public,
        })
    return out


# Add a whole block to a review
@router.post("/api/reviews/{review_id}/blocks/{block_id}")
async def add_block(review_id: str, block_id: str, _: BlockRefIn, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    try:
        count = add_block_to_review(db, review_id, block_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {"ok": True, "count": count}
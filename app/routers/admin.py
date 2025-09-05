# app/routers/admin.py
import json
from random import randint
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import select, update, delete
from db.session import get_db
from app.core.security import verify_csrf, issue_csrf
from db.models import Review, Question, QuestionType, QuestionOption, ReviewQuestionLink
from app.schemas.review import UpdateReviewIn
from app.schemas.question import QuestionCreate, QuestionUpdate, ReviewQuestionLinkUpdate
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

    q_associations = review.question_associations
    
    qctx = []
    for assoc in q_associations:
        q = assoc.question
        # Собираем опции в простой формат для JS
        if q.question_type in ["radio", "checkbox"]:
            options = [{"option_id": o.option_id, "option_text": o.option_text} for o in q.options]
        elif q.question_type == "range_slider" and q.meta_json:
            import json
            try:
                options = json.loads(q.meta_json)
            except:
                options = {"min": 1, "max": 10, "step": 1}
        else:
            options = []
        
        qctx.append({
            "question_id": q.question_id,
            "question_text": q.question_text,
            "question_type": q.question_type.value,
            "options": options,
            # Эти данные теперь берем из association
            "is_required": assoc.is_required,
            "position": assoc.position,
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
    db.delete(review)
    db.commit()
    return {"ok": True}


@router.post("/api/reviews/{review_id}/questions")
def link_questions_to_review(review_id: str, items: list[QuestionCreate], request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    created_links = 0
    for it in items:
        # 1. Создаем сам вопрос в "банке"
        q = Question(
            question_text=it.question_text,
            question_type=QuestionType(it.question_type)
        )
        
        # 2. Сохраняем метаданные для range_slider
        if it.question_type == "range_slider" and it.options:
            import json
            q.meta_json = json.dumps(it.options)
        
        db.add(q)
        
        # 3. Если есть опции (для radio/checkbox), создаем их и привязываем к вопросу
        if it.question_type in ["radio", "checkbox"] and it.options:
            for i, opt_data in enumerate(it.options):
                opt = QuestionOption(
                    question=q,
                    option_text=opt_data.option_text,
                    position=i
                )
                db.add(opt)
        
        # 3. Создаем связь между ревью и новым вопросом
        link = ReviewQuestionLink(
            review_id=review_id,
            question=q,
            position=it.position,
            is_required=it.is_required
        )
        db.add(link)
        created_links += 1

    db.commit()
    return {"ok": True, "count": created_links}


@router.patch("/api/questions/{question_id}")
def update_question(question_id: str, patch: QuestionUpdate, request: Request, db: Session = Depends(get_db), t: str = Query(...), review_id: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    question = db.get(Question, question_id)
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
        
    patch_data = patch.model_dump(exclude_unset=True)
    
    # Обновляем текст вопроса
    if 'question_text' in patch_data:
        question.question_text = patch_data['question_text']
        
    # Обновляем опции (сложная логика: удаляем старые, добавляем новые)
    if 'options' in patch_data:
        if question.question_type in ["radio", "checkbox"]:
            # Удаляем старые опции для radio/checkbox
            for opt in question.options:
                db.delete(opt)
            db.flush() # Применяем удаление
            # Добавляем новые опции
            for opt_data in patch.options:
                new_opt = QuestionOption(
                    question_id=question.question_id,
                    option_text=opt_data.option_text,
                    position=opt_data.position
                )
                db.add(new_opt)
        elif question.question_type == "range_slider":
            # Сохраняем метаданные для range_slider
            import json
            question.meta_json = json.dumps(patch.options)

    db.commit()
    return {"ok": True}


@router.patch("/api/reviews/{review_id}/questions/{question_id}")
def update_review_question_link(review_id: str, question_id: str, patch: ReviewQuestionLinkUpdate, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")
    
    # Ищем связь по составному ключу
    link = db.execute(
        select(ReviewQuestionLink).where(
            ReviewQuestionLink.review_id == review_id,
            ReviewQuestionLink.question_id == question_id
        )
    ).scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Question link not found in this review")
        
    patch_data = patch.model_dump(exclude_unset=True)
    if not patch_data:
        return {"ok": True, "message": "No changes"}
        
    for key, value in patch_data.items():
        setattr(link, key, value)
        
    db.commit()
    return {"ok": True}


@router.delete("/api/reviews/{review_id}/questions/{question_id}")
def unlink_question_from_review(review_id: str, question_id: str, request: Request, db: Session = Depends(get_db), t: str = Query(...)):
    token = verify_token(t)
    if not token or token.get("role") != "admin" or token.get("sub") != review_id:
        raise HTTPException(status_code=401)
    if not verify_csrf(request, request.headers.get("X-CSRF-Token", ""), scope=f"admin:{review_id}"):
        raise HTTPException(status_code=403, detail="Bad CSRF")

    stmt = delete(ReviewQuestionLink).where(
        ReviewQuestionLink.review_id == review_id,
        ReviewQuestionLink.question_id == question_id
    )
    result = db.execute(stmt)
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Link not found")
    db.commit()
    return {"ok": True}
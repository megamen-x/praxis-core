# app/routers/api.py
from fastapi import APIRouter, Depends, HTTPException, Request, status, Form
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List
import json

from src.app.core.config import settings, OPENAI_CLIENT
from src.app.services.links import sign_token
from src.db.session import get_db
from src.db.models import (
    User,
    Review,
    Report,
    Survey, SurveyStatus, 
    Answer, AnswerSelection, 
    Question, QuestionOption, 
    ReviewStatus
)

from src.app.schemas.user import UserOut, UserCreate, UserUpdate
from src.app.schemas.report import ReportWithReviewOut
from src.app.schemas.survey import CreateSurveysIn, SurveyWithUserOut
from src.app.schemas.review import CreateReviewIn, ReviewOut

from src.llm_agg.prompts import (
    SIDES_EXTRACTING_PROMPT, 
    RECOMMENDATIONS_PROMPT, 
    BASE_PROMPT_WO_TASK
)
from src.llm_agg.schemas.sides import Sides
from src.llm_agg.response import get_so_completion
from src.llm_agg.utils import remove_ambiguous_sides
from src.llm_agg.schemas.recommendations import Recommendations
from src.llm_agg.reports.jinja import create_report

router = APIRouter()


@router.post("/api/user/fio", response_model=UserOut)
async def get_user_by_fio(user_data: UserCreate, db: Session = Depends(get_db)):
    """Получить список всех пользователей"""
    user = db.execute(
            select(User).where(
                User.middle_name == user_data.middle_name,
                User.first_name == user_data.first_name,
                User.last_name == user_data.last_name,
             )
        ).scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=400, 
            detail="User is not exist with this FIO"
        )
    return user 


@router.get("/api/user/{user_id}", response_model=UserOut)
async def get_user(user_id: str, db: Session = Depends(get_db)):
    """Получить пользователя по ID"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/api/user/telegram/{telegram_chat_id}", response_model=UserOut)
async def get_user_by_telegram(telegram_chat_id: str, db: Session = Depends(get_db)):
    """Получить пользователя по Telegram chat ID"""
    user = db.execute(
        select(User).where(User.telegram_chat_id == telegram_chat_id)
    ).scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/api/user", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Создать нового пользователя"""
    if user_data.telegram_chat_id:
        existing_user = db.execute(
            select(User).where(User.telegram_chat_id == user_data.telegram_chat_id)
        ).scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="User with this telegram_chat_id already exists"
            )
    
    user = User(**user_data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.post("/api/user/{user_id}/check-telegram", status_code=status.HTTP_201_CREATED)
async def check_telegram(user_id: str, db: Session = Depends(get_db)):
    """Проверить Telegram у человека"""
    user = db.get(User, user_id)
    if not user:
        return {'result': 'error'}
    return {'is_registered': 1 if user.tg_chat_id else 0}

@router.post("/api/user/{user_id}/is_admin", status_code=status.HTTP_201_CREATED)
async def is_admin(user_id: str, db: Session = Depends(get_db)):
    """Проверить человека на возможность создавать ревью"""
    user = db.get(User, user_id)
    if not user:
        return {'result': 'error'}
    return {'is_admin': 1 if user.can_create_review else 0}

@router.post("/api/user/{user_id}/protote_to_admin", status_code=status.HTTP_201_CREATED)
async def promote_to_admin(user_id: str, db: Session = Depends(get_db)):
    """Сделать человека админом"""
    user = db.get(User, user_id)
    if not user:
        return {'result': 'error'}
    if user.can_create_review:
        return {'result': 'already_admin'}
    else:
        user.can_create_review = True
        db.commit()
        db.refresh(user)
        return {'result': 'ok'}

@router.put("/api/user/{user_id}", response_model=UserOut)
async def update_user(user_id: str, user_data: UserUpdate, db: Session = Depends(get_db)):
    """Обновить пользователя"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Проверяем уникальность email если он указан
    if user_data.email and user_data.email != user.email:
        existing_user = db.execute(
            select(User).where(User.email == user_data.email)
        ).scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="User with this email already exists"
            )
    
    # Обновляем только переданные поля
    update_data = user_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/api/user/{user_id}")
async def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Удалить пользователя"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "User deleted successfully"}


@router.get("/api/user/{user_id}/reports", response_model=List[ReportWithReviewOut])
async def get_user_reports(user_id: str, db: Session = Depends(get_db)):
    """Получить отчеты по конкретному сотруднику (subject_user_id)"""
    # Проверяем существование пользователя
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все отчеты для пользователя через Review
    reports = db.execute(
        select(Report, Review, User)
        .join(Review, Report.review_id == Review.review_id)
        .join(User, Review.subject_user_id == User.user_id)
        .where(Review.subject_user_id == user_id)
    ).all()
    
    result = []
    for report, review, subject_user in reports:
        result.append(ReportWithReviewOut(
            report_id=report.report_id,
            review_id=report.review_id,
            strengths=report.strengths,
            growth_points=report.growth_points,
            dynamics=report.dynamics,
            prompt=report.prompt,
            analytics_for_reviewers=report.analytics_for_reviewers,
            recommendations=report.recommendations,
            review_title=review.title,
            review_description=review.description,
            review_status=review.status.value,
            review_created_at=review.created_at.isoformat(),
            subject_user_name=f"{subject_user.first_name} {subject_user.last_name}"
        ))
    
    return result


@router.get("/api/user/{user_id}/reviews", response_model=List[ReviewOut])
async def get_user_reviews(user_id: str, db: Session = Depends(get_db)):
    """Получить список Review по created_by_user_id"""
    # Проверяем существование пользователя
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все ревью для пользователя
    reviews = db.scalars(
        select(Review)
        .where(Review.created_by_user_id == user_id)
    ).all()
    
    result = []
    for review in reviews:
        result.append(ReviewOut(
            review_id=review.review_id,
            title=review.title,
            description=review.description,
            anonymity=review.anonymity,
            status=review.status.value,
            start_at=review.start_at,
            end_at=review.end_at,
        ))  
    
    return result


@router.get("/api/user/{user_id}/surveys", response_model=List[SurveyWithUserOut])
async def get_user_surveys(user_id: str, db: Session = Depends(get_db)):
    """Получить Survey по evaluator_user_id"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    surveys = db.execute(
        select(Survey, Review, User)
        .join(Review, Survey.review_id == Review.review_id)
        .outerjoin(User, Survey.evaluator_user_id == User.user_id)
        .where(Survey.evaluator_user_id == user_id)
    ).all()
    
    result = []
    for survey, review, evaluator_user in surveys:
        evaluator_name = None
        if evaluator_user:
            evaluator_name = f"{evaluator_user.first_name} {evaluator_user.last_name}"
        
        result.append(SurveyWithUserOut(
            survey_id=survey.survey_id,
            review_id=survey.review_id,
            evaluator_user_id=survey.evaluator_user_id,
            status=survey.status.value,
            is_declined=survey.is_declined,
            declined_reason=survey.declined_reason,
            notification_call=survey.notification_call,
            next_reminder_at=survey.next_reminder_at,
            submitted_at=survey.submitted_at,
            respondent_key=survey.respondent_key,
            evaluator_name=evaluator_name,
            review_title=review.title,
            review_description=review.description
        ))
    
    return result


@router.get("/api/review/{review_id}", response_model=ReviewOut)
async def get_review(review_id: str, db: Session = Depends(get_db)):
    """Получить информацию о ревью по ID"""
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    
    return ReviewOut(
        review_id=review.review_id,
        title=review.title,
        description=review.description,
        anonymity=review.anonymity,
        status=review.status.value,
        start_at=review.start_at,
        end_at=review.end_at,
        review_link=review.review_link
    )

@router.post("/api/review/create", response_model=ReviewOut)
# , _: None = Depends(require_bot_auth)
def create_review(
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
    review.review_link = admin_link
    db.commit()
    db.refresh(review)
    return review

@router.post("/api/reviews/{review_id}/surveys")
# _: None = Depends(require_bot_auth)
def create_surveys(
    review_id: str, payload: CreateSurveysIn, request: Request, db: Session = Depends(get_db), 
):
    review = db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    for uid in payload.evaluator_user_ids:
        s = Survey(review_id=review_id, evaluator_user_id=uid, status=SurveyStatus.not_started)
        db.add(s)
        db.commit()
        t = sign_token({"role": "respondent", "sub": s.survey_id}, ttl_sec=settings.RESPONDENT_LINK_TTL)
        s.survey_link = f"/form/{s.survey_id}?t={t}"
        # Инициализация notification_call: середина интервала [start_at, end_at]
        if review.start_at and review.end_at:
            s.notification_call = review.start_at + (review.end_at - review.start_at) / 2
        else:
            s.notification_call = None
        db.commit()
    return {'task': 'ok'}

@router.post("/api/review/get_report")
async def llm_aggregation(
    review_id: str = Form(...), db: Session = Depends(get_db)
):
    # Fetch surveys with the given review_id
    survey_ids = db.scalars(
        select(Survey.survey_id)
        .where(Survey.review_id == review_id)
    ).all()

    # Map survey_id -> evaluator_user_id for fast access
    surveys = db.execute(
        select(Survey.survey_id, Survey.evaluator_user_id)
        .where(Survey.survey_id.in_(survey_ids))
    ).all()
    survey_id_to_evaluator = {s_id: eval_uid for s_id, eval_uid in surveys}

    # Get review to compare subject_user_id for self-evaluation
    review = db.get(Review, review_id)

    subject_first_name = review.subject_user.first_name
    subject_last_name = review.subject_user.last_name
    subject_middle_name = review.subject_user.middle_name
    subject_name = ' '.join([subject_last_name, subject_first_name, subject_middle_name])
    answers = db.scalars(
        select(Answer)
        .where(Answer.survey_id.in_(survey_ids))
    ).all()

    grouped_text_answers = {}
    self_exteem = {}
    manage_esteem = {}
    for answer in answers:
        if answer.survey_id not in grouped_text_answers:
            grouped_text_answers[answer.survey_id] = {"response_texts": [], "option_texts": []}

        if answer.response_text:
            question = db.get(Question, answer.question_id)
            question_text = question.question_text if question else "Unknown Question"

            def _is_number(value: str) -> bool:
                try:
                    float(value)
                    return True
                except (TypeError, ValueError):
                    return False

            if _is_number(answer.response_text):
                if question_text not in manage_esteem:
                    manage_esteem[question_text] = []
                evaluator_user_id = survey_id_to_evaluator.get(answer.survey_id)
                if evaluator_user_id == review.subject_user_id:
                    self_exteem[question_text] = float(answer.response_text)
                else:
                    manage_esteem[question_text].append(float(answer.response_text)) 
            else:
                grouped_text_answers[answer.survey_id]["response_texts"].append([
                    question_text, answer.response_text
                ])
        else:
            # Fetch option_texts for answers with empty response_text
            option_texts = db.scalars(
                select(QuestionOption.option_text, Question.question_text)
                .join(AnswerSelection, AnswerSelection.option_id == QuestionOption.option_id)
                .join(Question, QuestionOption.question_id == Question.question_id)
                .where(AnswerSelection.answer_id == answer.answer_id)
            ).all()

            for option_text, question_text in option_texts:
                if _is_number(option_text):
                    if question_text not in manage_esteem:
                        manage_esteem[question_text] = []
                    evaluator_user_id = survey_id_to_evaluator.get(answer.survey_id)
                    if evaluator_user_id == review.subject_user_id:
                        self_exteem[question_text] = float(option_text)
                    else:
                        manage_esteem[question_text].append(float(option_text)) 
                else:
                    grouped_text_answers[answer.survey_id]["option_texts"].append([
                        question_text, option_text
                    ])
    
    for k, v in list(manage_esteem.items()):
        if isinstance(v, list):
            if len(v) > 0:
                manage_esteem[k] = sum(v) / len(v)
            else:
                manage_esteem[k] = None
    numeric_values = {
        'self-esteem': self_exteem,
        'manage-esteem': manage_esteem
    }
    feedback = ''

    for i, (_, v) in enumerate(grouped_text_answers.items()):
        feedback += f"Feedback from reviewer №{i+1}: \n"
        feedback += "\n".join([f"{item[0]}: {item[1]}" for item in v['response_texts']])
        feedback += "\n".join([f"{item[0]}: {item[1]}" for item in v['option_texts']])
        feedback += "\n"

    log = [
        {"role": "system", "content": BASE_PROMPT_WO_TASK},
        {"role": "user", "content": SIDES_EXTRACTING_PROMPT.format(feedback=feedback)}
    ]

    completion = await get_so_completion(
        log=log, 
        model_name=settings.MODEL_NAME, 
        client=OPENAI_CLIENT, 
        pydantic_model=Sides, 
        provider_name='openrouter'
    )

    new_msg = {
        "role":"assistant",
        "content": remove_ambiguous_sides(completion)
    }
    log.append(new_msg)
    
    new_user_msg = {
        "role": "user",
        "content": RECOMMENDATIONS_PROMPT
    }
    log.append(new_user_msg)

    rec = await get_so_completion(
        log, 
        model_name=settings.MODEL_NAME, 
        client=OPENAI_CLIENT, 
        pydantic_model=Recommendations, 
        provider_name='openrouter'
    )
    print(self_exteem, manage_esteem)
    path_to_file = str(create_report(
        templates_dir='jinja_templates',
        template_name='base.html.jinja',
        sides_json=json.loads(completion),
        recommendations_json=json.loads(rec),
        numeric_values=numeric_values,
        employee_name=subject_name,
        visualization_url=None,
        quotes_layout="inline",
        write_intermediate_html=True
    ))
    return {"path_to_file": path_to_file}

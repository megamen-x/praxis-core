# app/routers/users.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from db.session import get_db
from db.models import User, Review, Report, Survey
from app.schemas.user import UserOut, UserCreate, UserUpdate
from app.schemas.report import ReportWithReviewOut
from app.schemas.review import ReviewWithUserOut
from app.schemas.survey import SurveyWithUserOut
from app.services.export import export_database_to_json, export_database_to_csv, export_user_data
from fastapi.responses import JSONResponse, Response
from typing import List

router = APIRouter()


@router.get("/api/users", response_model=List[UserOut])
def get_users(db: Session = Depends(get_db)):
    """Получить список всех пользователей"""
    users = db.execute(select(User)).scalars().all()
    return users


@router.get("/api/users/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: Session = Depends(get_db)):
    """Получить пользователя по ID"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/api/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Создать нового пользователя"""
    # Проверяем уникальность email если он указан
    if user_data.email:
        existing_user = db.execute(
            select(User).where(User.email == user_data.email)
        ).scalar_one_or_none()
        if existing_user:
            raise HTTPException(
                status_code=400, 
                detail="User with this email already exists"
            )
    
    user = User(**user_data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/api/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, user_data: UserUpdate, db: Session = Depends(get_db)):
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


@router.delete("/api/users/{user_id}")
def delete_user(user_id: str, db: Session = Depends(get_db)):
    """Удалить пользователя"""
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    return {"ok": True, "message": "User deleted successfully"}


@router.get("/api/users/{user_id}/reports", response_model=List[ReportWithReviewOut])
def get_user_reports(user_id: str, db: Session = Depends(get_db)):
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


@router.get("/api/users/{user_id}/reviews", response_model=List[ReviewWithUserOut])
def get_user_reviews(user_id: str, db: Session = Depends(get_db)):
    """Получить список Review по subject_user_id"""
    # Проверяем существование пользователя
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все ревью для пользователя
    reviews = db.execute(
        select(Review, User, User)
        .join(User, Review.created_by_user_id == User.user_id, aliased=True)
        .join(User, Review.subject_user_id == User.user_id, aliased=True)
        .where(Review.subject_user_id == user_id)
    ).all()
    
    result = []
    for review, created_by_user, subject_user in reviews:
        result.append(ReviewWithUserOut(
            review_id=review.review_id,
            created_by_user_id=review.created_by_user_id,
            subject_user_id=review.subject_user_id,
            title=review.title,
            description=review.description,
            anonymity=review.anonymity,
            status=review.status.value,
            start_at=review.start_at,
            end_at=review.end_at,
            created_at=review.created_at,
            created_by_name=f"{created_by_user.first_name} {created_by_user.last_name}",
            subject_user_name=f"{subject_user.first_name} {subject_user.last_name}"
        ))
    
    return result


@router.get("/api/users/{user_id}/surveys", response_model=List[SurveyWithUserOut])
def get_user_surveys(user_id: str, db: Session = Depends(get_db)):
    """Получить Survey по evaluator_user_id"""
    # Проверяем существование пользователя
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Получаем все опросы для пользователя как evaluator
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
            next_reminder_at=survey.next_reminder_at,
            submitted_at=survey.submitted_at,
            respondent_key=survey.respondent_key,
            evaluator_name=evaluator_name,
            review_title=review.title,
            review_description=review.description
        ))
    
    return result


@router.get("/api/export/database/json")
def export_database_json(db: Session = Depends(get_db)):
    """Экспортировать всю базу данных в формате JSON"""
    try:
        json_data = export_database_to_json(db)
        return JSONResponse(
            content=json.loads(json_data),
            media_type="application/json"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при экспорте: {str(e)}")


@router.get("/api/export/database/csv")
def export_database_csv(db: Session = Depends(get_db)):
    """Экспортировать всю базу данных в формате CSV (ZIP архив)"""
    try:
        import zipfile
        import io
        
        csv_data = export_database_to_csv(db)
        
        # Создаем ZIP архив с CSV файлами
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename, content in csv_data.items():
                zip_file.writestr(filename, content)
        
        zip_buffer.seek(0)
        
        return Response(
            content=zip_buffer.getvalue(),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=database_export.zip"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при экспорте: {str(e)}")


@router.get("/api/export/users/{user_id}")
def export_user_data_endpoint(user_id: str, db: Session = Depends(get_db)):
    """Экспортировать данные конкретного пользователя"""
    try:
        # Проверяем существование пользователя
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        json_data = export_user_data(db, user_id)
        return JSONResponse(
            content=json.loads(json_data),
            media_type="application/json"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при экспорте: {str(e)}")

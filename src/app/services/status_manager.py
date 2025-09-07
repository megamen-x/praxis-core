# app/services/status_manager.py
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, update, and_
from src.db.models import Review, Survey, ReviewStatus, SurveyStatus
from src.app.services.notification import get_notification_service

logger = logging.getLogger(__name__)


class StatusManager:
    """Сервис для автоматического управления статусами Review и Survey"""
    
    def __init__(self, db: Session):
        self.db = db
        self.notification_service = get_notification_service()
    
    async def update_review_statuses(self) -> Tuple[int, int, int]:
        """
        Обновляет статусы всех Review на основе времени
        
        Returns:
            Tuple[int, int, int]: (started_count, completed_count, archived_count)
        """
        current_time = datetime.now(timezone.utc)
        one_year_ago = current_time - timedelta(days=365)
        
        started_count = 0
        completed_count = 0
        archived_count = 0
        
        # 1. Начинаем ревью (draft -> in_progress)
        started_reviews = await self._start_reviews(current_time)
        started_count = len(started_reviews)
        
        # 2. Завершаем ревью (in_progress -> completed)
        completed_reviews = await self._complete_reviews(current_time)
        completed_count = len(completed_reviews)
        
        # 3. Архивируем старые ревью (completed -> archived)
        archived_reviews = await self._archive_reviews(one_year_ago)
        archived_count = len(archived_reviews)
        
        return started_count, completed_count, archived_count
    
    async def update_survey_statuses(self) -> int:
        """
        Обновляет статусы Survey на основе статуса Review
        
        Returns:
            int: количество обновленных опросов
        """
        updated_count = 0
        
        # Получаем все активные опросы
        active_surveys = self.db.execute(
            select(Survey, Review)
            .join(Review, Survey.review_id == Review.review_id)
            .where(
                and_(
                    Survey.status.in_([SurveyStatus.not_started, SurveyStatus.in_progress]),
                    Review.status == ReviewStatus.in_progress
                )
            )
        ).all()
        
        for survey, review in active_surveys:
            # Если ревью началось, но опрос еще не начат - переводим в in_progress
            if survey.status == SurveyStatus.not_started:
                survey.status = SurveyStatus.in_progress
                updated_count += 1
                logger.info(f"Survey {survey.survey_id} переведен в статус in_progress")
        
        # Получаем все опросы, где ревью завершено
        completed_reviews = self.db.execute(
            select(Review)
            .where(Review.status == ReviewStatus.completed)
        ).scalars().all()
        
        for review in completed_reviews:
            # Находим все не завершенные опросы для этого ревью
            incomplete_surveys = self.db.execute(
                select(Survey)
                .where(
                    and_(
                        Survey.review_id == review.review_id,
                        Survey.status.in_([SurveyStatus.not_started, SurveyStatus.in_progress])
                    )
                )
            ).scalars().all()
            
            for survey in incomplete_surveys:
                survey.status = SurveyStatus.expired
                updated_count += 1
                logger.info(f"Survey {survey.survey_id} переведен в статус expired")
        
        self.db.commit()
        return updated_count
    
    async def _start_reviews(self, current_time: datetime) -> List[Review]:
        """Начинает ревью, время которых пришло"""
        reviews_to_start = self.db.execute(
            select(Review)
            .where(
                and_(
                    Review.status == ReviewStatus.draft,
                    Review.start_at.isnot(None),
                    Review.start_at <= current_time
                )
            )
        ).scalars().all()
        
        for review in reviews_to_start:
            review.status = ReviewStatus.in_progress
            logger.info(f"Review {review.review_id} переведен в статус in_progress")
        
        self.db.commit()
        return reviews_to_start
    
    async def _complete_reviews(self, current_time: datetime) -> List[Review]:
        """Завершает ревью, время которых истекло"""
        reviews_to_complete = self.db.execute(
            select(Review)
            .where(
                and_(
                    Review.status == ReviewStatus.in_progress,
                    Review.end_at.isnot(None),
                    Review.end_at <= current_time
                )
            )
        ).scalars().all()
        
        for review in reviews_to_complete:
            review.status = ReviewStatus.completed
            logger.info(f"Review {review.review_id} переведен в статус completed")
            
            # Отправляем уведомление о готовности отчета
            try:
                await self.notification_service.send_notification(
                    user_id=review.created_by_user_id,
                    message=f"📊 Отчет готов!\n\nРевью: {review.title}",
                    db=self.db
                )
                logger.info(f"Уведомление отправлено для Review {review.review_id}")
            except Exception as e:
                logger.error(f"Ошибка отправки уведомления для Review {review.review_id}: {e}")
        
        self.db.commit()
        return reviews_to_complete
    
    async def _archive_reviews(self, one_year_ago: datetime) -> List[Review]:
        """Архивирует старые завершенные ревью"""
        reviews_to_archive = self.db.execute(
            select(Review)
            .where(
                and_(
                    Review.status == ReviewStatus.completed,
                    Review.end_at.isnot(None),
                    Review.end_at <= one_year_ago
                )
            )
        ).scalars().all()
        
        for review in reviews_to_archive:
            review.status = ReviewStatus.archived
            logger.info(f"Review {review.review_id} переведен в статус archived")
        
        self.db.commit()
        return reviews_to_archive
    
    async def process_all_statuses(self) -> dict:
        """
        Обрабатывает все статусы Review и Survey
        
        Returns:
            dict: статистика обновлений
        """
        try:
            # Обновляем статусы ревью
            started, completed, archived = await self.update_review_statuses()
            
            # Обновляем статусы опросов
            surveys_updated = await self.update_survey_statuses()
            
            stats = {
                "reviews_started": started,
                "reviews_completed": completed,
                "reviews_archived": archived,
                "surveys_updated": surveys_updated,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
            logger.info(f"Статусы обновлены: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка при обновлении статусов: {e}")
            raise


def get_status_manager(db: Session) -> StatusManager:
    """Получить экземпляр менеджера статусов"""
    return StatusManager(db)

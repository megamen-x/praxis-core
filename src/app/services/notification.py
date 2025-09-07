# app/services/notification.py
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from src.db.models import Review, User
from src.app.routers.telegram import send_telegram_message

logger = logging.getLogger(__name__)


async def check_review_notifications_task(db: Session):
    """
    Проверить и отправить уведомления о готовности отчетов
    
    :param db: Сессия базы данных
    """
    current_time = datetime.now(timezone.utc)
    
    # Найти все ревью, где end_at совпадает с текущим временем (с точностью до минуты)
    reviews = db.execute(
        select(Review, User)
        .join(User, Review.created_by_user_id == User.user_id)
        .where(
            and_(
                Review.end_at.isnot(None),
                Review.end_at <= current_time,
                Review.status == "completed"  # Только завершенные ревью
            )
        )
    ).all()
    
    for review, user in reviews:
        message = f"📊 Отчет готов!\n\nРевью: {review.title}\nСотрудник: {user.first_name} {user.last_name}"
        request = {
            "user_id": review.created_by_user_id,
            "message": message
            }
        response = await send_telegram_message(request)
        
        if response.success:
            logger.info(f"Уведомление о готовности отчета отправлено для ревью {review.review_id}")

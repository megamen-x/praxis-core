# app/services/notification.py
import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from src.db.models import Review, User
from src.app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Сервис для отправки уведомлений в Telegram"""
    
    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.bot = None
    
    async def _get_bot(self):
        """Ленивая инициализация бота"""
        if self.bot is None:
            from aiogram import Bot
            from aiogram.client.default import DefaultBotProperties
            from aiogram.enums import ParseMode
            
            self.bot = Bot(
                token=self.bot_token, 
                default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
            )
        return self.bot
    
    async def send_notification(self, user_id: str, message: str, db: Session) -> bool:
        """
        Отправить уведомление пользователю в Telegram
        
        :param user_id: ID пользователя в системе
        :param message: Текст сообщения
        :param db: Сессия базы данных
        :return: True если сообщение отправлено успешно
        """
        try:
            # Получаем пользователя из базы данных
            user = db.get(User, user_id)
            if not user or not user.telegram_chat_id:
                logger.warning(f"Пользователь {user_id} не найден или не имеет telegram_chat_id")
                return False
            
            bot = await self._get_bot()
            
            await bot.send_message(
                chat_id=user.telegram_chat_id,
                text=message
            )
            
            logger.info(f"Уведомление отправлено пользователю {user_id} (chat_id: {user.telegram_chat_id}): {message}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
            return False
    
    async def check_and_send_review_notifications(self, db: Session):
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
            
            success = await self.send_notification(
                user_id=review.created_by_user_id,
                message=message,
                db=db
            )
            
            if success:
                # Можно добавить флаг, что уведомление отправлено
                # чтобы не отправлять повторно
                logger.info(f"Уведомление о готовности отчета отправлено для ревью {review.review_id}")


# Глобальный экземпляр сервиса
notification_service = None


def get_notification_service() -> NotificationService:
    """Получить экземпляр сервиса уведомлений"""
    global notification_service
    if notification_service is None:
        notification_service = NotificationService(settings.TG_BOT_TOKEN)
    return notification_service


async def check_review_notifications_task(db: Session):
    """Задача для периодической проверки уведомлений"""
    service = get_notification_service()
    await service.check_and_send_review_notifications(db)

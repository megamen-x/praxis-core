# src/app/services/status_manager.py
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from src.app.core.config import settings
from src.db.session import LocalSession
from src.db.models import Review, Survey, ReviewStatus, SurveyStatus
from src.app.services.telegram_bot import get_telegram_bot_service

logger = logging.getLogger(__name__)


def _minute_window(now: datetime) -> Tuple[datetime, datetime]:
    start = now.replace(second=0, microsecond=0)
    end = start + timedelta(minutes=1)
    return start, end


async def _send_many(messages: list[tuple[int, str, str]]) -> None:
    if not messages:
        return

    bot_service = get_telegram_bot_service()
    if not bot_service:
        logger.warning("Telegram bot service is not available. %d message(s) skipped.", len(messages))
        return

    for chat_id, text, url in messages:
        try:
            if url!='':
                kb = InlineKeyboardBuilder()
                site_url = 'http://'+ settings.HOST + ':' + settings.PORT
                kb.button(text='Пройти опрос', url=site_url + url)
                await bot_service.bot.send_message(
                    chat_id=chat_id,
                    text=text,
                    reply_markup=kb.as_markup()
                )
            else:
                await bot_service.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logger.error("Failed to send message to %s: %s", chat_id, e)


async def _process_start_reviews(db: Session, now: datetime) -> int:
    """
    Переводит ревью со статусом draft в in_progress, если start_at совпадает по минуте.
    Рассылает ссылки на прохождение Survey их участникам.
    """
    start, end = _minute_window(now)

    q = (
        select(Review)
        .options(selectinload(Review.surveys).selectinload(Survey.evaluator))
        .where(
            and_(
                Review.status == ReviewStatus.draft,
                Review.start_at.isnot(None),
                Review.start_at >= start,
                Review.start_at < end,
            )
        )
    )
    reviews = db.execute(q).scalars().all()
    if not reviews:
        return 0

    messages: list[tuple[int, str, str]] = []

    for review in reviews:
        review.status = ReviewStatus.in_progress

        for survey in review.surveys:
            # Переводим опросы в in_progress, если еще не начаты
            if survey.status == SurveyStatus.not_started:
                survey.status = SurveyStatus.in_progress

            # Готовим отправку ссылок участникам
            evaluator = survey.evaluator
            if not evaluator:
                continue

            chat_id = evaluator.telegram_chat_id
            if not chat_id:
                logger.debug("No telegram chat_id for user %s (survey %s)", evaluator.user_id, survey.survey_id)
                continue

            link = survey.survey_link or review.review_link or ""
            text = f"📝 Вам доступен опрос по ревью «{review.title}»"
            messages.append((chat_id, text, link))

    db.commit()

    await _send_many(messages)

    logger.info("Started %d review(s) at %s", len(reviews), start.isoformat())
    return len(reviews)


async def _process_end_reviews(db: Session, now: datetime) -> int:
    """
    Переводит ревью со статусом in_progress в completed, если end_at совпадает по минуте.
    Помечает незавершенные опросы как expired и отправляет создателю Review уведомление «Отчет готов».
    """
    start, end = _minute_window(now)

    q = (
        select(Review)
        .options(selectinload(Review.surveys), selectinload(Review.created_by))
        .where(
            and_(
                Review.status == ReviewStatus.in_progress,
                Review.end_at.isnot(None),
                Review.end_at >= start,
                Review.end_at < end,
            )
        )
    )
    reviews = db.execute(q).scalars().all()
    if not reviews:
        return 0

    messages: list[tuple[int, str]] = []

    for review in reviews:
        review.status = ReviewStatus.completed

        # Все незавершенные опросы помечаем как expired
        for survey in review.surveys:
            if survey.status in (SurveyStatus.not_started, SurveyStatus.in_progress):
                survey.status = SurveyStatus.expired

        # Сообщение создателю ревью
        creator = review.created_by
        if creator:
            chat_id = creator.telegram_chat_id
            if chat_id:
                link = ""
                text = f"📊 Отчет готов."
                messages.append((chat_id, text, link))
            else:
                logger.debug("No telegram chat_id for creator %s (review %s)", creator.user_id, review.review_id)

    db.commit()

    await _send_many(messages)

    logger.info("Completed %d review(s) at %s", len(reviews), start.isoformat())
    return len(reviews)


async def process_tick(now: Optional[datetime] = None) -> dict:
    """
    Один «тик» планировщика: обработать старт/завершение ревью, разослать уведомления.
    Возвращает статистику по обновлениям.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    with LocalSession() as db:
        started = await _process_start_reviews(db, now)
        completed = await _process_end_reviews(db, now)

        return {
            "reviews_started": started,
            "reviews_completed": completed,
            "timestamp": now.isoformat(),
        }


async def run_status_manager_loop():
    """
    Фоновая задача: запускать process_tick каждую минуту (по границам минут).
    """
    logger.info("Status manager loop started")
    # Небольшая задержка, чтобы дать боту подняться
    await asyncio.sleep(0.5)

    while True:
        try:
            now = datetime.now(timezone.utc)
            stats = await process_tick(now)
            if stats["reviews_started"] or stats["reviews_completed"]:
                logger.info("StatusManager stats: %s", stats)
        except Exception as e:
            logger.exception("StatusManager tick failed: %s", e)

        now2 = datetime.now(timezone.utc)
        minute_start = now2.replace(second=0, microsecond=0)
        next_minute = minute_start + timedelta(minutes=1)
        sleep_s = (next_minute - now2).total_seconds()
        await asyncio.sleep(max(0.5, sleep_s))
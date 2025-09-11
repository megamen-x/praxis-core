# src/app/services/status_manager.py
import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple

from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import FSInputFile
import httpx
from sqlalchemy import and_, select
from sqlalchemy.orm import Session, selectinload

from src.db.session import LocalSession
from src.db.models import Review, Survey, ReviewStatus, SurveyStatus
from src.app.services.telegram_bot import get_telegram_bot_service
from src.app.core.logging import get_logs_writer_logger

from dotenv import dotenv_values

logger = get_logs_writer_logger()

config = dotenv_values(".env")

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
            kb = InlineKeyboardBuilder()
            site_url = config.get("BACKEND_URL", "http://127.0.0.1:8000")
            kb.button(text='Пройти опрос', url=site_url + url)
            await bot_service.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=kb.as_markup()
            )
        except Exception as e:
            logger.error("Failed to send message to %s: %s", chat_id, e)

async def _send_hrs(messages: list[tuple[int, str, str]]) -> None:
    if not messages:
        return

    bot_service = get_telegram_bot_service()
    if not bot_service:
        logger.warning("Telegram bot service is not available. %d message(s) skipped.", len(messages))
        return

    for chat_id, text, path_to_file in messages:
        try:
            document = FSInputFile(path_to_file)
            await bot_service.bot.send_document(
                chat_id=chat_id,
                document=document,
                caption=text,
            )
        except Exception as e:
            logger.error("Failed to send message to %s: %s", chat_id, e)


async def _send_hr_text(messages: list[tuple[int, str, str]]) -> None:
    """Отправка HR текстовых уведомлений с ссылкой на форму ревью."""
    if not messages:
        return

    bot_service = get_telegram_bot_service()
    if not bot_service:
        logger.warning("Telegram bot service is not available. %d message(s) skipped.", len(messages))
        return

    for chat_id, text, url in messages:
        try:
            await bot_service.bot.send_message(
                chat_id=chat_id,
                text=text,
            )
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
            if survey.status == SurveyStatus.not_started:
                survey.status = SurveyStatus.in_progress

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

        for survey in review.surveys:
            if survey.status in (SurveyStatus.not_started, SurveyStatus.in_progress):
                survey.status = SurveyStatus.expired

        creator = review.created_by
        if creator:
            chat_id = creator.telegram_chat_id
            if chat_id:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    params = {
                        "review_id": review.review_id,
                    }
                    
                    resp = await client.post(config.get("BACKEND_URL", "http://127.0.0.1:8000") + '/api/review/get_report', data=params)
                    data = resp.json()
                    path_to_report = data["path_to_file"]
                text = f"📊 Отчет к ревью «{review.title}»"
                messages.append((chat_id, text, path_to_report))
            else:
                logger.debug("No telegram chat_id for creator %s (review %s)", creator.user_id, review.review_id)

    db.commit()

    await _send_hrs(messages)

    logger.info("Completed %d review(s) at %s", len(reviews), start.isoformat())
    return len(reviews)


async def _process_survey_reminders(db: Session, now: datetime) -> int:
    """
    Отправляет напоминания по опросам, у которых наступил `notification_call`.
    После отправки переносит `notification_call` в середину между текущим `notification_call` и `review.end_at`.
    Последнее изменение выполняется, если до `review.end_at` остается 1 день или меньше — устанавливает `notification_call` на `review.end_at`.
    Не шлёт напоминания, если опрос завершён/отклонён/просрочен.
    """
    start, end = _minute_window(now)

    q = (
        select(Survey)
        .options(selectinload(Survey.review), selectinload(Survey.evaluator))
        .where(
            and_(
                Survey.status.in_([SurveyStatus.not_started, SurveyStatus.in_progress]),
                Survey.notification_call.isnot(None),
                Survey.notification_call >= start,
                Survey.notification_call < end,
            )
        )
    )
    surveys = db.execute(q).scalars().all()
    if not surveys:
        return 0

    messages: list[tuple[int, str, str]] = []

    for survey in surveys:
        review = survey.review
        evaluator = survey.evaluator
        if not review or not evaluator:
            continue
        if review.status != ReviewStatus.in_progress:
            continue
        if not evaluator.telegram_chat_id:
            continue

        link = survey.survey_link or review.review_link or ""
        text = f"🔔 Напоминание: пройдите опрос по ревью «{review.title}»"

        if review.end_at:
            if review.end_at - now <= timedelta(days=1):
                text = f"🔔 Напоминание: осталось менее суток на прохождение опроса по ревью «{review.title}»"
                survey.notification_call = None
            else:
                if survey.notification_call:
                    midpoint = survey.notification_call + (review.end_at - survey.notification_call) / 2
                    survey.notification_call = midpoint
        else:
            survey.notification_call = None

        messages.append((evaluator.telegram_chat_id, text, link))
        
    db.commit()

    await _send_many(messages)

    logger.info("Sent %d survey reminder(s) at %s", len(messages), start.isoformat())
    return len(messages)


async def _process_hr_day_before_end(db: Session, now: datetime) -> int:
    """
    За 1 день до окончания ревью уведомить HR (создателя), если есть незавершенные опросы.
    Отправляется однократно, когда `review.end_at` ровно через 1 день от текущего времени (окно по минуте).
    """
    target = now + timedelta(days=1)
    start = target.replace(second=0, microsecond=0)
    end = start + timedelta(minutes=1)

    q = (
        select(Review)
        .options(selectinload(Review.surveys).selectinload(Survey.evaluator), selectinload(Review.created_by))
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

    messages: list[tuple[int, str, str]] = []

    for review in reviews:
        pending = [s for s in review.surveys if s.status in (SurveyStatus.not_started, SurveyStatus.in_progress)]
        if not pending:
            continue
        creator = review.created_by
        if not creator or not creator.telegram_chat_id:
            continue
        names: list[str] = []
        for s in pending:
            ev = s.evaluator
            if ev:
                parts = [p for p in [ev.last_name, ev.first_name, ev.middle_name, f'@{ev.telegram_username}'] if p]
                names.append(' '.join(parts))
        names_text = '\n'.join(f"• {n}" for n in names) if names else "—"
        text = (
            f"⏰ До окончания ревью «{review.title}» остался 1 день.\n"
            f"Не завершили опрос:\n{names_text}"
        )
        messages.append((creator.telegram_chat_id, text, review.review_link or ''))

    await _send_hr_text(messages)
    logger.info("Sent %d HR day-before reminder(s) at %s", len(messages), start.isoformat())
    return len(messages)


async def process_tick(now: Optional[datetime] = None) -> dict:
    """
    Один «тик» планировщика: обработать старт/завершение ревью, разослать уведомления.
    Возвращает статистику по обновлениям.
    """
    if now is None:
        now = datetime.now(timezone.utc)

    with LocalSession() as db:
        started = await _process_start_reviews(db, now)
        reminders = await _process_survey_reminders(db, now)
        hr_day_before = await _process_hr_day_before_end(db, now)
        completed = await _process_end_reviews(db, now)

        return {
            "reviews_started": started,
            "reviews_completed": completed,
            "survey_reminders": reminders,
            "hr_day_before": hr_day_before,
            "timestamp": now.isoformat(),
        }


async def run_status_manager_loop():
    """
    Фоновая задача: запускать process_tick каждую минуту (по границам минут).
    """
    logger.info("Status manager loop started")
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
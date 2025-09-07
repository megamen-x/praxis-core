# app/main.py
import asyncio
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.app.core.config import settings
from src.db.session import engine, get_db
from src.db import Base
from src.app.routers import admin, surveys, tg, users
from src.app.services.notification import check_review_notifications_task

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(admin.router)
app.include_router(surveys.router)
app.include_router(tg.router)
app.include_router(users.router)


@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    
    # Запускаем фоновую задачу для проверки уведомлений
    asyncio.create_task(notification_checker())


async def notification_checker():
    """Фоновая задача для проверки уведомлений каждую минуту"""
    while True:
        try:
            # Получаем сессию базы данных
            db = next(get_db())
            await check_review_notifications_task(db)
            db.close()
        except Exception as e:
            logger.error(f"Ошибка в задаче проверки уведомлений: {e}")
        
        # Ждем 60 секунд перед следующей проверкой
        await asyncio.sleep(settings.NOTIFICATION_TIMER)


@app.get("/health")
def health():
    return {"status": "ok"}
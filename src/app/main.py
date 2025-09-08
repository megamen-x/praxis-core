# app/main.py
import asyncio
import logging
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from src.app.core.config import settings
from src.db.session import engine
from src.db import Base
from src.app.routers import admin, surveys, api
from src.app.services.telegram_bot import start_telegram_bot
from src.app.services.status_manager import run_status_manager_loop

logger = logging.getLogger(__name__)

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)

app.mount("/static", StaticFiles(directory="src/app/static"), name="static")
templates = Jinja2Templates(directory=settings.JINJA2_TEMPLATES)

app.include_router(admin.router)
app.include_router(surveys.router)
app.include_router(api.router)

@app.on_event("startup")
async def on_startup():
    Base.metadata.create_all(bind=engine)
    
    # Запускаем Telegram-бота параллельно с приложением
    asyncio.create_task(start_telegram_bot())
    # Запускаем статус-менеджер параллельно с приложением
    asyncio.create_task(run_status_manager_loop())


@app.get("/health")
def health():
    return {"status": "ok"}
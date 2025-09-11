"""Application configuration and LLM client initialization.

Defines `Settings` with environment variables and creates an `OPENAI_CLIENT'.
"""
# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from openai import AsyncOpenAI

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")
    
    OPENAI_BASE_URL: str = "https://openrouter.ai/api/v1"
    OPENAI_API_KEY: str = 'your_api_key'
    MODEL_NAME: str = 'openai/gpt-4o'

    APP_NAME: str = "Proxis Core"
    BACKEND_URL: str = "http://127.0.0.1:8000"
    DEBUG: bool = True
    NOTIFICATION_TIMER: int = 60
    LOG_PATH: str="logging"
    SECRET_KEY: str = "change-me-in-env"
    DATABASE_URL: str = "sqlite:///./app.db"
    BOT_TOKEN: str = "change-me-in-env"
    
    CSRF_COOKIE_NAME: str = "csrf_seed"
    CSRF_COOKIE_SECURE: bool = False
    CSRF_COOKIE_SAMESITE: str = "lax"
    CSRF_COOKIE_HTTPONLY: bool = False  # double submit pattern

    ADMIN_LINK_TTL: int = 60 * 60 * 24  # 24h
    RESPONDENT_LINK_TTL: int = 60 * 60 * 24 * 7  # 7 days
    JINJA2_TEMPLATES: str = "src/app/templates"


settings = Settings()
OPENAI_CLIENT = AsyncOpenAI(base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY)

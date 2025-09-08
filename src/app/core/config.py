# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_NAME: str = "Proxis Core"
    BASE_URL: str = "https://openrouter.ai/api/v1"
    DEBUG: bool = True
    NOTIFICATION_TIMER: int = 60
    HOST: str="127.0.0.1"
    PORT: str="8000"
    SECRET_KEY: str = "change-me-in-env"
    DATABASE_URL: str = "sqlite:///./app.db"
    TG_BOT_TOKEN: str = "change-me-in-env"

    CSRF_COOKIE_NAME: str = "csrf_seed"
    CSRF_COOKIE_SECURE: bool = False
    CSRF_COOKIE_SAMESITE: str = "lax"
    CSRF_COOKIE_HTTPONLY: bool = False  # double submit pattern

    ADMIN_LINK_TTL: int = 60 * 60 * 24  # 24h
    RESPONDENT_LINK_TTL: int = 60 * 60 * 24 * 7  # 7 days
    JINJA2_TEMPLATES: str = "src/app/templates"


settings = Settings()
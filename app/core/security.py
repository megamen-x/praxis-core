# app/core/security.py
import hmac
import hashlib
import base64
import secrets
from fastapi import Request, HTTPException, status
from fastapi.responses import Response
from app.core.config import settings


def issue_csrf(response: Response, scope: str) -> str:
    seed = secrets.token_urlsafe(18)
    response.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=seed,
        secure=settings.CSRF_COOKIE_SECURE,
        httponly=settings.CSRF_COOKIE_HTTPONLY,
        samesite=settings.CSRF_COOKIE_SAMESITE,
        path="/",
    )
    raw = f"{seed}:{scope}".encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(sig).decode()


def verify_csrf(request: Request, token: str, scope: str) -> bool:
    seed = request.cookies.get(settings.CSRF_COOKIE_NAME)
    if not seed or not token:
        return False
    try:
        expected_raw = f"{seed}:{scope}".encode()
        expected_sig = hmac.new(settings.SECRET_KEY.encode(), expected_raw, hashlib.sha256).digest()
        given = base64.urlsafe_b64decode(token.encode())
        return hmac.compare_digest(given, expected_sig)
    except Exception:
        return False


def require_bot_auth(request: Request):
    token = request.headers.get("X-Service-Token")
    if not token or token != settings.TG_BOT_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized bot")
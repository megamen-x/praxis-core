# app/services/links.py
import time
import hmac
import hashlib
import base64
import json
from typing import Optional
from src.app.core.config import settings


def sign_token(payload: dict, ttl_sec: int) -> str:
    data = payload | {"exp": int(time.time()) + ttl_sec}
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + sig).decode()


def verify_token(token: str) -> Optional[dict]:
    try:
        blob = base64.urlsafe_b64decode(token.encode())
        raw, sig = blob.rsplit(b".", 1)
        expected = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None
        data = json.loads(raw.decode())
        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None
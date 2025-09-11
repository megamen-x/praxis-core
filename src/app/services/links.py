# app/services/links.py
import time, hmac, hashlib, base64, json
from typing import Optional
from src.app.core.config import settings

def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

def _b64u_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)

def sign_token(payload: dict, ttl_sec: int) -> str:
    data = payload | {"exp": int(time.time()) + int(ttl_sec)}
    raw = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
    sig = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).digest()
    return f"{_b64u_encode(raw)}.{_b64u_encode(sig)}"

def verify_token(token: str) -> Optional[dict]:
    try:
        raw_b64, sig_b64 = token.split(".", 1)
        raw = _b64u_decode(raw_b64)
        sig = _b64u_decode(sig_b64)

        expected = hmac.new(settings.SECRET_KEY.encode(), raw, hashlib.sha256).digest()
        if not hmac.compare_digest(sig, expected):
            return None

        data = json.loads(raw.decode())
        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None
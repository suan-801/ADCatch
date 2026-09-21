"""Viewer/Admin 권한 — 공용 Admin 비밀번호 + stateless 서명 세션 쿠키.

사용자 계정 시스템이 아니다 (User/default_admin 구조는 그대로 둔다). 세션을 서버 메모리나
DB에 저장하지 않고 "만료시각.HMAC서명" 토큰을 쿠키에 그대로 담아 검증하므로, 여러 워커/인스턴스로
수평 확장되는 배포(Vercel + 별도 backend 등)에서도 별도 공유 저장소 없이 동일하게 동작한다.
"""

import hashlib
import hmac
import threading
import time
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Response

from app.config import settings

ADMIN_COOKIE_NAME = "adcatcher_admin_session"


def hash_password(raw_password: str) -> str:
    """scripts/hash_admin_password.py 에서 ADMIN_PASSWORD_HASH 값을 만들 때 사용."""
    return bcrypt.hashpw(raw_password.encode(), bcrypt.gensalt()).decode()


def verify_password(raw_password: str) -> bool:
    if not settings.admin_password_hash:
        return False
    try:
        return bcrypt.checkpw(raw_password.encode(), settings.admin_password_hash.encode())
    except ValueError:
        # ADMIN_PASSWORD_HASH가 유효한 bcrypt hash가 아닌 경우 — 설정 오류를 조용히 통과시키지 않는다.
        return False


def _sign(payload: str) -> str:
    return hmac.new(settings.admin_session_secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def create_session_token() -> tuple[str, datetime]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=settings.admin_session_ttl_hours)
    payload = str(int(expires_at.timestamp()))
    return f"{payload}.{_sign(payload)}", expires_at


def verify_session_token(token: str | None) -> bool:
    if not token or not settings.admin_session_secret:
        return False
    payload, _, sig = token.partition(".")
    if not payload or not sig:
        return False
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    try:
        expires_at = int(payload)
    except ValueError:
        return False
    return time.time() < expires_at


def set_admin_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=ADMIN_COOKIE_NAME,
        value=token,
        max_age=settings.admin_session_ttl_hours * 3600,
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite=settings.admin_cookie_samesite,
        path="/",
    )


def clear_admin_cookie(response: Response) -> None:
    response.delete_cookie(
        key=ADMIN_COOKIE_NAME,
        path="/",
        samesite=settings.admin_cookie_samesite,
        secure=settings.admin_cookie_secure,
    )


# ── 로그인 brute-force 대응 (in-memory sliding window) ──────────────────────
# MVP 규모에 맞춘 best-effort 구현 — Redis 등 외부 인프라를 추가하지 않는다. 여러 워커로
# 스케일아웃되면 워커별로 카운트가 나뉘어 완벽하게 차단되진 않지만, 단일 워커 기준으로는
# 충분한 저지 효과가 있다.
_attempts_lock = threading.Lock()
_failed_attempts: dict[str, list[float]] = {}


def is_rate_limited(key: str) -> bool:
    now = time.time()
    window = settings.admin_login_lockout_seconds
    with _attempts_lock:
        history = [t for t in _failed_attempts.get(key, []) if now - t < window]
        _failed_attempts[key] = history
        return len(history) >= settings.admin_login_max_attempts


def record_failed_attempt(key: str) -> None:
    with _attempts_lock:
        _failed_attempts.setdefault(key, []).append(time.time())


def reset_attempts(key: str) -> None:
    with _attempts_lock:
        _failed_attempts.pop(key, None)

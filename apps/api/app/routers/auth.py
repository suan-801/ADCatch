from fastapi import APIRouter, HTTPException, Request, Response, status

from app.schemas import AdminLoginRequest, AdminStatusOut
from app.services import admin_auth

router = APIRouter(prefix="/auth", tags=["auth"])


def _client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


@router.post("/admin", response_model=AdminStatusOut)
def login_admin(payload: AdminLoginRequest, request: Request, response: Response):
    key = _client_key(request)
    if admin_auth.is_rate_limited(key):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요.",
        )

    if not admin_auth.verify_password(payload.password):
        admin_auth.record_failed_attempt(key)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="비밀번호가 올바르지 않습니다.")

    admin_auth.reset_attempts(key)
    token, _ = admin_auth.create_session_token()
    admin_auth.set_admin_cookie(response, token)
    return AdminStatusOut(is_admin=True)


@router.get("/status", response_model=AdminStatusOut)
def auth_status(request: Request):
    token = request.cookies.get(admin_auth.ADMIN_COOKIE_NAME)
    return AdminStatusOut(is_admin=admin_auth.verify_session_token(token))


@router.post("/logout", response_model=AdminStatusOut)
def logout_admin(response: Response):
    admin_auth.clear_admin_cookie(response)
    return AdminStatusOut(is_admin=False)

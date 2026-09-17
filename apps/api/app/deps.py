"""공용 FastAPI 의존성.

MVP는 로그인을 생략하고 DB의 default_admin 계정을 고정 사용한다 (PRD 3.2).
요청이 들어올 때마다 last_accessed_at을 갱신해 14일 자동 정지 정책의 기준으로 삼는다.
"""

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.services.autopause import touch_last_accessed


def get_current_user(db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.email == settings.default_admin_email))
    if user is None:
        user = User(email=settings.default_admin_email)
        db.add(user)
        db.commit()
        db.refresh(user)

    touch_last_accessed(db, user.id)
    return user

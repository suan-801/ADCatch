"""14일 미접속 자동 정지 정책 (PRD 3.2).

- 사용자가 웹사이트에 접속/조작할 때마다 users.last_accessed_at 갱신 (touch_last_accessed).
- 매일 새벽 수집 실행 시 프로젝트별로 마지막 접속 후 14일 초과 여부를 검사해
  PAUSED/ACTIVE 상태를 갱신하고, PAUSED 프로젝트는 그날 수집을 스킵한다 (should_collect_project).
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Project, User


def touch_last_accessed(db: Session, user_id) -> None:
    user = db.get(User, user_id)
    if user is None:
        return
    user.last_accessed_at = datetime.now(timezone.utc)

    # 접속 즉시 해당 유저의 PAUSED 프로젝트를 ACTIVE로 복구 (PRD 3.2)
    projects = db.scalars(select(Project).where(Project.user_id == user_id, Project.status == "PAUSED")).all()
    for project in projects:
        project.status = "ACTIVE"

    db.commit()


def should_collect_project(project: Project, user: User) -> bool:
    if not project.auto_collect_enabled:
        return False
    threshold = timedelta(days=settings.auto_pause_days)
    return datetime.now(timezone.utc) - user.last_accessed_at.replace(tzinfo=timezone.utc) <= threshold


def apply_auto_pause(db: Session) -> list[Project]:
    """매일 수집 스케줄러 시작 시 호출 — 14일 미접속 프로젝트를 PAUSED로 전환하고,
    이번 회차에 수집을 건너뛸 프로젝트 목록을 반환한다."""
    skipped: list[Project] = []
    projects = db.scalars(select(Project)).all()
    for project in projects:
        user = db.get(User, project.user_id)
        if user is None:
            continue
        if should_collect_project(project, user):
            project.status = "ACTIVE"
        else:
            project.status = "PAUSED"
            skipped.append(project)
    db.commit()
    return skipped

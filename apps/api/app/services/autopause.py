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


def _needs_touch(last_accessed_at: datetime, now: datetime, threshold_seconds: int) -> bool:
    # SQLite(테스트)는 DateTime(timezone=True) 컬럼도 naive datetime으로 돌려주므로 항상 UTC로 보정.
    last = last_accessed_at if last_accessed_at.tzinfo is not None else last_accessed_at.replace(tzinfo=timezone.utc)
    return (now - last).total_seconds() >= threshold_seconds


def touch_last_accessed(db: Session, user: User) -> None:
    """§13-3 성능 최적화 — 이전에는 이 함수가 요청마다(사실상 거의 모든 API 호출마다) DB
    write(SELECT+UPDATE+COMMIT)를 실행했다. last_accessed_touch_throttle_seconds 이내에 이미
    갱신됐다면 아무 것도 하지 않고 즉시 반환한다.

    14일 자동 정지 판정(should_collect_project)은 일 단위 스케줄러에서만 평가되므로, 이 정도의
    지연은 정책 의미에 영향이 없다 — PAUSED→ACTIVE 복구도 동일한 throttle 창 안에서 이뤄지는
    것으로 허용한다. get_current_user()가 이미 조회해둔 User 객체를 그대로 받아 재조회를 피한다."""
    now = datetime.now(timezone.utc)
    if user.last_accessed_at is not None and not _needs_touch(
        user.last_accessed_at, now, settings.last_accessed_touch_throttle_seconds
    ):
        return

    user.last_accessed_at = now

    # 접속 즉시 해당 유저의 PAUSED 프로젝트를 ACTIVE로 복구 (PRD 3.2)
    projects = db.scalars(select(Project).where(Project.user_id == user.id, Project.status == "PAUSED")).all()
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

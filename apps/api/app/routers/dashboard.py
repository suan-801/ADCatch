import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Ad, Competitor, Project, User
from app.schemas import AdStatus, CollectionFreshness, DashboardMetrics
from app.services.collection_history import get_freshness_summary

router = APIRouter(prefix="/projects/{project_id}/dashboard", tags=["dashboard"])


@router.get("", response_model=DashboardMetrics)
def get_dashboard(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PRD 4장 'Fact Metrics' — 신규/종료/유지 카운트 + 비주얼 포맷 비율.
    P0-18/P0-19: Project 안의 모든 등록 브랜드를 동일하게 집계한다(자사/경쟁사 구분 없음).

    §13-4 성능 최적화: 전체 Ad row를 Python으로 가져와 Counter로 세지 않고 SQL GROUP BY로
    집계한다(응답 값의 의미는 기존 구현과 동일)."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    base_filter = (Competitor.project_id == project_id, Ad.is_archived.is_(False))

    status_counts = dict(
        db.execute(
            select(Ad.status, func.count())
            .join(Competitor, Ad.competitor_id == Competitor.id)
            .where(*base_filter)
            .group_by(Ad.status)
        ).all()
    )
    visual_counts = dict(
        db.execute(
            select(Ad.visual_type, func.count())
            .join(Competitor, Ad.competitor_id == Competitor.id)
            .where(*base_filter, Ad.visual_type.is_not(None))
            .group_by(Ad.visual_type)
        ).all()
    )

    return DashboardMetrics(
        project_id=project_id,
        new_count=status_counts.get(AdStatus.NEW.value, 0),
        active_count=status_counts.get(AdStatus.ACTIVE.value, 0),
        inactive_count=status_counts.get(AdStatus.INACTIVE.value, 0),
        visual_type_ratio=visual_counts,
    )


@router.get("/freshness", response_model=CollectionFreshness)
def get_dashboard_freshness(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """P0-09 — '이 데이터를 믿어도 되는가' 요약 (최신 수집 시각, N/N 경쟁사 정상)."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    return get_freshness_summary(db, project_id)

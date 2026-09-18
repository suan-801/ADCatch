import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
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
    자사(is_own_brand=True) 소재는 경쟁사 집계에서 제외한다 (PRD 3.1)."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    ads = db.scalars(
        select(Ad)
        .join(Competitor, Ad.competitor_id == Competitor.id)
        .where(
            Competitor.project_id == project_id,
            Competitor.is_own_brand.is_(False),
            Ad.is_archived.is_(False),
        )
    ).all()

    status_counts = Counter(ad.status for ad in ads)
    visual_counts = Counter(ad.visual_type for ad in ads if ad.visual_type)

    return DashboardMetrics(
        project_id=project_id,
        new_count=status_counts.get(AdStatus.NEW.value, 0),
        active_count=status_counts.get(AdStatus.ACTIVE.value, 0),
        inactive_count=status_counts.get(AdStatus.INACTIVE.value, 0),
        visual_type_ratio=dict(visual_counts),
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

import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Competitor, Project, User
from app.schemas import AdChangesResponse
from app.services.collection_history import get_ad_changes

router = APIRouter(prefix="/projects/{project_id}/ad-changes", tags=["ad-changes"])


@router.get("", response_model=AdChangesResponse)
def get_project_ad_changes(
    project_id: uuid.UUID,
    date: date_type = Query(..., description="조회할 날짜 (YYYY-MM-DD, KST 기준)"),
    competitor_id: uuid.UUID | None = Query(None, description="생략 시 프로젝트 전체(자사 제외) 기준"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PART A — 날짜 × 광고주 기준 광고 변화 이력 (켠 광고 / 끈 광고 / 다시 켠 광고 / 비주얼 패턴)."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if competitor_id is not None:
        competitor = db.get(Competitor, competitor_id)
        if competitor is None or competitor.project_id != project_id:
            raise HTTPException(status_code=404, detail="Competitor not found")

    return get_ad_changes(db, project_id, date, competitor_id)

import uuid
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models import Competitor, Project, User
from app.schemas import AdChangesRangeResponse, AdChangesResponse
from app.services.collection_history import get_ad_changes, get_ad_changes_range

router = APIRouter(prefix="/projects/{project_id}/ad-changes", tags=["ad-changes"])


def _validate_scope(db: Session, user: User, project_id: uuid.UUID, competitor_id: uuid.UUID | None) -> None:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    if competitor_id is not None:
        competitor = db.get(Competitor, competitor_id)
        if competitor is None or competitor.project_id != project_id:
            raise HTTPException(status_code=404, detail="Competitor not found")


@router.get("", response_model=AdChangesResponse)
def get_project_ad_changes(
    project_id: uuid.UUID,
    date: date_type = Query(..., description="조회할 날짜 (YYYY-MM-DD, KST 기준)"),
    competitor_id: uuid.UUID | None = Query(None, description="생략 시 프로젝트 전체(자사 제외) 기준"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """PART A — 날짜 × 광고주 기준 광고 변화 이력 (켠 광고 / 끈 광고 / 다시 켠 광고 / 비주얼 패턴).

    기간(주간) 조회가 필요하면 GET .../ad-changes/range를 사용한다 — 이 엔드포인트의 계약은
    그대로 유지된다(기존 프론트 호출을 깨지 않기 위함)."""
    _validate_scope(db, user, project_id, competitor_id)
    return get_ad_changes(db, project_id, date, competitor_id)


@router.get("/range", response_model=AdChangesRangeResponse)
def get_project_ad_changes_range(
    project_id: uuid.UUID,
    start_date: date_type = Query(..., description="조회 시작일 (YYYY-MM-DD, KST 기준, inclusive)"),
    end_date: date_type = Query(..., description="조회 종료일 (YYYY-MM-DD, KST 기준, inclusive)"),
    competitor_id: uuid.UUID | None = Query(None, description="생략 시 프로젝트 전체 기준"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """§6 — 기간(주간) 조회. 광고주 보고용 주간 단위 조회를 지원한다(월요일~일요일 기본은 프론트가
    구성). 동일 광고가 기간 내 여러 이벤트를 가지면 각각 개별 항목으로 보존한다."""
    if start_date > end_date:
        raise HTTPException(status_code=400, detail="start_date must not be after end_date")
    _validate_scope(db, user, project_id, competitor_id)
    return get_ad_changes_range(db, project_id, start_date, end_date, competitor_id)

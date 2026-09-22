import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Ad, Competitor, Project, User
from app.schemas import VisualAnalysisProcessPendingRequest, VisualAnalysisProcessPendingResult
from app.services.pending_analysis import process_pending_analysis

router = APIRouter(prefix="/projects/{project_id}/visual-analysis", tags=["visual-analysis"])


def _get_owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/process-pending", response_model=VisualAnalysisProcessPendingResult)
def process_pending_visual_analysis(
    project_id: uuid.UUID,
    payload: VisualAnalysisProcessPendingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """§9/§10 — 대시보드 비주얼 패턴 카드의 "분석 업데이트" 버튼. 기존
    process_pending_analysis()(Gemini Vision, visual_type)를 그대로 재사용하되 project_id로
    스코프를 좁히고, 한 요청에서 처리할 소재 수를 bounded batch(기본/상한
    settings.visual_analysis_manual_batch_size)로 제한한다. 프론트가 pending_remaining>0인 동안
    짧은 delay를 두고 반복 호출해 "자동 연속 처리"를 구현한다 — 이 endpoint 자체는 항상 한 배치만
    처리하고 즉시 반환한다(서버가 루프를 소유하지 않는다)."""
    _get_owned_project(db, project_id, user)

    limit = payload.limit or settings.visual_analysis_manual_batch_size
    limit = min(limit, settings.visual_analysis_manual_batch_size)

    summary = process_pending_analysis(db, project_id=project_id, limit=limit)

    pending_remaining = db.scalar(
        select(func.count())
        .select_from(Ad)
        .where(
            Ad.competitor_id.in_(select(Competitor.id).where(Competitor.project_id == project_id)),
            Ad.analysis_status == "PENDING",
        )
    ) or 0

    return VisualAnalysisProcessPendingResult(
        processed=summary.processed,
        succeeded=summary.succeeded,
        still_pending=summary.still_pending,
        failed=summary.failed,
        quota_stopped=summary.quota_stopped,
        pending_remaining=pending_remaining,
    )

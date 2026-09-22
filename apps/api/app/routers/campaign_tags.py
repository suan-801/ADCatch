import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Ad, CampaignTag, Competitor, Project, User
from app.schemas import (
    CampaignTagClassificationStatusOut,
    CampaignTagCreate,
    CampaignTagOut,
    CampaignTagProcessPendingRequest,
    CampaignTagProcessPendingResult,
    CampaignTagReclassifyRequest,
    CampaignTagReclassifyResult,
    CampaignTagUpdate,
)
from app.services import campaign_tags as campaign_tags_service
from app.services.pending_campaign_classification import process_pending_campaign_classification

router = APIRouter(prefix="/projects/{project_id}/campaign-tags", tags=["campaign-tags"])
# PATCH/DELETE는 project_id 없이 tag_id만으로 식별된다 — app/routers/ads.py의 ad_detail_router와
# 동일한 패턴(리소스 자신의 id로 직접 접근, 소유권은 project_id를 역참조해 검증).
tag_detail_router = APIRouter(prefix="/campaign-tags", tags=["campaign-tags"])


def _get_owned_project(db: Session, project_id: uuid.UUID, user: User) -> Project:
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_owned_tag_project_id(db: Session, tag_id: uuid.UUID, user: User) -> uuid.UUID:
    """tag_id로부터 project_id를 역참조해 소유권을 검증한다. 다른 프로젝트/다른 사용자의 태그에
    접근하지 못하도록 항상 이 경로를 거친다."""
    tag = db.get(CampaignTag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="Campaign tag not found")
    project = db.get(Project, tag.project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Campaign tag not found")
    return tag.project_id


@router.get("", response_model=list[CampaignTagOut])
def list_campaign_tags(
    project_id: uuid.UUID,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_owned_project(db, project_id, user)
    return campaign_tags_service.list_campaign_tags(db, project_id, include_inactive=include_inactive)


@router.post("", response_model=CampaignTagOut)
def create_campaign_tag(
    project_id: uuid.UUID,
    payload: CampaignTagCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    _get_owned_project(db, project_id, user)
    try:
        return campaign_tags_service.create_campaign_tag(db, project_id, payload.name, payload.definition)
    except campaign_tags_service.DuplicateCampaignTagNameError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


def _not_user_assigned_condition():
    # SQL의 NULL 비교 규칙 주의: assignment_source != "USER"만 쓰면 NULL인 행(아직 아무도
    # 지정하지 않은 소재)이 조건에서 통째로 빠진다(NULL != 'USER'는 NULL이지 TRUE가 아니다) —
    # NULL은 명백히 "USER 아님"이므로 명시적으로 포함시킨다.
    return or_(Ad.campaign_tag_assignment_source.is_(None), Ad.campaign_tag_assignment_source != "USER")


@router.post("/reclassify", response_model=CampaignTagReclassifyResult)
def reclassify_campaign_tags(
    project_id: uuid.UUID,
    payload: CampaignTagReclassifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """§5 — "기존 광고 반영". 대상 ads를 완전히 리셋해 campaign_classification_status=PENDING으로
    되돌린다 — 실제 재분류는 이 요청 안에서 즉시 실행하지 않고(대량 Gemini 호출이 core collection을
    막으면 안 됨) 이후 pending 배치(Daily Scheduler 또는 §2-3 "지금 재분류 실행")가 처리한다.

    include_user_assigned=false(기본)면 USER가 직접 지정한 소재는 쿼리에서부터 제외되어 전혀
    건드리지 않는다.

    reset_count만으로는 "기존 광고 반영" 상태를 온전히 표현하지 못한다 — 태그가 없던 시절 생성된
    소재는 이미 campaign_classification_status=PENDING이라 reset 대상이 아니지만, 활성 태그가
    생긴 지금은 여전히 분류 대기 중인 "기존 광고 반영" 대상이다. 그래서 already_pending_count를
    함께 반환한다(§2-1)."""
    _get_owned_project(db, project_id, user)

    competitor_ids_subq = select(Competitor.id).where(Competitor.project_id == project_id)
    user_scope = [] if payload.include_user_assigned else [_not_user_assigned_condition()]

    # reset 대상(SUCCESS/NEEDS_REVIEW/FAILED)과 already-pending 집합은 상태값 기준으로 서로
    # 배타적이므로, reset으로 인한 상태 변경이 already_pending_count 집계에 영향을 주지 않는다 —
    # 그래도 명확성을 위해 already_pending_count를 먼저 조회한 뒤 reset을 수행한다.
    already_pending_count = db.scalar(
        select(func.count())
        .select_from(Ad)
        .where(
            Ad.competitor_id.in_(competitor_ids_subq),
            Ad.campaign_classification_status == "PENDING",
            *user_scope,
        )
    ) or 0

    target_ads = db.scalars(
        select(Ad).where(
            Ad.competitor_id.in_(competitor_ids_subq),
            Ad.campaign_classification_status.in_(["SUCCESS", "NEEDS_REVIEW", "FAILED"]),
            *user_scope,
        )
    ).all()
    for ad in target_ads:
        ad.campaign_tag_id = None
        ad.campaign_tag_assignment_source = None
        ad.campaign_classification_status = "PENDING"
        ad.campaign_tag_confidence = None
        ad.campaign_tag_reason = None
        ad.campaign_classification_retry_count = 0
        ad.campaign_classification_error = None
    reset_count = len(target_ads)
    db.commit()

    return CampaignTagReclassifyResult(
        reset_count=reset_count,
        already_pending_count=already_pending_count,
        total_target_count=reset_count + already_pending_count,
    )


@router.get("/reclassification-status", response_model=CampaignTagClassificationStatusOut)
def get_campaign_tag_classification_status(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """§2-2 — "현재 프로젝트 소재 분류 상태" 스냅샷(이번 재분류의 진행률이 아니다 — 별도 job
    테이블 없이는 "이번 실행 batch"만 정확히 추적할 수 없으므로, 프로젝트 전체 소재의 현재 상태를
    그대로 집계해 보여준다). 프론트는 이 값을 CampaignTagReclassifyResult의 total_target_count와
    혼동되지 않게 별도 레이블("현재 분류 상태")로 표시해야 한다."""
    _get_owned_project(db, project_id, user)

    rows = db.execute(
        select(Ad.campaign_classification_status, func.count())
        .join(Competitor, Ad.competitor_id == Competitor.id)
        .where(Competitor.project_id == project_id)
        .group_by(Ad.campaign_classification_status)
    ).all()
    counts = dict(rows)
    return CampaignTagClassificationStatusOut(
        pending=counts.get("PENDING", 0),
        success=counts.get("SUCCESS", 0),
        needs_review=counts.get("NEEDS_REVIEW", 0),
        failed=counts.get("FAILED", 0),
    )


@router.post("/process-pending", response_model=CampaignTagProcessPendingResult)
def process_pending_campaign_tags(
    project_id: uuid.UUID,
    payload: CampaignTagProcessPendingRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """§2-3 — "지금 재분류 실행". 한 요청에서 프로젝트 전체 PENDING 소재를 다 처리하지 않고,
    bounded batch(기본/상한 settings.campaign_classification_manual_batch_size)만 동기 처리한다.
    project_id로 스코프해 다른 프로젝트의 PENDING 광고는 절대 함께 처리하지 않는다. 남은 PENDING은
    사용자가 페이지를 떠나도 Daily Scheduler가 계속 처리한다(브라우저가 큐를 소유하지 않는다)."""
    _get_owned_project(db, project_id, user)

    limit = payload.limit or settings.campaign_classification_manual_batch_size
    limit = min(limit, settings.campaign_classification_manual_batch_size)

    summary = process_pending_campaign_classification(db, project_id=project_id, limit=limit)

    pending_remaining = db.scalar(
        select(func.count())
        .select_from(Ad)
        .where(
            Ad.competitor_id.in_(select(Competitor.id).where(Competitor.project_id == project_id)),
            Ad.campaign_classification_status == "PENDING",
        )
    ) or 0

    return CampaignTagProcessPendingResult(
        processed=summary.processed,
        succeeded=summary.succeeded,
        needs_review=summary.needs_review,
        still_pending=summary.still_pending,
        failed=summary.failed,
        quota_stopped=summary.quota_stopped,
        pending_remaining=pending_remaining,
    )


@tag_detail_router.patch("/{tag_id}", response_model=CampaignTagOut)
def update_campaign_tag(
    tag_id: uuid.UUID,
    payload: CampaignTagUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    project_id = _get_owned_tag_project_id(db, tag_id, user)
    try:
        return campaign_tags_service.update_campaign_tag(
            db, project_id, tag_id, name=payload.name, definition=payload.definition
        )
    except campaign_tags_service.DuplicateCampaignTagNameError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except campaign_tags_service.CampaignTagNotFoundError as e:
        raise HTTPException(status_code=404, detail="Campaign tag not found") from e


@tag_detail_router.delete("/{tag_id}", response_model=CampaignTagOut)
def delete_campaign_tag(
    tag_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """삭제는 soft delete(is_active=False)다 — 과거 소재의 태그 표시/이력을 보존한다."""
    project_id = _get_owned_tag_project_id(db, tag_id, user)
    try:
        return campaign_tags_service.deactivate_campaign_tag(db, project_id, tag_id)
    except campaign_tags_service.CampaignTagNotFoundError as e:
        raise HTTPException(status_code=404, detail="Campaign tag not found") from e

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Ad, CampaignTag, Competitor, Project, User
from app.schemas import (
    CampaignTagCreate,
    CampaignTagOut,
    CampaignTagReclassifyRequest,
    CampaignTagReclassifyResult,
    CampaignTagUpdate,
)
from app.services import campaign_tags as campaign_tags_service

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


@router.post("/reclassify", response_model=CampaignTagReclassifyResult)
def reclassify_campaign_tags(
    project_id: uuid.UUID,
    payload: CampaignTagReclassifyRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """§5 — 재분류. 대상 ads를 완전히 리셋해 campaign_classification_status=PENDING으로 되돌린다 —
    실제 재분류는 이 요청 안에서 즉시 실행하지 않고(대량 Gemini 호출이 core collection을 막으면
    안 됨) 이후 pending 배치(process_pending_campaign_classification)가 처리한다.

    include_user_assigned=false(기본)면 USER가 직접 지정한 소재는 쿼리에서부터 제외되어 전혀
    건드리지 않는다."""
    _get_owned_project(db, project_id, user)

    eligible_statuses = ["SUCCESS", "NEEDS_REVIEW", "FAILED"]
    conditions = [
        Ad.competitor_id.in_(select(Competitor.id).where(Competitor.project_id == project_id)),
        Ad.campaign_classification_status.in_(eligible_statuses),
    ]
    if not payload.include_user_assigned:
        # SQL의 NULL 비교 규칙 주의: assignment_source != "USER"만 쓰면 NULL인 행(아직 아무도
        # 지정하지 않은 FAILED/NEEDS_REVIEW 소재)이 조건에서 통째로 빠진다(NULL != 'USER'는
        # NULL이지 TRUE가 아니다) — NULL은 명백히 "USER 아님"이므로 명시적으로 포함시킨다.
        conditions.append(
            or_(Ad.campaign_tag_assignment_source.is_(None), Ad.campaign_tag_assignment_source != "USER")
        )

    target_ads = db.scalars(select(Ad).where(and_(*conditions))).all()
    for ad in target_ads:
        ad.campaign_tag_id = None
        ad.campaign_tag_assignment_source = None
        ad.campaign_classification_status = "PENDING"
        ad.campaign_tag_confidence = None
        ad.campaign_tag_reason = None
        ad.campaign_classification_retry_count = 0
        ad.campaign_classification_error = None
    db.commit()

    return CampaignTagReclassifyResult(reset_count=len(target_ads))


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

"""프로젝트별 Campaign Tag CRUD + 검증 규칙.

시스템에 고정된 캠페인 카테고리를 두지 않는다 — 프로젝트마다 사용자가 태그명+정의를 직접
관리한다. 이름 중복 방지/soft delete/project 격리 등 라우터가 공유해야 하는 규칙을 여기 모아둔다
(app/routers/campaign_tags.py, app/services/campaign_tagging.py, app/services/ad_sync.py가 재사용).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import CampaignTag


class CampaignTagNotFoundError(Exception):
    pass


class DuplicateCampaignTagNameError(Exception):
    pass


def _normalize(name: str) -> str:
    return name.strip()


def list_campaign_tags(db: Session, project_id: uuid.UUID, *, include_inactive: bool = False) -> list[CampaignTag]:
    query = select(CampaignTag).where(CampaignTag.project_id == project_id)
    if not include_inactive:
        query = query.where(CampaignTag.is_active.is_(True))
    return list(db.scalars(query.order_by(CampaignTag.created_at.asc())).all())


def list_active_campaign_tags(db: Session, project_id: uuid.UUID) -> list[CampaignTag]:
    return list_campaign_tags(db, project_id, include_inactive=False)


def get_owned_campaign_tag(db: Session, project_id: uuid.UUID, tag_id: uuid.UUID) -> CampaignTag:
    tag = db.get(CampaignTag, tag_id)
    if tag is None or tag.project_id != project_id:
        raise CampaignTagNotFoundError(f"CampaignTag {tag_id} not found in project {project_id}")
    return tag


def _assert_name_available(
    db: Session, project_id: uuid.UUID, name: str, *, exclude_tag_id: uuid.UUID | None = None
) -> None:
    """같은 프로젝트 내 활성 태그 중 대소문자 무시 동일 이름이 있으면 거부한다.
    DB partial unique index(idx_campaign_tags_project_name_active)는 동시 요청 경합에 대비한
    보조 안전망이고, 사용자에게 보이는 에러 메시지는 항상 이 검증에서 나온다."""
    query = select(CampaignTag).where(
        CampaignTag.project_id == project_id,
        CampaignTag.is_active.is_(True),
        func.lower(CampaignTag.name) == name.lower(),
    )
    if exclude_tag_id is not None:
        query = query.where(CampaignTag.id != exclude_tag_id)
    if db.scalar(query) is not None:
        raise DuplicateCampaignTagNameError(f"이미 사용 중인 태그 이름입니다: {name}")


def create_campaign_tag(db: Session, project_id: uuid.UUID, name: str, definition: str) -> CampaignTag:
    name = _normalize(name)
    definition = definition.strip()
    _assert_name_available(db, project_id, name)
    tag = CampaignTag(project_id=project_id, name=name, definition=definition, is_active=True)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


def update_campaign_tag(
    db: Session, project_id: uuid.UUID, tag_id: uuid.UUID, *, name: str | None, definition: str | None
) -> CampaignTag:
    tag = get_owned_campaign_tag(db, project_id, tag_id)
    if name is not None:
        name = _normalize(name)
        _assert_name_available(db, project_id, name, exclude_tag_id=tag_id)
        tag.name = name
    if definition is not None:
        tag.definition = definition.strip()
    tag.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tag)
    return tag


def deactivate_campaign_tag(db: Session, project_id: uuid.UUID, tag_id: uuid.UUID) -> CampaignTag:
    """삭제는 soft delete다 — 과거 소재에 이미 붙은 태그 표시/이력을 보존한다."""
    tag = get_owned_campaign_tag(db, project_id, tag_id)
    tag.is_active = False
    tag.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(tag)
    return tag

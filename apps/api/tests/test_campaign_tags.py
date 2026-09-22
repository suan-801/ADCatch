"""Campaign Tag CRUD — 프로젝트별 격리, 이름 중복 방지, soft delete, Admin 게이팅."""

import uuid

import pytest
from fastapi import HTTPException

from app.models import Project, User
from app.routers.campaign_tags import (
    create_campaign_tag as router_create_campaign_tag,
    delete_campaign_tag as router_delete_campaign_tag,
    list_campaign_tags as router_list_campaign_tags,
    update_campaign_tag as router_update_campaign_tag,
)
from app.schemas import CampaignTagCreate, CampaignTagUpdate
from app.services import campaign_tags as service


def _make_project(db, name="P") -> Project:
    user = User(id=uuid.uuid4(), email=f"{name}@adcather.local")
    db.add(user)
    db.flush()
    project = Project(id=uuid.uuid4(), user_id=user.id, name=name)
    db.add(project)
    db.commit()
    return project


def test_create_and_list_tags_scoped_to_project(db):
    p1 = _make_project(db, "p1")
    p2 = _make_project(db, "p2")

    service.create_campaign_tag(db, p1.id, "굿즈", "상품 구매를 유도하는 광고")
    service.create_campaign_tag(db, p2.id, "굿즈", "다른 프로젝트의 동명 태그 — 충돌 없어야 함")

    tags_p1 = service.list_campaign_tags(db, p1.id)
    tags_p2 = service.list_campaign_tags(db, p2.id)
    assert len(tags_p1) == 1
    assert len(tags_p2) == 1
    assert tags_p1[0].id != tags_p2[0].id


def test_duplicate_active_name_rejected_case_insensitive(db):
    p = _make_project(db)
    service.create_campaign_tag(db, p.id, "굿즈", "정의1")
    with pytest.raises(service.DuplicateCampaignTagNameError):
        service.create_campaign_tag(db, p.id, " 굿즈 ", "정의2 — trim/공백만 다름")


def test_update_tag_name_and_definition(db):
    p = _make_project(db)
    tag = service.create_campaign_tag(db, p.id, "굿즈", "정의1")
    updated = service.update_campaign_tag(db, p.id, tag.id, name="팔찌 굿즈", definition="팔찌류만")
    assert updated.name == "팔찌 굿즈"
    assert updated.definition == "팔찌류만"


def test_update_to_duplicate_name_rejected(db):
    p = _make_project(db)
    service.create_campaign_tag(db, p.id, "굿즈", "정의1")
    tag2 = service.create_campaign_tag(db, p.id, "정기후원", "정의2")
    with pytest.raises(service.DuplicateCampaignTagNameError):
        service.update_campaign_tag(db, p.id, tag2.id, name="굿즈", definition=None)


def test_deactivate_is_soft_delete(db):
    p = _make_project(db)
    tag = service.create_campaign_tag(db, p.id, "굿즈", "정의1")
    service.deactivate_campaign_tag(db, p.id, tag.id)

    active_only = service.list_campaign_tags(db, p.id, include_inactive=False)
    all_tags = service.list_campaign_tags(db, p.id, include_inactive=True)
    assert active_only == []
    assert len(all_tags) == 1
    assert all_tags[0].is_active is False


def test_deactivated_tag_name_becomes_reusable(db):
    """비활성 태그는 이름 중복 검사에서 제외된다 — 같은 이름으로 새로 만들 수 있어야 한다."""
    p = _make_project(db)
    tag = service.create_campaign_tag(db, p.id, "굿즈", "정의1")
    service.deactivate_campaign_tag(db, p.id, tag.id)
    recreated = service.create_campaign_tag(db, p.id, "굿즈", "새 정의")
    assert recreated.id != tag.id
    assert recreated.is_active is True


def test_get_owned_campaign_tag_rejects_other_project(db):
    p1 = _make_project(db, "p1")
    p2 = _make_project(db, "p2")
    tag = service.create_campaign_tag(db, p1.id, "굿즈", "정의")
    with pytest.raises(service.CampaignTagNotFoundError):
        service.get_owned_campaign_tag(db, p2.id, tag.id)


# ── 라우터 레벨: project_id 소유권/역참조 검증 ──────────────────────────────


def test_router_list_requires_project_ownership(db):
    owner = User(id=uuid.uuid4(), email="owner@adcather.local")
    intruder = User(id=uuid.uuid4(), email="intruder@adcather.local")
    db.add_all([owner, intruder])
    db.flush()
    project = Project(id=uuid.uuid4(), user_id=owner.id, name="P")
    db.add(project)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        router_list_campaign_tags(project.id, False, db=db, user=intruder)
    assert exc_info.value.status_code == 404


def test_router_create_and_update_and_delete_roundtrip(db):
    p = _make_project(db)
    user = db.get(User, p.user_id)

    created = router_create_campaign_tag(p.id, CampaignTagCreate(name="굿즈", definition="정의"), db=db, user=user)
    assert created.name == "굿즈"

    updated = router_update_campaign_tag(
        created.id, CampaignTagUpdate(name="팔찌 굿즈", definition=None), db=db, user=user
    )
    assert updated.name == "팔찌 굿즈"
    assert updated.definition == "정의"

    deleted = router_delete_campaign_tag(created.id, db=db, user=user)
    assert deleted.is_active is False

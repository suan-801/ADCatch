"""PATCH /ads/{id}/campaign-tag — 사용자 수동 지정. AI 값보다 항상 우선하고, confidence/reason을
항상 클리어하며(사용자 리뷰 #1), 다른 프로젝트/비활성 태그 지정은 서버에서 거부한다(사용자 리뷰 #3)."""

import uuid

import pytest
from fastapi import HTTPException

from app.models import Ad, Competitor, Project, User
from app.routers.ads import update_ad_campaign_tag
from app.schemas import AdCampaignTagUpdate
from app.services.campaign_tags import create_campaign_tag, deactivate_campaign_tag


def _make_ad(db, competitor, **kwargs) -> Ad:
    ad = Ad(competitor_id=competitor.id, ad_archive_id="A1", image_url="https://cdn/a1.jpg", format="IMAGE", **kwargs)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def test_manual_assignment_overrides_ai_and_clears_confidence_reason(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    other_tag = create_campaign_tag(db, competitor.project_id, "정기후원", "정의2")
    ad = _make_ad(
        db, competitor,
        campaign_tag_id=tag.id, campaign_tag_assignment_source="AI",
        campaign_tag_confidence=0.75, campaign_tag_reason="AI 판단 근거",
        campaign_classification_status="SUCCESS",
    )
    user = db.get(User, competitor.project.user_id)

    updated = update_ad_campaign_tag(ad.id, AdCampaignTagUpdate(campaign_tag_id=other_tag.id), db=db, user=user)

    assert str(updated.campaign_tag_id) == str(other_tag.id)
    assert updated.campaign_tag_assignment_source == "USER"
    assert updated.campaign_classification_status == "SUCCESS"
    # "사용자 지정 / AI 신뢰도 87%" 같은 모순 UI 방지 — 항상 NULL로 클리어.
    assert updated.campaign_tag_confidence is None
    assert updated.campaign_tag_reason is None


def test_rejects_tag_from_another_project(db, competitor):
    """FK만으로는 다른 프로젝트 태그 지정을 막지 못한다 — 서버가 project_id를 직접 재검증해야 한다."""
    other_project = Project(id=uuid.uuid4(), user_id=competitor.project.user_id, name="다른 프로젝트")
    db.add(other_project)
    db.commit()
    other_tag = create_campaign_tag(db, other_project.id, "다른태그", "정의")
    ad = _make_ad(db, competitor)
    user = db.get(User, competitor.project.user_id)

    with pytest.raises(HTTPException) as exc_info:
        update_ad_campaign_tag(ad.id, AdCampaignTagUpdate(campaign_tag_id=other_tag.id), db=db, user=user)
    assert exc_info.value.status_code == 400


def test_rejects_inactive_tag(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    deactivate_campaign_tag(db, competitor.project_id, tag.id)
    ad = _make_ad(db, competitor)
    user = db.get(User, competitor.project.user_id)

    with pytest.raises(HTTPException) as exc_info:
        update_ad_campaign_tag(ad.id, AdCampaignTagUpdate(campaign_tag_id=tag.id), db=db, user=user)
    assert exc_info.value.status_code == 400


def test_rejects_ad_not_owned_by_user(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    ad = _make_ad(db, competitor)
    intruder = User(id=uuid.uuid4(), email="intruder@adcather.local")
    db.add(intruder)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        update_ad_campaign_tag(ad.id, AdCampaignTagUpdate(campaign_tag_id=tag.id), db=db, user=intruder)
    assert exc_info.value.status_code == 404

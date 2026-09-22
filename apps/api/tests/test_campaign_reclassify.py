"""§5 재분류 API — include_user_assigned 기본값(false)에서 USER 소재는 절대 건드리지 않고,
true일 때만 명시적으로 리셋되어 실제로 pending 배치의 대상이 되는지(v1 계획의 버그 수정) 검증."""

import uuid

from app.models import Ad, User
from app.routers.campaign_tags import reclassify_campaign_tags
from app.schemas import CampaignTagReclassifyRequest
from app.services.campaign_tags import create_campaign_tag
from app.services.pending_campaign_classification import process_pending_campaign_classification


def _make_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(competitor_id=competitor.id, ad_archive_id=archive_id, image_url=f"https://cdn/{archive_id}.jpg", format="IMAGE", **kwargs)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def test_default_excludes_user_assigned(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    user_ad = _make_ad(
        db, competitor, "U1",
        campaign_classification_status="SUCCESS", campaign_tag_assignment_source="USER", campaign_tag_id=tag.id,
    )
    ai_ad = _make_ad(
        db, competitor, "A1",
        campaign_classification_status="SUCCESS", campaign_tag_assignment_source="AI", campaign_tag_id=tag.id,
        campaign_tag_confidence=0.9,
    )

    user = db.get(User, competitor.project.user_id)
    result = reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=False), db=db, user=user
    )

    db.refresh(user_ad)
    db.refresh(ai_ad)
    assert result.reset_count == 1
    assert user_ad.campaign_classification_status == "SUCCESS"  # 건드리지 않음
    assert user_ad.campaign_tag_id == tag.id
    assert ai_ad.campaign_classification_status == "PENDING"  # 리셋됨
    assert ai_ad.campaign_tag_id is None
    assert ai_ad.campaign_tag_confidence is None


def test_include_user_assigned_true_resets_and_pending_batch_then_reclassifies(db, competitor):
    """v1 계획의 버그: include_user_assigned=true로 리셋해도 pending 배치가 assignment_source로
    걸러내 실제로는 재분류되지 않는 문제가 있었다. 지금 구현은 배치가 status만 보므로, 리셋 →
    배치 실행까지 전체 흐름이 실제로 동작해야 한다."""
    from unittest.mock import patch

    tag_a = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    tag_b = create_campaign_tag(db, competitor.project_id, "정기후원", "정의2")
    user_ad = _make_ad(
        db, competitor, "U1",
        campaign_classification_status="SUCCESS", campaign_tag_assignment_source="USER", campaign_tag_id=tag_a.id,
        campaign_tag_confidence=None,
    )

    user = db.get(User, competitor.project.user_id)
    result = reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=True), db=db, user=user
    )
    db.refresh(user_ad)
    assert result.reset_count == 1
    assert user_ad.campaign_classification_status == "PENDING"
    assert user_ad.campaign_tag_id is None
    assert user_ad.campaign_tag_assignment_source is None

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag_b.id), 0.95, "새 기준으로 재분류"),
    ):
        summary = process_pending_campaign_classification(db)

    db.refresh(user_ad)
    assert summary.succeeded == 1
    assert str(user_ad.campaign_tag_id) == str(tag_b.id)
    assert user_ad.campaign_tag_assignment_source == "AI"


def test_needs_review_and_failed_are_eligible_by_default(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    needs_review_ad = _make_ad(db, competitor, "N1", campaign_classification_status="NEEDS_REVIEW")
    failed_ad = _make_ad(db, competitor, "F1", campaign_classification_status="FAILED", campaign_classification_retry_count=3)

    user = db.get(User, competitor.project.user_id)
    result = reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=False), db=db, user=user
    )

    db.refresh(needs_review_ad)
    db.refresh(failed_ad)
    assert result.reset_count == 2
    assert needs_review_ad.campaign_classification_status == "PENDING"
    assert failed_ad.campaign_classification_status == "PENDING"
    assert failed_ad.campaign_classification_retry_count == 0


def test_reclassify_does_not_touch_other_projects(db, competitor):
    from app.models import Competitor, Project

    other_project = Project(id=uuid.uuid4(), user_id=competitor.project.user_id, name="다른 프로젝트")
    db.add(other_project)
    db.flush()
    other_competitor = Competitor(
        id=uuid.uuid4(), project_id=other_project.id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=2", page_id="2",
    )
    db.add(other_competitor)
    db.commit()

    create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    other_tag = create_campaign_tag(db, other_project.id, "다른태그", "정의")
    other_ad = _make_ad(
        db, other_competitor, "O1",
        campaign_classification_status="SUCCESS", campaign_tag_assignment_source="AI", campaign_tag_id=other_tag.id,
    )

    user = db.get(User, competitor.project.user_id)
    reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=False), db=db, user=user
    )

    db.refresh(other_ad)
    assert other_ad.campaign_classification_status == "SUCCESS"  # 다른 프로젝트는 영향 없음

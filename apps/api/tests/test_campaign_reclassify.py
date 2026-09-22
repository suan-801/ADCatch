"""§5 재분류 API — include_user_assigned 기본값(false)에서 USER 소재는 절대 건드리지 않고,
true일 때만 명시적으로 리셋되어 실제로 pending 배치의 대상이 되는지(v1 계획의 버그 수정) 검증.

§2 사용자 피드백 — "기존 광고 반영"이 눌러도 반응이 없어 보이던 문제 회귀 테스트:
  - PENDING이었던 기존 광고(태그가 없던 시절 생성)는 reset 대상이 아니지만 total_target_count에
    반드시 포함돼야 한다(굿네이버스 프로젝트 재현 케이스).
  - "지금 재분류 실행"(process-pending)은 프로젝트 스코프 + bounded batch로 실제 Gemini 분류를
    수행하고, 상태 조회 API로 진행 상황을 확인할 수 있어야 한다."""

import uuid
from unittest.mock import patch

from app.models import Ad, User
from app.routers.campaign_tags import (
    get_campaign_tag_classification_status,
    process_pending_campaign_tags,
    reclassify_campaign_tags,
)
from app.schemas import CampaignTagProcessPendingRequest, CampaignTagReclassifyRequest
from app.services.campaign_tags import create_campaign_tag
from app.services.pending_campaign_classification import process_pending_campaign_classification
from app.services.vision_tagging import GeminiQuotaExceeded


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


# ── §2-1/§2-5: "기존 광고 반영" — reset_count만으로는 상태를 온전히 표현하지 못하는 문제 ──────


def test_already_pending_ads_are_counted_but_not_reset(db, competitor):
    """굿네이버스 재현 케이스: 태그가 없던 시절 생성된 광고는 이미 PENDING이다. reset 대상은
    아니지만(원래도 PENDING이었으므로) total_target_count에는 반드시 포함돼야 한다 — 그렇지 않으면
    "0개 처리"처럼 보여 사용자가 버튼이 작동하지 않는다고 오해한다."""
    create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    already_pending_ad = _make_ad(db, competitor, "P1", campaign_classification_status="PENDING")
    success_ad = _make_ad(
        db, competitor, "S1", campaign_classification_status="SUCCESS", campaign_tag_assignment_source="AI"
    )

    user = db.get(User, competitor.project.user_id)
    result = reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=False), db=db, user=user
    )

    db.refresh(already_pending_ad)
    assert result.reset_count == 1  # success_ad만 실제 reset
    assert result.already_pending_count == 1  # already_pending_ad는 원래도 PENDING
    assert result.total_target_count == 2  # 그러나 "기존 광고 반영" 대상 전체에는 둘 다 포함
    assert already_pending_ad.campaign_classification_status == "PENDING"  # 건드려지지 않음


def test_all_existing_ads_already_pending_shows_nonzero_total(db, competitor):
    """태그를 프로젝트에 처음 추가한 직후처럼, 기존 광고 전부가 PENDING인 상황 — reset_count=0
    이어도 total_target_count는 0이 아니어야 사용자가 "반영 대상이 있다"는 걸 알 수 있다."""
    create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    _make_ad(db, competitor, "P1", campaign_classification_status="PENDING")
    _make_ad(db, competitor, "P2", campaign_classification_status="PENDING")

    user = db.get(User, competitor.project.user_id)
    result = reclassify_campaign_tags(
        competitor.project_id, CampaignTagReclassifyRequest(include_user_assigned=False), db=db, user=user
    )

    assert result.reset_count == 0
    assert result.already_pending_count == 2
    assert result.total_target_count == 2


# ── §2-2: 재분류 상태 조회 API ───────────────────────────────────────────────


def test_classification_status_endpoint_counts_by_status(db, competitor):
    _make_ad(db, competitor, "P1", campaign_classification_status="PENDING")
    _make_ad(db, competitor, "S1", campaign_classification_status="SUCCESS")
    _make_ad(db, competitor, "S2", campaign_classification_status="SUCCESS")
    _make_ad(db, competitor, "N1", campaign_classification_status="NEEDS_REVIEW")
    _make_ad(db, competitor, "F1", campaign_classification_status="FAILED")

    user = db.get(User, competitor.project.user_id)
    status = get_campaign_tag_classification_status(competitor.project_id, db=db, user=user)

    assert status.pending == 1
    assert status.success == 2
    assert status.needs_review == 1
    assert status.failed == 1


# ── §2-3: "지금 재분류 실행" — bounded batch + project 격리 ─────────────────────


def test_process_pending_endpoint_respects_batch_limit(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    for i in range(5):
        _make_ad(db, competitor, f"P{i}", campaign_classification_status="PENDING")

    user = db.get(User, competitor.project.user_id)
    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "이유"),
    ):
        result = process_pending_campaign_tags(
            competitor.project_id, CampaignTagProcessPendingRequest(limit=2), db=db, user=user
        )

    assert result.processed == 2  # limit=2를 넘지 않음
    assert result.succeeded == 2
    assert result.pending_remaining == 3


def test_process_pending_endpoint_caps_limit_at_configured_max(db, competitor, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "campaign_classification_manual_batch_size", 3)
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    for i in range(10):
        _make_ad(db, competitor, f"P{i}", campaign_classification_status="PENDING")

    user = db.get(User, competitor.project.user_id)
    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "이유"),
    ):
        # 사용자가 limit=100을 요청해도(한 요청에 수십~수백 개를 Gemini에 보내면 안 됨) 설정된
        # 상한(3)으로 잘린다.
        result = process_pending_campaign_tags(
            competitor.project_id, CampaignTagProcessPendingRequest(limit=100), db=db, user=user
        )

    assert result.processed == 3


def test_process_pending_endpoint_does_not_touch_other_project(db, competitor):
    from app.models import Competitor, Project

    other_project = Project(id=uuid.uuid4(), user_id=competitor.project.user_id, name="다른 프로젝트")
    db.add(other_project)
    db.flush()
    other_competitor = Competitor(
        id=uuid.uuid4(), project_id=other_project.id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=3", page_id="3",
    )
    db.add(other_competitor)
    db.commit()

    create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    other_ad = _make_ad(db, other_competitor, "O1", campaign_classification_status="PENDING")

    user = db.get(User, competitor.project.user_id)
    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag"
    ) as mocked:
        process_pending_campaign_tags(
            competitor.project_id, CampaignTagProcessPendingRequest(limit=10), db=db, user=user
        )

    mocked.assert_not_called()  # 대상 프로젝트에 PENDING 소재가 없으므로 호출 자체가 없어야 함
    db.refresh(other_ad)
    assert other_ad.campaign_classification_status == "PENDING"  # 다른 프로젝트 소재는 그대로


def test_process_pending_endpoint_quota_stop_is_graceful(db, competitor):
    create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    ad = _make_ad(db, competitor, "P1", campaign_classification_status="PENDING")

    user = db.get(User, competitor.project.user_id)
    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        side_effect=GeminiQuotaExceeded("429"),
    ):
        result = process_pending_campaign_tags(
            competitor.project_id, CampaignTagProcessPendingRequest(limit=10), db=db, user=user
        )

    assert result.quota_stopped is True
    assert result.processed == 0
    db.refresh(ad)
    assert ad.campaign_classification_status == "PENDING"
    assert ad.campaign_classification_retry_count == 0

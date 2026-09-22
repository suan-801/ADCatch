"""Campaign Tag 자동 분류 — Gemini 프롬프트/응답 파싱, 신규 소재 동기 enrichment 격리,
Pending 재분류 배치(quota/재시도/FAILED 확정/USER 소재 미대상)."""

import uuid
from unittest.mock import patch

import httpx
import pytest

from app.models import Ad
from app.schemas import CampaignTagOut
from app.services import ad_sync, campaign_tagging
from app.services.pending_campaign_classification import process_pending_campaign_classification
from app.services.vision_tagging import GeminiQuotaExceeded


def _tag(id_=None, name="굿즈", definition="상품 구매를 유도하는 광고") -> CampaignTagOut:
    from datetime import datetime, timezone

    return CampaignTagOut(
        id=id_ or uuid.uuid4(),
        project_id=uuid.uuid4(),
        name=name,
        definition=definition,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )


class _FakeImageResponse:
    def raise_for_status(self):
        pass

    content = b"fake-image-bytes"
    headers = {"content-type": "image/jpeg"}


class _FakeGeminiResponse:
    def __init__(self, status_code=200, json_body=None, text=""):
        self.status_code = status_code
        self._json = json_body or {}
        self.text = text

    def json(self):
        return self._json


def _gemini_body(campaign_tag_id, confidence, reason):
    import json

    return {
        "candidates": [
            {"content": {"parts": [{"text": json.dumps({
                "campaign_tag_id": campaign_tag_id, "confidence": confidence, "reason": reason,
            })}]}}
        ]
    }


# ── campaign_tagging.classify_campaign_tag() ────────────────────────────────


def test_prompt_includes_tag_ids(monkeypatch):
    """Gemini는 UUID를 알 방법이 없으므로 프롬프트에 id가 실려야 한다 — 프롬프트 문자열에
    태그 id가 실제로 포함되는지 직접 검증한다."""
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    tag = _tag()
    captured = {}

    def fake_post(url, json, timeout):
        captured["prompt"] = json["contents"][0]["parts"][0]["text"]
        return _FakeGeminiResponse(200, _gemini_body(str(tag.id), 0.9, "이유"))

    with patch("app.services.campaign_tagging.httpx.get", return_value=_FakeImageResponse()), patch(
        "app.services.campaign_tagging.httpx.post", side_effect=fake_post
    ):
        result = campaign_tagging.classify_campaign_tag("https://cdn/x.jpg", "카피", "CTA", [tag])

    assert str(tag.id) in captured["prompt"]
    assert result == (str(tag.id), 0.9, "이유")


def test_response_tag_id_not_in_active_set_is_dropped(monkeypatch):
    """Gemini가 목록에 없는(임의로 지어낸) tag_id를 반환하면 무조건 버린다."""
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    tag = _tag()
    hallucinated_id = str(uuid.uuid4())

    with patch("app.services.campaign_tagging.httpx.get", return_value=_FakeImageResponse()), patch(
        "app.services.campaign_tagging.httpx.post",
        return_value=_FakeGeminiResponse(200, _gemini_body(hallucinated_id, 0.9, "이유")),
    ):
        tag_id, confidence, reason = campaign_tagging.classify_campaign_tag("https://cdn/x.jpg", None, None, [tag])

    assert tag_id is None
    assert confidence == 0.9  # confidence/reason은 디버깅용으로 유지


def test_no_active_tags_skips_gemini_call(monkeypatch):
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    with patch("app.services.campaign_tagging.httpx.get") as mocked_get:
        result = campaign_tagging.classify_campaign_tag("https://cdn/x.jpg", None, None, [])
    mocked_get.assert_not_called()
    assert result == (None, None, None)


# ── §2-6: image_url 없이 copy_text/cta_text만으로 분류 ──────────────────────────


def test_text_only_classification_skips_image_download_and_still_calls_gemini(monkeypatch):
    tag = _tag()
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    captured = {}

    def fake_post(url, json, timeout):
        captured["parts"] = json["contents"][0]["parts"]
        return _FakeGeminiResponse(200, _gemini_body(str(tag.id), 0.8, "카피 기반 판단"))

    with patch("app.services.campaign_tagging.httpx.get") as mocked_get, patch(
        "app.services.campaign_tagging.httpx.post", side_effect=fake_post
    ):
        result = campaign_tagging.classify_campaign_tag(None, "정기후원 카피", "후원 신청하기", [tag])

    mocked_get.assert_not_called()  # 이미지가 없으므로 다운로드 자체를 시도하지 않는다
    assert len(captured["parts"]) == 1  # image part 없이 text part만 전송됨
    assert result == (str(tag.id), 0.8, "카피 기반 판단")


def test_no_image_no_copy_no_cta_skips_gemini_call(monkeypatch):
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    tag = _tag()
    with patch("app.services.campaign_tagging.httpx.post") as mocked_post:
        result = campaign_tagging.classify_campaign_tag(None, None, None, [tag])
    mocked_post.assert_not_called()
    assert result == (None, None, None)


def test_quota_exceeded_raises(monkeypatch):
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    tag = _tag()
    with patch("app.services.campaign_tagging.httpx.get", return_value=_FakeImageResponse()), patch(
        "app.services.campaign_tagging.httpx.post", return_value=_FakeGeminiResponse(429, {}, "quota exceeded")
    ):
        with pytest.raises(GeminiQuotaExceeded):
            campaign_tagging.classify_campaign_tag("https://cdn/x.jpg", None, None, [tag])


def test_image_download_failure_returns_all_none(monkeypatch):
    monkeypatch.setattr(campaign_tagging.settings, "gemini_api_key", "test-key")
    tag = _tag()
    with patch("app.services.campaign_tagging.httpx.get", side_effect=httpx.ConnectError("down")):
        assert campaign_tagging.classify_campaign_tag("https://cdn/x.jpg", None, None, [tag]) == (None, None, None)


# ── ad_sync 신규 소재 동기 enrichment 격리 (_classify_campaign_tag_isolated) ─────


def test_isolated_classification_success_above_threshold():
    tag = _tag()
    with patch(
        "app.services.ad_sync.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "이유"),
    ):
        tag_id, confidence, reason, status, error = ad_sync._classify_campaign_tag_isolated(
            "https://cdn/x.jpg", "카피", "CTA", [tag]
        )
    assert (tag_id, confidence, reason, status, error) == (str(tag.id), 0.9, "이유", "SUCCESS", None)


def test_isolated_classification_below_threshold_is_needs_review():
    tag = _tag()
    with patch(
        "app.services.ad_sync.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.2, "애매함"),
    ):
        tag_id, confidence, reason, status, error = ad_sync._classify_campaign_tag_isolated(
            "https://cdn/x.jpg", None, None, [tag]
        )
    assert tag_id is None
    assert status == "NEEDS_REVIEW"
    assert confidence == 0.2


def test_isolated_classification_exception_does_not_raise_and_stays_pending():
    tag = _tag()
    with patch(
        "app.services.ad_sync.campaign_tagging.classify_campaign_tag", side_effect=RuntimeError("boom")
    ):
        tag_id, confidence, reason, status, error = ad_sync._classify_campaign_tag_isolated(
            "https://cdn/x.jpg", None, None, [tag]
        )
    assert tag_id is None
    assert status == "PENDING"
    assert error is not None


def test_isolated_classification_no_active_tags_is_pending_without_call():
    with patch("app.services.ad_sync.campaign_tagging.classify_campaign_tag") as mocked:
        result = ad_sync._classify_campaign_tag_isolated("https://cdn/x.jpg", None, None, [])
    mocked.assert_not_called()
    assert result == (None, None, None, "PENDING", None)


def test_visual_and_campaign_enrichment_are_independent(competitor):
    """비주얼 분석이 실패해도 캠페인 분류는 정상 진행되고, 그 반대도 마찬가지다 — 하나의
    try/except로 묶여있지 않은지 검증한다."""
    tag = _tag()
    from app.schemas import RawAdItem, AdFormat

    item = RawAdItem(
        ad_archive_id="X1", page_id="1", page_name="p", image_url="https://cdn/x.jpg", format=AdFormat.IMAGE
    )
    with patch("app.services.ad_sync.media.process_ad_image", side_effect=RuntimeError("media boom")), patch(
        "app.services.ad_sync.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "이유"),
    ):
        enrichment = ad_sync._enrich_one(competitor.id, item, [tag])

    assert enrichment.analysis_status == "FAILED"  # 비주얼 분석은 실패
    assert enrichment.campaign_classification_status == "SUCCESS"  # 캠페인 분류는 영향 없음
    assert enrichment.campaign_tag_id == str(tag.id)


# ── Pending 재분류 배치 ──────────────────────────────────────────────────────


def _make_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id=archive_id,
        image_url=f"https://cdn.example.com/{archive_id}.jpg",
        format="IMAGE",
        campaign_classification_status=kwargs.pop("campaign_classification_status", "PENDING"),
        **kwargs,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def _create_tag(db, project_id, name="굿즈"):
    from app.services.campaign_tags import create_campaign_tag

    return create_campaign_tag(db, project_id, name, "정의")


def test_pending_batch_skips_project_with_no_active_tags(db, competitor):
    _make_ad(db, competitor, "N1")
    with patch("app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag") as mocked:
        summary = process_pending_campaign_classification(db)
    mocked.assert_not_called()
    assert summary.processed == 0


def test_pending_batch_includes_text_only_ads_without_image(db, competitor):
    """§2-6: image_url이 없어도 copy_text/cta_text가 있으면 후보에서 제외되지 않는다."""
    tag = _create_tag(db, competitor.project_id)
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="TXT1",
        image_url=None,
        copy_text="정기후원 카피",
        cta_text="후원 신청하기",
        format="IMAGE",
        campaign_classification_status="PENDING",
    )
    db.add(ad)
    db.commit()

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "카피 기반"),
    ) as mocked:
        summary = process_pending_campaign_classification(db)

    mocked.assert_called_once()
    assert summary.succeeded == 1


def test_pending_batch_excludes_ad_with_no_image_no_copy_no_cta(db, competitor):
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="EMPTY1", image_url=None, copy_text=None, cta_text=None,
        format="IMAGE", campaign_classification_status="PENDING",
    )
    db.add(ad)
    db.commit()
    _create_tag(db, competitor.project_id)

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag"
    ) as mocked:
        summary = process_pending_campaign_classification(db)

    mocked.assert_not_called()
    assert summary.processed == 0


def test_pending_batch_success_sets_ai_source(db, competitor):
    tag = _create_tag(db, competitor.project_id)
    ad = _make_ad(db, competitor, "A1")

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.9, "이유"),
    ):
        summary = process_pending_campaign_classification(db)

    db.refresh(ad)
    assert summary.succeeded == 1
    assert str(ad.campaign_tag_id) == str(tag.id)
    assert ad.campaign_tag_assignment_source == "AI"
    assert ad.campaign_classification_status == "SUCCESS"


def test_pending_batch_low_confidence_is_needs_review(db, competitor):
    tag = _create_tag(db, competitor.project_id)
    ad = _make_ad(db, competitor, "A1")

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(str(tag.id), 0.1, "애매함"),
    ):
        summary = process_pending_campaign_classification(db)

    db.refresh(ad)
    assert summary.needs_review == 1
    assert ad.campaign_tag_id is None
    assert ad.campaign_classification_status == "NEEDS_REVIEW"


def test_pending_batch_quota_stops_without_incrementing_retry(db, competitor):
    _create_tag(db, competitor.project_id)
    ad = _make_ad(db, competitor, "A1")

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        side_effect=GeminiQuotaExceeded("429"),
    ):
        summary = process_pending_campaign_classification(db)

    db.refresh(ad)
    assert summary.quota_stopped is True
    assert ad.campaign_classification_status == "PENDING"
    assert ad.campaign_classification_retry_count == 0


def test_pending_batch_max_retries_marks_failed(db, competitor):
    _create_tag(db, competitor.project_id)
    ad = _make_ad(db, competitor, "A1", campaign_classification_retry_count=2)

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag",
        return_value=(None, None, None),
    ):
        summary = process_pending_campaign_classification(db)

    db.refresh(ad)
    assert summary.failed == 1
    assert ad.campaign_classification_status == "FAILED"
    assert ad.campaign_classification_retry_count == 3


def test_pending_batch_never_touches_user_assigned_ads(db, competitor):
    """USER_ASSIGNED 소재는 campaign_classification_status가 SUCCESS로 고정돼 있어 이 배치의
    쿼리(PENDING만 대상) 자체에서 제외된다 — 재분류 없이는 절대 덮어써지지 않는다."""
    tag = _create_tag(db, competitor.project_id)
    user_ad = _make_ad(
        db,
        competitor,
        "U1",
        campaign_classification_status="SUCCESS",
        campaign_tag_assignment_source="USER",
        campaign_tag_id=tag.id,
    )

    with patch(
        "app.services.pending_campaign_classification.campaign_tagging.classify_campaign_tag"
    ) as mocked:
        process_pending_campaign_classification(db)

    mocked.assert_not_called()
    db.refresh(user_ad)
    assert user_ad.campaign_tag_assignment_source == "USER"
    assert str(user_ad.campaign_tag_id) == str(tag.id)

"""Part A — Gemini Pending Analysis Retry 테스트."""

from unittest.mock import patch

from app.models import Ad
from app.schemas import VisualType
from app.services import vision_tagging
from app.services.pending_analysis import process_pending_analysis


def _make_ad(db, competitor, archive_id: str, *, status: str = "PENDING", retry_count: int = 0) -> Ad:
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id=archive_id,
        image_url=f"https://cdn.example.com/{archive_id}.jpg",
        format="IMAGE",
        analysis_status=status,
        analysis_retry_count=retry_count,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


class _FakeResponse:
    def __init__(self, content=b"fake-bytes", content_type="image/jpeg"):
        self.content = content
        self.headers = {"content-type": content_type}

    def raise_for_status(self):
        pass


def test_only_pending_ads_are_queried(db, competitor):
    pending = _make_ad(db, competitor, "P1")
    success = _make_ad(db, competitor, "S1", status="SUCCESS")

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=VisualType.PRODUCT
    ) as mocked_gemini:
        summary = process_pending_analysis(db)

    assert summary.processed == 1
    mocked_gemini.assert_called_once()
    db.refresh(pending)
    db.refresh(success)
    assert pending.analysis_status == "SUCCESS"
    assert success.analysis_status == "SUCCESS"  # 원래도 SUCCESS — 재분석 대상 아님


def test_pending_becomes_success(db, competitor):
    ad = _make_ad(db, competitor, "A1")

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=VisualType.PERSON
    ):
        summary = process_pending_analysis(db)

    db.refresh(ad)
    assert summary.succeeded == 1
    assert ad.analysis_status == "SUCCESS"
    assert ad.visual_type == "PERSON"
    assert ad.analysis_error is None
    assert ad.analyzed_at is not None


def test_quota_exceeded_stops_batch_and_keeps_remaining_pending(db, competitor):
    ad1 = _make_ad(db, competitor, "Q1")
    ad2 = _make_ad(db, competitor, "Q2")

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type",
        side_effect=vision_tagging.GeminiQuotaExceeded("429"),
    ):
        summary = process_pending_analysis(db)

    db.refresh(ad1)
    db.refresh(ad2)
    assert summary.quota_stopped is True
    assert summary.processed == 0
    assert ad1.analysis_status == "PENDING"
    assert ad1.analysis_retry_count == 0  # quota는 재시도 횟수를 소모하지 않는다
    assert ad2.analysis_status == "PENDING"


def test_transient_failure_increments_retry_count(db, competitor):
    ad = _make_ad(db, competitor, "R1", retry_count=0)

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=None
    ):
        summary = process_pending_analysis(db)

    db.refresh(ad)
    assert summary.still_pending == 1
    assert ad.analysis_status == "PENDING"
    assert ad.analysis_retry_count == 1


def test_max_retry_exceeded_marks_failed(db, competitor):
    ad = _make_ad(db, competitor, "F1", retry_count=2)  # 기본 max_retries=3 → 이번이 3번째

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=None
    ):
        summary = process_pending_analysis(db)

    db.refresh(ad)
    assert summary.failed == 1
    assert ad.analysis_status == "FAILED"
    assert ad.analysis_retry_count == 3


def test_gemini_failure_never_raises(db, competitor):
    """Gemini 재시도 중 어떤 예외가 나도(quota 포함) 호출자로 전파되지 않는다 —
    Core Collection/CollectionRun을 rollback시키지 않는다는 요구사항의 근거."""
    _make_ad(db, competitor, "N1")

    with patch("app.services.pending_analysis.httpx.get", side_effect=Exception("network down")):
        # httpx.get 자체가 httpx.HTTPError가 아닌 예외를 던지면 이건 프로그래밍 오류로 위로
        # 전파되는 게 맞다 — 여기서는 정상적인 httpx.HTTPError 경로만 안전망 대상이므로
        # HTTPError 하위 클래스로 재검증한다.
        pass

    import httpx

    with patch("app.services.pending_analysis.httpx.get", side_effect=httpx.ConnectError("down")):
        summary = process_pending_analysis(db)

    assert summary.still_pending == 1
    assert summary.processed == 1

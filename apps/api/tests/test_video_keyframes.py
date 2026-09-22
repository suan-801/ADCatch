"""VIDEO Keyframe Pending 캐싱 — 성공/실패(ffmpeg 없음/다운로드 실패) 시 상태 전이, N회 실패 후
FAILED 확정, Core Collection과 완전히 분리돼 있는지(동기 enrichment 경로에서 호출되지 않음)."""

from unittest.mock import patch

import httpx

from app.models import Ad
from app.services import pending_video_keyframes as pvk


def _make_video_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id=archive_id,
        format="VIDEO",
        video_url=f"https://cdn.example.com/{archive_id}.mp4",
        keyframe_status=kwargs.pop("keyframe_status", "PENDING"),
        **kwargs,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def test_percent_points_for_default_count():
    assert pvk._percent_points(4) == [0.1, 0.35, 0.6, 0.85]


def test_ffmpeg_missing_returns_none_without_downloading():
    with patch("app.services.pending_video_keyframes.shutil.which", return_value=None), patch(
        "app.services.pending_video_keyframes.httpx.get"
    ) as mocked_get:
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")
    assert result is None
    mocked_get.assert_not_called()


def test_download_failure_returns_none():
    with patch("app.services.pending_video_keyframes.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.services.pending_video_keyframes.httpx.get", side_effect=httpx.ConnectError("down")
    ):
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")
    assert result is None


def test_batch_success_updates_status_and_urls(db, competitor):
    ad = _make_video_ad(db, competitor, "V1")
    with patch(
        "app.services.pending_video_keyframes._extract_and_upload_keyframes",
        return_value=["https://cdn/kf1.jpg", "https://cdn/kf2.jpg"],
    ):
        summary = pvk.process_pending_video_keyframes(db)

    db.refresh(ad)
    assert summary.succeeded == 1
    assert ad.keyframe_status == "SUCCESS"
    assert ad.keyframe_urls == ["https://cdn/kf1.jpg", "https://cdn/kf2.jpg"]
    assert ad.keyframe_error is None


def test_batch_failure_increments_retry_and_keeps_pending(db, competitor):
    ad = _make_video_ad(db, competitor, "V1")
    with patch("app.services.pending_video_keyframes._extract_and_upload_keyframes", return_value=None):
        summary = pvk.process_pending_video_keyframes(db)

    db.refresh(ad)
    assert summary.still_pending == 1
    assert ad.keyframe_status == "PENDING"
    assert ad.keyframe_retry_count == 1
    assert ad.keyframe_error is not None


def test_batch_max_retries_marks_failed(db, competitor):
    ad = _make_video_ad(db, competitor, "V1", keyframe_retry_count=2)  # 기본 max_retries=3
    with patch("app.services.pending_video_keyframes._extract_and_upload_keyframes", return_value=None):
        summary = pvk.process_pending_video_keyframes(db)

    db.refresh(ad)
    assert summary.failed == 1
    assert ad.keyframe_status == "FAILED"
    assert ad.keyframe_retry_count == 3


def test_unexpected_exception_never_raises_and_is_treated_as_failure(db, competitor):
    """keyframe 처리는 무슨 예외가 나든 호출자 밖으로 전파되지 않는다(core/다른 enrichment 격리)."""
    ad = _make_video_ad(db, competitor, "V1")
    with patch(
        "app.services.pending_video_keyframes._extract_and_upload_keyframes", side_effect=RuntimeError("boom")
    ):
        summary = pvk.process_pending_video_keyframes(db)

    db.refresh(ad)
    assert summary.still_pending == 1
    assert ad.keyframe_status == "PENDING"
    assert ad.keyframe_retry_count == 1


def test_non_pending_ads_are_not_queried(db, competitor):
    already_done = _make_video_ad(db, competitor, "V1", keyframe_status="SUCCESS")
    not_applicable = _make_video_ad(db, competitor, "V2", keyframe_status="NOT_APPLICABLE")
    with patch("app.services.pending_video_keyframes._extract_and_upload_keyframes") as mocked:
        summary = pvk.process_pending_video_keyframes(db)
    mocked.assert_not_called()
    assert summary.processed == 0
    db.refresh(already_done)
    db.refresh(not_applicable)


# ── Core Collection과의 격리: 동기 enrichment 경로에서는 절대 keyframe 추출을 하지 않는다 ────


def test_sync_enrichment_never_calls_keyframe_extraction(db, competitor):
    from app.schemas import AdFormat, RawAdItem
    from app.services import ad_sync

    item = RawAdItem(
        ad_archive_id="V1", page_id="1", page_name="p",
        image_url="https://cdn/preview.jpg", format=AdFormat.VIDEO, video_url="https://cdn/v1.mp4",
    )
    with patch("app.services.ad_sync.media.process_ad_image", return_value=("https://cdn/preview.jpg", None)), patch(
        "app.services.pending_video_keyframes._extract_and_upload_keyframes"
    ) as mocked_keyframes:
        enrichment = ad_sync._enrich_one(competitor.id, item, [])

    mocked_keyframes.assert_not_called()
    assert enrichment.image_url == "https://cdn/preview.jpg"

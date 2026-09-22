"""VIDEO Keyframe Pending 캐싱 — 성공/실패(ffmpeg 없음/다운로드 실패) 시 상태 전이, N회 실패 후
FAILED 확정, Core Collection과 완전히 분리돼 있는지(동기 enrichment 경로에서 호출되지 않음),
2026-09-22 개정(streaming 다운로드/max bytes/bounded retry/4장 전부 성공해야 SUCCESS)."""

from pathlib import Path
from unittest.mock import MagicMock, patch

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


class _FakeStreamResponse:
    def __init__(self, status_code=200, chunks=None):
        self.status_code = status_code
        self._chunks = chunks if chunks is not None else [b"fake-mp4-bytes"]

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=MagicMock(), response=MagicMock(status_code=self.status_code))

    def iter_bytes(self, chunk_size=None):
        yield from self._chunks


class _FakeStreamCM:
    """httpx.stream(...)이 반환하는 컨텍스트 매니저를 흉내낸다."""

    def __init__(self, response):
        self._response = response

    def __enter__(self):
        return self._response

    def __exit__(self, *exc):
        return False


def test_percent_points_for_default_count():
    # 2026-09-22 개정 — Hook/CTA를 포함하도록 8/35/65/92% 고정 지점으로 변경.
    assert pvk._percent_points(4) == [0.08, 0.35, 0.65, 0.92]


def test_ffmpeg_missing_returns_none_without_downloading():
    with patch("app.services.pending_video_keyframes.shutil.which", return_value=None), patch(
        "app.services.pending_video_keyframes.httpx.stream"
    ) as mocked_stream:
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")
    assert result is None
    mocked_stream.assert_not_called()


def test_download_failure_returns_none():
    with patch("app.services.pending_video_keyframes.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.services.pending_video_keyframes.httpx.stream", side_effect=httpx.ConnectError("down")
    ), patch("app.services.pending_video_keyframes.time.sleep"):
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")
    assert result is None


def test_download_streams_to_tempfile_not_memory(tmp_path):
    """전체를 메모리에 올리지 않고 stream으로 tempfile에 기록하는지 — 반환된 경로가 실제 파일이고
    청크들이 이어붙여 저장됐는지 확인한다."""
    chunks = [b"a" * 10, b"b" * 10]
    response = _FakeStreamResponse(chunks=chunks)
    with patch("app.services.pending_video_keyframes.httpx.stream", return_value=_FakeStreamCM(response)):
        path = pvk._download_video("https://cdn/x.mp4")
    try:
        assert path is not None
        assert path.exists()
        assert path.read_bytes() == b"a" * 10 + b"b" * 10
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def test_download_aborts_when_exceeding_max_bytes(monkeypatch):
    monkeypatch.setattr(pvk.settings, "video_keyframe_max_download_bytes", 5)
    response = _FakeStreamResponse(chunks=[b"x" * 10])
    with patch("app.services.pending_video_keyframes.httpx.stream", return_value=_FakeStreamCM(response)):
        path = pvk._download_video("https://cdn/huge.mp4")
    assert path is None


def test_download_retries_on_429_then_succeeds(monkeypatch):
    monkeypatch.setattr(pvk.settings, "video_keyframe_download_retries", 2)
    attempts = [_FakeStreamCM(_FakeStreamResponse(status_code=429)), _FakeStreamCM(_FakeStreamResponse(status_code=200))]
    with patch("app.services.pending_video_keyframes.httpx.stream", side_effect=attempts), patch(
        "app.services.pending_video_keyframes.time.sleep"
    ) as mocked_sleep:
        path = pvk._download_video("https://cdn/x.mp4")
    try:
        assert path is not None
        mocked_sleep.assert_called_once()
    finally:
        if path is not None:
            path.unlink(missing_ok=True)


def test_download_gives_up_after_bounded_retries_not_infinite(monkeypatch):
    """429가 계속 나도 retry 횟수를 넘기면 포기한다 — 무한 재시도 금지."""
    monkeypatch.setattr(pvk.settings, "video_keyframe_download_retries", 2)
    always_429 = _FakeStreamCM(_FakeStreamResponse(status_code=429))
    with patch("app.services.pending_video_keyframes.httpx.stream", return_value=always_429) as mocked_stream, patch(
        "app.services.pending_video_keyframes.time.sleep"
    ):
        path = pvk._download_video("https://cdn/x.mp4")
    assert path is None
    assert mocked_stream.call_count == 3  # 최초 시도 + retry 2회 = 3회, 그 이상은 호출되지 않음


def test_all_four_keyframes_required_for_success(tmp_path):
    """4장 중 하나라도 추출 실패하면 부분 성공을 SUCCESS로 취급하지 않는다."""
    fake_video = tmp_path / "video.mp4"
    fake_video.write_bytes(b"fake")

    def _fake_extract_frame(video_path, timestamp, out_path):
        # 1,2번째는 성공, 3번째부터 실패
        idx = int(out_path.stem.rsplit("kf", 1)[1])
        if idx <= 2:
            out_path.write_bytes(b"jpeg-bytes")
            return True
        return False

    with patch("app.services.pending_video_keyframes.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.services.pending_video_keyframes._download_video", return_value=fake_video
    ), patch("app.services.pending_video_keyframes._probe_duration_seconds", return_value=10.0), patch(
        "app.services.pending_video_keyframes._extract_frame", side_effect=_fake_extract_frame
    ), patch(
        "app.services.pending_video_keyframes.storage.upload_thumbnail", return_value="https://cdn/uploaded.jpg"
    ) as mocked_upload:
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")

    assert result is None  # 3번째가 실패했으므로 부분 성공(2장)은 SUCCESS가 아니다
    assert mocked_upload.call_count == 2  # 실패 시점 이전까지만 업로드 시도


def test_all_four_keyframes_succeed_returns_four_urls(tmp_path):
    fake_video = tmp_path / "video.mp4"
    fake_video.write_bytes(b"fake")

    def _fake_extract_frame(video_path, timestamp, out_path):
        out_path.write_bytes(b"jpeg-bytes")
        return True

    with patch("app.services.pending_video_keyframes.shutil.which", return_value="/usr/bin/ffmpeg"), patch(
        "app.services.pending_video_keyframes._download_video", return_value=fake_video
    ), patch("app.services.pending_video_keyframes._probe_duration_seconds", return_value=10.0), patch(
        "app.services.pending_video_keyframes._extract_frame", side_effect=_fake_extract_frame
    ), patch(
        "app.services.pending_video_keyframes.storage.upload_thumbnail",
        side_effect=lambda path, content, content_type: f"https://cdn/{path}",
    ):
        result = pvk._extract_and_upload_keyframes("comp-1", "A1", "https://cdn/x.mp4")

    assert result is not None
    assert len(result) == 4


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

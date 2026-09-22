"""VIDEO Keyframe Pending 캐싱 — app.services.pending_analysis와 동일한 모양.

Core Collection(app.services.ad_sync._enrich_one, ThreadPoolExecutor 안)에서는 keyframe을 절대
만들지 않는다 — 영상 다운로드+ffprobe+ffmpeg×N+Storage 업로드×N은 무겁고, 이미 "대량 소재 브랜드
첫 수집이 무한 수집중처럼 보이던 문제"를 해결하려고 넣은 병렬 enrichment 구조를 다시 느리게 만들기
때문이다. 신규 VIDEO 소재는 keyframe_status='PENDING'만 세팅되고, 이 모듈이 별도 배치로 처리한다.

ffmpeg가 시스템에 없으면 즉시 실패로 처리한다(무한 재시도 방지). 어떤 이유로 실패하든 예외를
호출자 밖으로 던지지 않는다 — keyframe 처리 실패가 수집 자체나 다른 enrichment(비주얼/캠페인
분류)에 영향을 줘서는 안 된다. 실패해도 기존 image_url(preview 썸네일)로 항상 폴백 가능하다.
"""

import logging
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad
from app.services import storage
from app.services.timing import stage_timer

logger = logging.getLogger("adcatcher.pending_video_keyframes")


@dataclass
class PendingKeyframeSummary:
    processed: int = 0
    succeeded: int = 0
    still_pending: int = 0
    failed: int = 0


def _percent_points(count: int) -> list[float]:
    """영상 길이 대비 keyframe을 뽑을 지점(0~1) 목록. count=4면 [0.1, 0.35, 0.6, 0.85]
    (reference 스크립트의 6장 대신 제품 UI에 맞춰 4장으로 축소, 0.1~0.85 구간에 균등 배치)."""
    if count <= 1:
        return [0.5]
    start, end = 0.1, 0.85
    step = (end - start) / (count - 1)
    return [round(start + step * i, 4) for i in range(count)]


def _ffmpeg_available() -> bool:
    return shutil.which(settings.ffmpeg_path) is not None and shutil.which("ffprobe") is not None


def _download_video(video_url: str) -> Path | None:
    try:
        resp = httpx.get(video_url, timeout=settings.video_keyframe_max_download_seconds)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    try:
        tmp.write(resp.content)
    finally:
        tmp.close()
    return Path(tmp.name)


def _probe_duration_seconds(video_path: Path) -> float | None:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(video_path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        duration = float(result.stdout.strip())
        return duration if duration > 0 else None
    except (subprocess.SubprocessError, ValueError, OSError):
        return None


def _extract_frame(video_path: Path, timestamp_seconds: float, out_path: Path) -> bool:
    try:
        subprocess.run(
            [
                settings.ffmpeg_path,
                "-loglevel", "error",
                "-ss", f"{timestamp_seconds:.2f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "3",
                "-y", str(out_path),
            ],
            capture_output=True,
            timeout=30,
            check=True,
        )
    except (subprocess.SubprocessError, OSError):
        return False
    return out_path.exists() and out_path.stat().st_size > 0


def _extract_and_upload_keyframes(competitor_id: uuid.UUID, ad_archive_id: str, video_url: str) -> list[str] | None:
    """성공 시 캐싱된 keyframe URL 목록(1개 이상), 실패 시 None을 반환한다. 예외를 던지지 않는다."""
    if not _ffmpeg_available():
        return None

    video_path = _download_video(video_url)
    if video_path is None:
        return None

    try:
        duration = _probe_duration_seconds(video_path)
        if duration is None:
            return None

        urls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, pct in enumerate(_percent_points(settings.video_keyframe_count), start=1):
                frame_path = Path(tmp_dir) / f"{ad_archive_id}_kf{i}.jpg"
                if not _extract_frame(video_path, duration * pct, frame_path):
                    continue
                uploaded = storage.upload_thumbnail(
                    f"{competitor_id}/{ad_archive_id}_kf{i}.jpg", frame_path.read_bytes(), "image/jpeg"
                )
                if uploaded:
                    urls.append(uploaded)
        return urls or None
    finally:
        video_path.unlink(missing_ok=True)


def process_pending_video_keyframes(
    db: Session,
    *,
    competitor_id: uuid.UUID | None = None,
    limit: int | None = None,
) -> PendingKeyframeSummary:
    """keyframe_status='PENDING'인 VIDEO 소재를 oldest-first로 골라 keyframe을 추출/캐싱한다.

    - 성공: keyframe_status=SUCCESS, keyframe_urls 갱신, keyframe_error=NULL.
    - 실패(다운로드 실패/ffmpeg 미설치/ffprobe 실패 등 무엇이든): keyframe_retry_count += 1.
      임계값(video_keyframe_max_retries) 초과 시 keyframe_status=FAILED로 확정.
    - 어떤 경우든 기존 image_url(preview 썸네일)은 그대로 남아있으므로 Drawer는 항상 정상 표시된다.
    """
    batch_limit = limit if limit is not None else settings.video_keyframe_pending_batch_size

    query = select(Ad).where(
        Ad.format == "VIDEO", Ad.video_url.is_not(None), Ad.keyframe_status == "PENDING"
    )
    if competitor_id is not None:
        query = query.where(Ad.competitor_id == competitor_id)
    query = query.order_by(Ad.first_seen_at.asc()).limit(batch_limit)

    pending_ads = db.scalars(query).all()
    summary = PendingKeyframeSummary()

    for ad in pending_ads:
        try:
            with stage_timer("pending_video_keyframes", ad_archive_id=ad.ad_archive_id):
                urls = _extract_and_upload_keyframes(ad.competitor_id, ad.ad_archive_id, ad.video_url)
        except Exception as e:  # noqa: BLE001 - keyframe 처리는 무슨 예외가 나든 core/다른 enrichment와 격리한다.
            urls = None
            logger.warning("keyframe extraction raised unexpectedly for %s: %s", ad.ad_archive_id, e)

        summary.processed += 1
        if urls:
            ad.keyframe_urls = urls
            ad.keyframe_status = "SUCCESS"
            ad.keyframe_error = None
            summary.succeeded += 1
        else:
            ad.keyframe_retry_count += 1
            ad.keyframe_error = "영상 다운로드 또는 keyframe 추출 실패(ffmpeg 미설치 포함)"
            if ad.keyframe_retry_count >= settings.video_keyframe_max_retries:
                ad.keyframe_status = "FAILED"
                summary.failed += 1
            else:
                summary.still_pending += 1
        db.commit()

    return summary

"""VIDEO Keyframe Pending 캐싱 — app.services.pending_analysis와 동일한 모양.

Core Collection(app.services.ad_sync._enrich_one, ThreadPoolExecutor 안)에서는 keyframe을 절대
만들지 않는다 — 영상 다운로드+ffprobe+ffmpeg×N+Storage 업로드×N은 무겁고, 이미 "대량 소재 브랜드
첫 수집이 무한 수집중처럼 보이던 문제"를 해결하려고 넣은 병렬 enrichment 구조를 다시 느리게 만들기
때문이다. 신규 VIDEO 소재는 keyframe_status='PENDING'만 세팅되고, 이 모듈이 별도 배치로 처리한다.

ffmpeg가 시스템에 없으면 즉시 실패로 처리한다(무한 재시도 방지). 어떤 이유로 실패하든 예외를
호출자 밖으로 던지지 않는다 — keyframe 처리 실패가 수집 자체나 다른 enrichment(비주얼/캠페인
분류)에 영향을 줘서는 안 된다. 실패해도 기존 image_url(preview 썸네일)로 항상 폴백 가능하다.

2026-09-22 개정: 원본 mp4는 절대 영구 저장하지 않는다는 원칙은 그대로 유지하되,
  - 다운로드를 메모리에 통째로 올리지 않고 stream으로 tempfile에 바로 쓴다(대용량 영상이
    worker 메모리를 잡아먹지 않게 max_download_bytes로 상한을 둔다).
  - 일시적 오류(429/5xx)에 한해 짧은 bounded retry를 허용한다(무한 재시도는 금지).
  - Key Visual은 정확히 4장(video_keyframe_count) 성공해야 SUCCESS로 처리한다 — 1~3장만
    성공해도 SUCCESS로 취급하지 않고 재시도 가능한 실패로 남긴다.
  - 4개 지점은 8%/35%/65%/92%(마케팅 영상의 Hook·CTA를 포함하도록 ADetect reference의
    8/22/40/58/75/92 구조를 4장에 맞게 축소).
  - 저장 해상도는 원본 그대로가 아니라 최대 너비 video_keyframe_max_width로 제한한다(비율
    유지, upscale 없음 — ffmpeg scale filter로 추출 시점에 바로 처리해 별도 이미지 처리
    라이브러리를 추가하지 않는다).
"""

import logging
import shutil
import subprocess
import tempfile
import time
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

_RETRYABLE_STATUS_CODES = {429}
_DOWNLOAD_RETRY_BACKOFF_SECONDS = 2

# 마케팅 영상의 Hook(초반)과 CTA(막판)를 놓치지 않도록 4장 기본 지점 — ADetect reference의
# 8/22/40/58/75/92(6장) 구조를 4장에 맞춰 축소한 값.
_DEFAULT_FOUR_POINT_PCTS = (0.08, 0.35, 0.65, 0.92)


@dataclass
class PendingKeyframeSummary:
    processed: int = 0
    succeeded: int = 0
    still_pending: int = 0
    failed: int = 0


def _percent_points(count: int) -> list[float]:
    """영상 길이 대비 keyframe을 뽑을 지점(0~1) 목록. count=4(기본값)면 고정된 8/35/65/92% 지점을
    쓴다 — count가 4가 아닌 값으로 설정되면 8%~92% 구간에 균등 배치하는 일반 공식으로 폴백한다."""
    if count == 4:
        return list(_DEFAULT_FOUR_POINT_PCTS)
    if count <= 1:
        return [0.5]
    start, end = 0.08, 0.92
    step = (end - start) / (count - 1)
    return [round(start + step * i, 4) for i in range(count)]


def _ffmpeg_available() -> bool:
    return shutil.which(settings.ffmpeg_path) is not None and shutil.which("ffprobe") is not None


def _download_video(video_url: str) -> Path | None:
    """video_url을 stream으로 tempfile에 바로 기록한다(전체를 메모리에 올리지 않음).
    max_download_bytes를 넘으면 즉시 중단하고 None을 반환한다. 429/5xx는 짧은 bounded retry
    (video_keyframe_download_retries회)를 허용하되 무한 재시도는 하지 않는다."""
    max_bytes = settings.video_keyframe_max_download_bytes
    attempts = settings.video_keyframe_download_retries + 1

    for attempt in range(attempts):
        tmp_path: Path | None = None
        try:
            with httpx.stream(
                "GET", video_url, timeout=settings.video_keyframe_max_download_seconds, follow_redirects=True
            ) as resp:
                if resp.status_code in _RETRYABLE_STATUS_CODES or resp.status_code >= 500:
                    if attempt < attempts - 1:
                        time.sleep(_DOWNLOAD_RETRY_BACKOFF_SECONDS * (attempt + 1))
                        continue
                    return None
                resp.raise_for_status()

                fd = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
                tmp_path = Path(fd.name)
                total = 0
                try:
                    for chunk in resp.iter_bytes(chunk_size=256 * 1024):
                        total += len(chunk)
                        if total > max_bytes:
                            fd.close()
                            tmp_path.unlink(missing_ok=True)
                            return None
                        fd.write(chunk)
                finally:
                    fd.close()
                return tmp_path
        except httpx.HTTPError:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)
            if attempt < attempts - 1:
                time.sleep(_DOWNLOAD_RETRY_BACKOFF_SECONDS * (attempt + 1))
                continue
            return None
    return None


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
    """지정 시점의 프레임 1장을 추출한다. aspect ratio를 유지하면서 upscale 없이 최대
    video_keyframe_max_width로 제한한다(Storage 용량 절감) — 별도 이미지 처리 라이브러리 없이
    ffmpeg scale filter로 추출과 동시에 처리한다."""
    scale_filter = f"scale='min({settings.video_keyframe_max_width},iw)':-2"
    try:
        subprocess.run(
            [
                settings.ffmpeg_path,
                "-loglevel", "error",
                "-ss", f"{timestamp_seconds:.2f}",
                "-i", str(video_path),
                "-frames:v", "1",
                "-vf", scale_filter,
                "-q:v", "4",
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
    """성공 시 정확히 video_keyframe_count장의 캐싱된 keyframe URL, 그 중 하나라도 추출/업로드에
    실패하면 None을 반환한다(부분 성공을 SUCCESS로 취급하지 않는다). 예외를 던지지 않는다."""
    if not _ffmpeg_available():
        return None

    video_path = _download_video(video_url)
    if video_path is None:
        return None

    try:
        duration = _probe_duration_seconds(video_path)
        if duration is None:
            return None

        target_count = settings.video_keyframe_count
        urls: list[str] = []
        with tempfile.TemporaryDirectory() as tmp_dir:
            for i, pct in enumerate(_percent_points(target_count), start=1):
                frame_path = Path(tmp_dir) / f"{ad_archive_id}_kf{i}.jpg"
                if not _extract_frame(video_path, duration * pct, frame_path):
                    return None  # 4장 전부 성공해야 SUCCESS — 하나라도 실패하면 즉시 실패 처리.
                uploaded = storage.upload_thumbnail(
                    f"{competitor_id}/{ad_archive_id}_kf{i}.jpg", frame_path.read_bytes(), "image/jpeg"
                )
                if not uploaded:
                    return None
                urls.append(uploaded)

        return urls if len(urls) == target_count else None
    finally:
        video_path.unlink(missing_ok=True)


def process_pending_video_keyframes(
    db: Session,
    *,
    competitor_id: uuid.UUID | None = None,
    limit: int | None = None,
) -> PendingKeyframeSummary:
    """keyframe_status='PENDING'인 VIDEO 소재를 oldest-first로 골라 keyframe을 추출/캐싱한다.

    - 성공(4장 전부): keyframe_status=SUCCESS, keyframe_urls 갱신, keyframe_error=NULL.
    - 실패(다운로드 실패/ffmpeg 미설치/ffprobe 실패/일부만 성공 등 무엇이든): keyframe_retry_count += 1.
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
            ad.keyframe_error = "영상 다운로드 또는 keyframe 4장 추출/업로드 실패(ffmpeg 미설치 포함)"
            if ad.keyframe_retry_count >= settings.video_keyframe_max_retries:
                ad.keyframe_status = "FAILED"
                summary.failed += 1
            else:
                summary.still_pending += 1
        db.commit()

    return summary

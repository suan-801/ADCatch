"""신규 소재 이미지 처리 — 원본 이미지를 한 번만 다운로드해
(1) Supabase Storage 캐싱과 (2) Gemini Vision 태깅을 함께 수행한다.
"""

import uuid

import httpx

from app.schemas import VisualType
from app.services import storage, vision_tagging
from app.services.timing import stage_timer


def process_ad_image(competitor_id: uuid.UUID, ad_archive_id: str, image_url: str) -> tuple[str, VisualType | None]:
    """(캐싱된 or 원본 image_url, 비전 태깅 결과)를 반환한다.
    다운로드/업로드/태깅 중 어떤 단계가 실패해도 원본 image_url로 안전하게 폴백한다.

    G-01: 신규 소재 1건당 thumbnail_download / storage_upload / gemini_visual_analysis 시간을
    structured log로 남긴다 — 이 함수는 ThreadPoolExecutor로 여러 소재가 동시에 실행되므로
    로그 1건당 ad_archive_id를 함께 남겨 이후 stage별로 집계할 수 있게 한다."""
    try:
        with stage_timer("thumbnail_download", ad_archive_id=ad_archive_id):
            resp = httpx.get(image_url, timeout=30)
            resp.raise_for_status()
    except httpx.HTTPError:
        return image_url, None

    content = resp.content
    content_type = resp.headers.get("content-type", "image/jpeg")
    ext = "png" if "png" in content_type else "jpg"

    with stage_timer("storage_upload", ad_archive_id=ad_archive_id):
        cached_url = storage.upload_thumbnail(f"{competitor_id}/{ad_archive_id}.{ext}", content, content_type)

    visual_type: VisualType | None = None
    try:
        with stage_timer("gemini_visual_analysis", ad_archive_id=ad_archive_id):
            visual_type = vision_tagging.analyze_visual_type(content, content_type)
    except vision_tagging.GeminiQuotaExceeded:
        pass

    return cached_url or image_url, visual_type

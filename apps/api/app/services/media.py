"""신규 소재 이미지 처리 — 원본 이미지를 한 번만 다운로드해
(1) Supabase Storage 캐싱과 (2) Gemini Vision 태깅을 함께 수행한다.
"""

import uuid

import httpx

from app.schemas import VisualType
from app.services import storage, vision_tagging


def process_ad_image(competitor_id: uuid.UUID, ad_archive_id: str, image_url: str) -> tuple[str, VisualType | None]:
    """(캐싱된 or 원본 image_url, 비전 태깅 결과)를 반환한다.
    다운로드/업로드/태깅 중 어떤 단계가 실패해도 원본 image_url로 안전하게 폴백한다."""
    try:
        resp = httpx.get(image_url, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError:
        return image_url, None

    content = resp.content
    content_type = resp.headers.get("content-type", "image/jpeg")
    ext = "png" if "png" in content_type else "jpg"

    cached_url = storage.upload_thumbnail(f"{competitor_id}/{ad_archive_id}.{ext}", content, content_type)

    visual_type: VisualType | None = None
    try:
        visual_type = vision_tagging.analyze_visual_type(content, content_type)
    except vision_tagging.GeminiQuotaExceeded:
        pass

    return cached_url or image_url, visual_type

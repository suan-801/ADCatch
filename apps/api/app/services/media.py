"""신규 소재 이미지 처리 — 원본 이미지를 한 번만 다운로드해
(1) Supabase Storage 캐싱과 (2) Gemini Vision 태깅을 함께 수행한다.

기존 소재 재발견 시의 image_url backfill(app.services.ad_sync)은 "이미지 캐싱"만 필요하고
Gemini 태깅은 절대 다시 돌리면 안 된다(재발견마다 동기 Gemini 호출을 하면 Core Collection
latency와 Gemini quota 모두에 영향을 준다) — 그래서 다운로드+캐싱 로직을 _download_and_cache()로
분리해 process_ad_image()(신규 소재, 캐싱+Gemini)와 cache_thumbnail_only()(기존 소재 backfill,
캐싱만)가 공유한다.
"""

import uuid

import httpx

from app.schemas import VisualType
from app.services import storage, vision_tagging
from app.services.timing import stage_timer


def _download_and_cache(
    competitor_id: uuid.UUID, ad_archive_id: str, image_url: str, *, stage_prefix: str = "thumbnail"
) -> tuple[str, bytes | None, str | None]:
    """원본 이미지를 다운로드해 Storage에 캐싱한다. 반환값은
    (캐싱된 or 원본 image_url, 다운로드한 bytes(실패 시 None), content-type(실패 시 None)).
    다운로드가 실패하면 원본 image_url로 안전하게 폴백한다."""
    try:
        with stage_timer(f"{stage_prefix}_download", ad_archive_id=ad_archive_id):
            resp = httpx.get(image_url, timeout=30)
            resp.raise_for_status()
    except httpx.HTTPError:
        return image_url, None, None

    content = resp.content
    content_type = resp.headers.get("content-type", "image/jpeg")
    ext = "png" if "png" in content_type else "jpg"

    with stage_timer(f"{stage_prefix}_upload", ad_archive_id=ad_archive_id):
        cached_url = storage.upload_thumbnail(f"{competitor_id}/{ad_archive_id}.{ext}", content, content_type)

    return cached_url or image_url, content, content_type


def process_ad_image(competitor_id: uuid.UUID, ad_archive_id: str, image_url: str) -> tuple[str, VisualType | None]:
    """(캐싱된 or 원본 image_url, 비전 태깅 결과)를 반환한다.
    다운로드/업로드/태깅 중 어떤 단계가 실패해도 원본 image_url로 안전하게 폴백한다.

    G-01: 신규 소재 1건당 thumbnail_download / storage_upload / gemini_visual_analysis 시간을
    structured log로 남긴다 — 이 함수는 ThreadPoolExecutor로 여러 소재가 동시에 실행되므로
    로그 1건당 ad_archive_id를 함께 남겨 이후 stage별로 집계할 수 있게 한다."""
    final_url, content, content_type = _download_and_cache(competitor_id, ad_archive_id, image_url)
    if content is None:
        return final_url, None

    visual_type: VisualType | None = None
    try:
        with stage_timer("gemini_visual_analysis", ad_archive_id=ad_archive_id):
            visual_type = vision_tagging.analyze_visual_type(content, content_type)
    except vision_tagging.GeminiQuotaExceeded:
        pass

    return final_url, visual_type


def cache_thumbnail_only(competitor_id: uuid.UUID, ad_archive_id: str, image_url: str) -> str:
    """기존(재발견된) 소재의 image_url backfill 전용 — Gemini 태깅은 절대 하지 않는다.

    호출자(app.services.ad_sync)는 existing.image_url이 비어 있는 경우에만 이 함수를 부른다 —
    재발견마다 무조건 다시 다운로드/업로드하지 않는다. 실패해도 예외를 던지지 않고 원본
    image_url로 폴백한다(Core Collection을 절대 막지 않는다는 기존 enrichment 격리 원칙과 동일)."""
    final_url, _, _ = _download_and_cache(competitor_id, ad_archive_id, image_url, stage_prefix="thumbnail_backfill")
    return final_url

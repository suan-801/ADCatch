"""Supabase Storage 업로드 — Meta CDN 썸네일 캐싱 (PRD 3.3).

Meta의 광고 이미지 CDN 링크는 시간이 지나면 만료되므로, 신규 소재 발견 시 원본
이미지를 다운로드해 Supabase Storage에 캐싱하고 그 안정적인 URL을 ads.image_url에
저장한다. supabase-py 의존성 없이 Storage REST API를 httpx로 직접 호출한다.
버킷은 Public으로 생성했다는 전제하에 공개 URL을 그대로 반환한다.
"""

import httpx

from app.config import settings


def is_configured() -> bool:
    return bool(settings.supabase_url and settings.supabase_service_key and settings.supabase_storage_bucket)


def upload_thumbnail(path: str, content: bytes, content_type: str = "image/jpeg") -> str | None:
    """content를 Storage 버킷의 path에 업로드하고 공개 URL을 반환한다.
    Supabase 미설정이거나 업로드 실패 시 None을 반환해 호출자가 원본 CDN URL로 폴백하게 한다."""
    if not is_configured():
        return None

    base = settings.supabase_url.rstrip("/")
    upload_url = f"{base}/storage/v1/object/{settings.supabase_storage_bucket}/{path}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": content_type,
        "x-upsert": "true",
    }

    try:
        resp = httpx.post(upload_url, content=content, headers=headers, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError:
        return None

    return f"{base}/storage/v1/object/public/{settings.supabase_storage_bucket}/{path}"

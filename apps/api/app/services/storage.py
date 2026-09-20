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


def _list_objects(prefix: str) -> list[str]:
    """prefix(폴더) 아래의 object path 전체를 나열한다. Supabase Storage REST는 prefix 기반
    삭제를 직접 지원하지 않으므로(list → remove 2단계 필요), 재귀적으로 폴더를 순회한다."""
    base = settings.supabase_url.rstrip("/")
    list_url = f"{base}/storage/v1/object/list/{settings.supabase_storage_bucket}"
    headers = {
        "apikey": settings.supabase_service_key,
        "Authorization": f"Bearer {settings.supabase_service_key}",
        "Content-Type": "application/json",
    }
    resp = httpx.post(list_url, json={"prefix": prefix, "limit": 1000}, headers=headers, timeout=30)
    resp.raise_for_status()
    entries = resp.json()

    paths: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if not name:
            continue
        full_path = f"{prefix.rstrip('/')}/{name}"
        # id가 없는 entry는 파일이 아니라 하위 폴더(placeholder)인 경우가 많다 — 재귀 탐색.
        if entry.get("id") is None:
            paths.extend(_list_objects(full_path))
        else:
            paths.append(full_path)
    return paths


def cleanup_prefix(prefix: str) -> bool:
    """Project/Brand 삭제 시 해당 prefix(보통 `{competitor_id}/`) 아래 캐시된 썸네일을
    best-effort로 정리한다. 실패해도 예외를 던지지 않고 False만 반환한다 — 호출자(Project
    삭제 트랜잭션)가 Storage 정리 실패 때문에 DB 삭제 자체를 막아서는 안 된다(H-03)."""
    if not is_configured():
        return True  # 정리할 대상 자체가 없음(미설정) — 실패로 취급하지 않는다.

    base = settings.supabase_url.rstrip("/")
    try:
        paths = _list_objects(prefix)
        if not paths:
            return True
        remove_url = f"{base}/storage/v1/object/{settings.supabase_storage_bucket}"
        headers = {
            "apikey": settings.supabase_service_key,
            "Authorization": f"Bearer {settings.supabase_service_key}",
            "Content-Type": "application/json",
        }
        resp = httpx.request("DELETE", remove_url, json={"prefixes": paths}, headers=headers, timeout=30)
        resp.raise_for_status()
        return True
    except httpx.HTTPError:
        return False

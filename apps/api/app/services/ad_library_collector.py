"""Meta Ad Library 수집기.

Apify 액터(curious_coder/facebook-ads-library-scraper) 호출 패턴은
reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py 의
검증된 구현(run_actor → wait_run → get_items, classify_and_extract)을 그대로 이식했다.
NEW/ACTIVE/INACTIVE 상태 추적은 이 레퍼런스에 없던 부분이라 app.services.ad_sync 에서 새로 구현한다.
"""

import time
from datetime import datetime

import httpx

from app.config import settings
from app.schemas import AdFormat, RawAdItem

APIFY_API_BASE = "https://api.apify.com/v2"


class ApifyRunError(RuntimeError):
    pass


def _actor_path(actor: str) -> str:
    return actor.replace("/", "~")


def run_actor(ad_library_url: str, max_ads: int = 30) -> dict:
    actor_path = _actor_path(settings.apify_actor)
    url = f"{APIFY_API_BASE}/acts/{actor_path}/runs?token={settings.apify_token}"
    payload = {
        "urls": [{"url": ad_library_url}],
        "count": max_ads,
        "maxItems": max_ads,
        "scrapeAdDetails": True,
    }
    resp = httpx.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json()["data"]


def wait_run(run_id: str, poll_seconds: int = 8, max_wait_seconds: int = 900) -> dict:
    url = f"{APIFY_API_BASE}/actor-runs/{run_id}?token={settings.apify_token}"
    waited = 0
    while waited < max_wait_seconds:
        resp = httpx.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json()["data"]
        if data["status"] in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            return data
        time.sleep(poll_seconds)
        waited += poll_seconds
    raise ApifyRunError(f"Apify run {run_id} did not finish within {max_wait_seconds}s")


def get_dataset_items(dataset_id: str) -> list[dict]:
    url = f"{APIFY_API_BASE}/datasets/{dataset_id}/items?token={settings.apify_token}&clean=true&format=json"
    resp = httpx.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()


def classify_format_and_image(item: dict) -> tuple[AdFormat, str | None]:
    """Apify 아이템의 snapshot 에서 포맷(IMAGE/VIDEO/CAROUSEL)과 대표 썸네일 URL을 판별한다."""
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []

    if videos:
        v = videos[0]
        return AdFormat.VIDEO, v.get("video_preview_image_url")
    if cards:
        first = cards[0]
        return AdFormat.CAROUSEL, first.get("original_image_url") or first.get("resized_image_url")
    if images:
        img = images[0]
        return AdFormat.IMAGE, img.get("original_image_url") or img.get("resized_image_url")
    return AdFormat.IMAGE, None


def _extract_caption(item: dict) -> str | None:
    snap = item.get("snapshot") or {}
    body = snap.get("body") or {}
    if isinstance(body, dict):
        return (body.get("text") or "").strip() or None
    if isinstance(body, str):
        return body.strip() or None
    return None


def parse_items(items: list[dict], page_id: str) -> list[RawAdItem]:
    parsed: list[RawAdItem] = []
    for item in items:
        snap = item.get("snapshot") or {}
        ad_archive_id = str(item.get("ad_archive_id") or item.get("adArchiveID") or item.get("id") or "")
        if not ad_archive_id:
            continue
        fmt, image_url = classify_format_and_image(item)
        start_ts = snap.get("creation_time") or item.get("start_date")
        start_date = datetime.fromtimestamp(int(start_ts)) if start_ts else None
        parsed.append(
            RawAdItem(
                ad_archive_id=ad_archive_id,
                page_id=page_id,
                page_name=snap.get("page_name") or item.get("page_name") or "",
                copy_text=_extract_caption(item),
                cta_text=(snap.get("cta_text") or "").strip() or None,
                image_url=image_url,
                format=fmt,
                start_date=start_date,
            )
        )
    return parsed


def fetch_live_ads(ad_library_url: str, page_id: str, max_ads: int = 30) -> list[RawAdItem]:
    """경쟁사 Meta Ad Library URL 기준으로 현재 라이브 소재 전체를 수집한다."""
    run = run_actor(ad_library_url, max_ads=max_ads)
    finished = wait_run(run["id"])
    if finished["status"] != "SUCCEEDED":
        raise ApifyRunError(f"Apify run ended with status={finished['status']}")
    items = get_dataset_items(finished["defaultDatasetId"])
    return parse_items(items, page_id)


def extract_page_id(ad_library_url: str) -> str | None:
    """Ad Library URL의 view_all_page_id 쿼리 파라미터를 추출한다."""
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(ad_library_url).query)
    values = query.get("view_all_page_id")
    return values[0] if values else None

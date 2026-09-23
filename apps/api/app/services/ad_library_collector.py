"""Meta Ad Library 수집기.

Apify 액터(curious_coder/facebook-ads-library-scraper) 호출 패턴은
reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py 의
검증된 구현(run_actor → wait_run → get_items, classify_and_extract)을 그대로 이식했다.
NEW/ACTIVE/INACTIVE 상태 추적은 이 레퍼런스에 없던 부분이라 app.services.ad_sync 에서 새로 구현한다.
"""

import logging
import time
from datetime import datetime

import httpx

from app.config import settings
from app.schemas import AdFormat, RawAdItem
from app.services.timing import stage_timer

APIFY_API_BASE = "https://api.apify.com/v2"

media_classification_logger = logging.getLogger("adcatcher.media_classification")


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


def _raw_display_format(item: dict) -> str | None:
    """Meta/Apify가 원본 포맷 신호(display_format/displayFormat 등)를 item 최상위 또는
    snapshot 아래에 내려주는지 확인한다. 반환값은 원본 그대로(대소문자 미정규화) — 정규화는
    호출자(_normalize_display_format)가 한다."""
    snap = item.get("snapshot") or {}
    for key in ("display_format", "displayFormat"):
        value = item.get(key) or snap.get(key)
        if value:
            return str(value)
    return None


def _normalize_display_format(raw: str | None) -> str | None:
    return raw.strip().upper() if raw else None


def _log_media_classification(
    item: dict,
    ad_archive_id: str | None,
    classified_format: AdFormat,
    classification_reason: str,
) -> None:
    """실제 운영 raw structure를 계속 관찰하기 위한 진단 로그. URL 전체는 남기지 않고
    count/format/근거만 기록한다(민감 정보 최소화)."""
    snap = item.get("snapshot") or {}
    media_classification_logger.info(
        "stage=media_classification ad_archive_id=%s raw_display_format=%s videos_count=%d cards_count=%d "
        "images_count=%d classified_format=%s classification_reason=%s",
        ad_archive_id or item.get("ad_archive_id") or "unknown",
        _raw_display_format(item) or "absent",
        len(snap.get("videos") or []),
        len(snap.get("cards") or []),
        len(snap.get("images") or []),
        classified_format.value,
        classification_reason,
    )


def _media_preview_url(node: dict) -> str | None:
    """video/card 노드의 대표 poster 이미지 후보를 우선순위대로 찾는다:
    video_preview_image_url → original_image_url → resized_image_url."""
    return node.get("video_preview_image_url") or node.get("original_image_url") or node.get("resized_image_url") or None


def _find_video_url(videos: list[dict], cards: list[dict]) -> str | None:
    """videos[] 다음 cards[]의 순서로 첫 번째 유효한 video URL을 찾는다(HD 우선, SD fallback)."""
    for v in videos:
        url = v.get("video_hd_url") or v.get("video_sd_url")
        if url:
            return url
    for c in cards:
        url = c.get("video_hd_url") or c.get("video_sd_url")
        if url:
            return url
    return None


def _find_video_thumbnail(videos: list[dict], cards: list[dict], images: list[dict]) -> str | None:
    """VIDEO로 확정된 소재의 대표 썸네일 후보를 우선순위대로 찾는다: video_preview_image_url →
    original_image_url → resized_image_url(videos[] 노드 우선, 그다음 cards[] 노드) → cards의
    첫 이미지 → snapshot.images 첫 이미지 → NULL."""
    for v in videos:
        preview = _media_preview_url(v)
        if preview:
            return preview
    for c in cards:
        preview = _media_preview_url(c)
        if preview:
            return preview
    for img in images:
        url = img.get("original_image_url") or img.get("resized_image_url")
        if url:
            return url
    return None


def _find_first_image(cards: list[dict], images: list[dict]) -> str | None:
    """IMAGE로 판정된 소재(캐러셀 포함)의 대표 이미지 — 첫 카드 이미지, 없으면 snapshot.images
    첫 이미지."""
    for c in cards:
        url = c.get("original_image_url") or c.get("resized_image_url")
        if url:
            return url
    for img in images:
        url = img.get("original_image_url") or img.get("resized_image_url")
        if url:
            return url
    return None


def _classify_media(item: dict) -> tuple[AdFormat, str | None, str | None, str]:
    """classify_and_extract_media()의 순수 판별 로직. classification_reason(진단 로그용)을
    4번째 값으로 함께 반환한다.

    **format 결정 규칙 (2026-09-23 재설계 — IMAGE/VIDEO 2분류로 단순화)**:
    이전 라운드(2026-09-22)에 display_format/DCO/CAROUSEL/MULTI_IMAGES/DPA를 조합한 3-way
    분류(+ffmpeg keyframe 파이프라인)를 도입했으나, 실패 지점이 많고(다운로드→ffprobe→ffmpeg×4→
    Storage 업로드×4→재시도) ADCatcher의 목적("어떤 광고가 살아있고 어떤 패턴/캠페인으로
    운영되는지 빠르게 보는 트래커")에 비해 과한 복잡도였다. VIDEO는 아주 명확한 경우에만 VIDEO로
    판정하고, 그 외 전부(캐러셀 포함) IMAGE로 단순화했다:

      1. `_raw_display_format()`이 명시적으로 "VIDEO"(대소문자 무시)이고 videos[]/cards[]
         어디에서든 유효한 video URL을 찾을 수 있으면 → VIDEO(카드가 몇 개든 상관없다 — 영상
         광고를 cards 배열로 감싸 내려주는 케이스, 예: ad_archive_id=1411948807546506).
      2. `snapshot.videos`가 실제로 존재하고 유효한 video URL이 있으면 → VIDEO
         (display_format 신호가 없거나 다른 값이어도).
      3. `snapshot.cards`가 정확히 1개이고 그 카드에 video URL이 있으면 → VIDEO(Apify가 단일
         영상 광고를 카드 1개짜리 배열로 감싸는 케이스 — 카드가 1개뿐이면 "여러 장 넘겨보는
         캐러셀"이라는 의미 자체가 없다).
      4. 그 외 전부 → IMAGE. 캐러셀(카드 2개 이상)은 첫 카드의 대표 이미지 1장만 쓴다 — 카드
         안에 영상이 섞여 있어도(카드 하나가 영상이라도) VIDEO로 승격하지 않는다. display_format이
         명시적으로 VIDEO를 주장해도 실제 video URL을 하나도 찾지 못하면(메타데이터 불일치) 이
         fallback으로 내려간다.

    이 저장소에는 여전히 APIFY_TOKEN/.env가 없어(2026-09-23 재확인) 실제 Apify raw item을 직접
    조회하지 못했다 — `_log_media_classification()`이 남기는 운영 로그로 이 규칙을 계속
    재검증해야 한다.
    """
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []
    normalized_format = _normalize_display_format(_raw_display_format(item))

    video_url = _find_video_url(videos, cards)

    if normalized_format == "VIDEO" and video_url:
        return AdFormat.VIDEO, _find_video_thumbnail(videos, cards, images), video_url, "display_format_video"

    if videos and video_url:
        return AdFormat.VIDEO, _find_video_thumbnail(videos, cards, images), video_url, "videos_present"

    if len(cards) == 1:
        single_video_url = _find_video_url([], cards)
        if single_video_url:
            return (
                AdFormat.VIDEO,
                _find_video_thumbnail([], cards, images),
                single_video_url,
                "single_card_video",
            )

    return AdFormat.IMAGE, _find_first_image(cards, images), None, "image_default"


def classify_and_extract_media(item: dict, ad_archive_id: str | None = None) -> tuple[AdFormat, str | None, str | None]:
    """Apify 아이템의 snapshot에서 포맷(IMAGE/VIDEO), 대표 썸네일 URL, 대표 영상 URL(VIDEO
    전용)을 판별한다. 판별 규칙은 _classify_media()를 참고. 매 호출마다 진단 로그를 남긴다 —
    ad_archive_id는 parse_items()가 이미 알고 있는 값을 그대로 넘겨받는다(없으면 item 자체에서
    재시도)."""
    fmt, image_url, video_url, reason = _classify_media(item)
    _log_media_classification(item, ad_archive_id, fmt, reason)
    return fmt, image_url, video_url


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
        fmt, image_url, video_url = classify_and_extract_media(item, ad_archive_id=ad_archive_id)
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
                video_url=video_url,
            )
        )
    return parsed


def fetch_live_ads(ad_library_url: str, page_id: str, max_ads: int = 30) -> list[RawAdItem]:
    """경쟁사 Meta Ad Library URL 기준으로 현재 라이브 소재 전체를 수집한다.

    G-01: stage별(actor start / running·wait / dataset download / parse) 시간을 structured
    log로 남긴다 — 로직/반환값은 이전과 동일하다."""
    with stage_timer("apify_actor_start", page_id=page_id):
        run = run_actor(ad_library_url, max_ads=max_ads)
    with stage_timer("apify_actor_wait", page_id=page_id, run_id=run["id"]):
        finished = wait_run(run["id"])
    if finished["status"] != "SUCCEEDED":
        raise ApifyRunError(f"Apify run ended with status={finished['status']}")
    with stage_timer("dataset_download", page_id=page_id):
        items = get_dataset_items(finished["defaultDatasetId"])
    with stage_timer("raw_ad_parse", page_id=page_id, item_count=len(items)):
        parsed = parse_items(items, page_id)
    return parsed


def extract_page_id(ad_library_url: str) -> str | None:
    """Ad Library URL의 view_all_page_id 쿼리 파라미터를 추출한다."""
    from urllib.parse import parse_qs, urlparse

    query = parse_qs(urlparse(ad_library_url).query)
    values = query.get("view_all_page_id")
    return values[0] if values else None

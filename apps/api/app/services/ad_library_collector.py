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
from app.schemas import AdFormat, MediaItem, RawAdItem
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


# 2026-09-22 개정 — 실제 재현 사례(ad_archive_id=1411948807546506, Meta Ad Library에서는 VIDEO로
# 보이지만 ADCatch는 CAROUSEL로 저장)를 계기로, "cards가 2개 이상이면 무조건 CAROUSEL"이라는 구조
# 전용 규칙을 raw display_format을 evidence로 삼는 규칙으로 재설계했다. 이 저장소에는 여전히
# APIFY_TOKEN이 없어(2026-09 재확인) 이 광고의 실제 raw item을 직접 조회하지는 못했다 — 아래 값
# 집합(VIDEO/CAROUSEL/MULTI_IMAGES/DPA/DCO)은 사용자가 이번 요청에서 직접 지정한 분류 규칙이며,
# 실제 Apify 응답의 display_format 필드명/값과 정확히 일치하는지는 운영 로그(§ 진단 로깅)로
# 재검증이 필요하다.
_VIDEO_DISPLAY_FORMATS = frozenset({"VIDEO"})
_CAROUSEL_DISPLAY_FORMATS = frozenset({"CAROUSEL", "MULTI_IMAGES", "DPA"})
_DCO_DISPLAY_FORMATS = frozenset({"DCO"})


def _log_media_classification(
    item: dict,
    ad_archive_id: str | None,
    classified_format: AdFormat,
    classification_reason: str,
) -> None:
    """§15 — 실제 운영 raw structure를 확인하기 위한 진단 로그. URL 전체는 남기지 않고
    count/format/근거만 기록한다(민감 정보 최소화)."""
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []

    card_video_count = sum(1 for c in cards if c.get("video_hd_url") or c.get("video_sd_url"))
    unique_video_urls: set[str] = set()
    for v in videos:
        u = v.get("video_hd_url") or v.get("video_sd_url")
        if u:
            unique_video_urls.add(u)
    for c in cards:
        u = c.get("video_hd_url") or c.get("video_sd_url")
        if u:
            unique_video_urls.add(u)

    media_classification_logger.info(
        "stage=media_classification ad_archive_id=%s raw_display_format=%s videos_count=%d cards_count=%d "
        "images_count=%d card_video_count=%d unique_video_url_count=%d classified_format=%s classification_reason=%s",
        ad_archive_id or item.get("ad_archive_id") or "unknown",
        _raw_display_format(item) or "absent",
        len(videos),
        len(cards),
        len(images),
        card_video_count,
        len(unique_video_urls),
        classified_format.value,
        classification_reason,
    )


def _media_preview_url(node: dict) -> str | None:
    """video/card 노드의 대표 poster 이미지 후보를 우선순위대로 찾는다:
    video_preview_image_url → original_image_url → resized_image_url. 카드 영상의 poster가
    video_preview_image_url에만 있는 경우가 있어(원본 코드가 놓치던 지점), 영상 URL은 있는데
    image_url이 None이 되는 케이스를 여기서 최대한 제거한다."""
    return node.get("video_preview_image_url") or node.get("original_image_url") or node.get("resized_image_url") or None


def _dedup_media_items(items: list[MediaItem]) -> list[MediaItem]:
    """빈 URL을 제거하고, 동일 url이 여러 번 나오면(예: 같은 영상이 videos/cards 양쪽에 중복 등장)
    첫 번째만 남긴다 — 순서는 유지한다."""
    seen: set[str] = set()
    out: list[MediaItem] = []
    for m in items:
        if not m.url or m.url in seen:
            continue
        seen.add(m.url)
        out.append(m)
    return out


def _first_video_asset(videos: list[dict], cards: list[dict]) -> tuple[str | None, str | None]:
    """videos[] 다음 cards[]의 순서로 첫 번째 유효한 video URL과 그 poster를 찾는다."""
    for v in videos:
        url = v.get("video_hd_url") or v.get("video_sd_url")
        if url:
            return url, _media_preview_url(v)
    for c in cards:
        url = c.get("video_hd_url") or c.get("video_sd_url")
        if url:
            return url, _media_preview_url(c)
    return None, None


def _videos_to_media_items(videos: list[dict]) -> list[MediaItem]:
    items = [
        MediaItem(type="video", url=(v.get("video_hd_url") or v.get("video_sd_url") or ""), preview_url=_media_preview_url(v))
        for v in videos
        if v.get("video_hd_url") or v.get("video_sd_url")
    ]
    return _dedup_media_items(items)


def _card_media_item(card: dict) -> MediaItem | None:
    video_url = card.get("video_hd_url") or card.get("video_sd_url")
    if video_url:
        return MediaItem(type="video", url=video_url, preview_url=_media_preview_url(card))
    image_url = card.get("original_image_url") or card.get("resized_image_url")
    if image_url:
        return MediaItem(type="image", url=image_url)
    return None


def _cards_to_media_items(cards: list[dict]) -> list[MediaItem]:
    items = [m for m in (_card_media_item(c) for c in cards) if m is not None]
    return _dedup_media_items(items)


def _images_to_media_items(images: list[dict]) -> list[MediaItem]:
    items = [
        MediaItem(type="image", url=(img.get("original_image_url") or img.get("resized_image_url") or ""))
        for img in images
        if img.get("original_image_url") or img.get("resized_image_url")
    ]
    return _dedup_media_items(items)


def _representative_image_from_cards(cards: list[dict]) -> str | None:
    for card in cards:
        preview = _media_preview_url(card)
        if preview:
            return preview
    return None


def _representative_image_from_images(images: list[dict]) -> str | None:
    for img in images:
        url = img.get("original_image_url") or img.get("resized_image_url")
        if url:
            return url
    return None


def _classify_media_by_structure(
    videos: list[dict], images: list[dict], cards: list[dict]
) -> tuple[AdFormat, str | None, str | None, list[MediaItem], str]:
    """display_format 신호가 없거나(또는 있어도 실제 구조와 맞지 않아 신뢰할 수 없거나) 알 수
    없는 값일 때 쓰는 구조 기반 fallback. 2026-09 이전 규칙과 동일한 판정을 유지한다:
      - `snapshot.videos`에 유효 video URL이 있으면 → VIDEO.
      - `snapshot.cards`가 정확히 1개이고 video URL이 있으면 → VIDEO(Apify가 단일 영상 광고를
        카드 1개짜리 배열로 감싸는 케이스).
      - 그 외 cards가 있으면(2개 이상, 또는 1개인데 영상이 없으면 아래에서 IMAGE) → CAROUSEL.
      - `snapshot.images`만 있으면 → IMAGE.
    """
    if videos:
        video_url, preview = _first_video_asset(videos, [])
        return AdFormat.VIDEO, preview, video_url, _videos_to_media_items(videos), "videos_present"

    if len(cards) == 1:
        card = cards[0]
        card_video_url = card.get("video_hd_url") or card.get("video_sd_url")
        card_image_url = _media_preview_url(card)
        if card_video_url:
            media_items = _dedup_media_items([MediaItem(type="video", url=card_video_url, preview_url=card_image_url)])
            return AdFormat.VIDEO, card_image_url, card_video_url, media_items, "single_card_video"
        if card_image_url:
            return AdFormat.IMAGE, card_image_url, None, [MediaItem(type="image", url=card_image_url)], "single_card_image"
        return AdFormat.IMAGE, None, None, [], "single_card_empty"

    if cards:
        return (
            AdFormat.CAROUSEL,
            _representative_image_from_cards(cards),
            None,
            _cards_to_media_items(cards),
            "multi_cards_fallback",
        )

    if images:
        return (
            AdFormat.IMAGE,
            _representative_image_from_images(images),
            None,
            _images_to_media_items(images),
            "images_present",
        )

    return AdFormat.IMAGE, None, None, [], "no_media"


def _classify_media(item: dict) -> tuple[AdFormat, str | None, str | None, list[MediaItem], str]:
    """classify_and_extract_media()의 순수 판별 로직. classification_reason(진단 로그용)을
    5번째 값으로 함께 반환한다.

    **format 결정 규칙 (2026-09-22 개정 — raw display_format을 우선 evidence로 사용)**:
    실제 재현 사례(ad_archive_id=1411948807546506)에서 Meta Ad Library는 VIDEO로 보여주는데
    ADCatch는 "cards가 2개 이상이면 무조건 CAROUSEL"이라는 구조 전용 규칙 때문에 CAROUSEL로
    저장하고 있었다. 이 규칙을 폐기하고 아래 우선순위로 재설계했다:

      1. `_raw_display_format()`이 명시적으로 "VIDEO"(대소문자 무시)이고 videos[]/cards[]
         어디에서든 유효한 video URL을 하나 이상 찾을 수 있으면 → VIDEO. cards가 몇 개든 상관없다
         (이 케이스가 바로 1411948807546506류 — 영상 광고를 cards 배열로 감싸 내려주는 경우).
         유효한 video URL을 찾지 못하면(메타데이터 불일치) 아래 구조 기반 fallback으로 내려간다.
      2. `_raw_display_format()`이 "DCO"이면 CAROUSEL과 동일시하지 않는다 — DCO의 cards는 실제
         슬라이드가 아니라 dynamic creative variant일 수 있다. video asset이 있으면 대표
         format=VIDEO, 첫 유효 video asset을 대표 video_url로 사용한다. video asset이 전혀
         없으면 대표 format=IMAGE. 어느 쪽이든 원본 variant 구조는 media_items에 그대로 보존한다.
      3. `_raw_display_format()`이 "CAROUSEL"/"MULTI_IMAGES"/"DPA" 중 하나이고 실제로 cards가
         2개 이상 있으면(=진짜 여러 장 구조) → CAROUSEL로 유지. cards가 2개 미만이면(구조가
         claim과 맞지 않음) 아래 fallback으로 내려간다.
      4. display_format이 없거나 위 어느 값에도 해당하지 않으면(알 수 없는 값 포함) →
         `_classify_media_by_structure()`의 기존 fallback 규칙을 그대로 쓴다.

    이 저장소에는 여전히 APIFY_TOKEN/.env가 없어(2026-09-22 재확인) 1411948807546506의 실제 raw
    item을 직접 조회하지 못했다 — 위 VIDEO/CAROUSEL/MULTI_IMAGES/DPA/DCO 값 집합은 이번 요청에서
    사용자가 직접 지정한 분류 규칙이며, 실제 Apify 응답 필드명/값과 정확히 일치하는지는
    `_log_media_classification()`이 남기는 운영 로그로 재검증이 필요하다.
    """
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []
    normalized_format = _normalize_display_format(_raw_display_format(item))

    if normalized_format in _VIDEO_DISPLAY_FORMATS:
        video_url, preview = _first_video_asset(videos, cards)
        if video_url:
            media_items = _dedup_media_items(_videos_to_media_items(videos) + _cards_to_media_items(cards))
            if not media_items:
                media_items = [MediaItem(type="video", url=video_url, preview_url=preview)]
            return AdFormat.VIDEO, preview, video_url, media_items, "display_format_video"
        # display_format이 VIDEO를 주장하지만 videos/cards 어디에도 유효한 URL이 없다 — 메타데이터
        # 불일치이므로 강제 판정하지 않고 구조 기반 fallback으로 내려간다.

    elif normalized_format in _DCO_DISPLAY_FORMATS:
        video_url, preview = _first_video_asset(videos, cards)
        media_items = _dedup_media_items(_videos_to_media_items(videos) + _cards_to_media_items(cards))
        if video_url:
            return AdFormat.VIDEO, preview, video_url, media_items, "dco_video_asset"
        representative = _representative_image_from_cards(cards) or _representative_image_from_images(images)
        if not media_items and images:
            media_items = _images_to_media_items(images)
        return AdFormat.IMAGE, representative, None, media_items, "dco_image_only"

    elif normalized_format in _CAROUSEL_DISPLAY_FORMATS and len(cards) >= 2:
        return (
            AdFormat.CAROUSEL,
            _representative_image_from_cards(cards),
            None,
            _cards_to_media_items(cards),
            "display_format_carousel",
        )

    return _classify_media_by_structure(videos, images, cards)


def classify_and_extract_media(
    item: dict, ad_archive_id: str | None = None
) -> tuple[AdFormat, str | None, str | None, list[MediaItem]]:
    """Apify 아이템의 snapshot에서 포맷(IMAGE/VIDEO/CAROUSEL), 대표 썸네일 URL, 대표 영상 URL,
    미디어 원본 구조(media_items)를 판별한다. 판별 규칙은 _classify_media()를 참고. 매 호출마다
    진단 로그(§15)를 남긴다 — ad_archive_id는 parse_items()가 이미 알고 있는 값을 그대로
    넘겨받는다(없으면 item 자체에서 재시도)."""
    fmt, image_url, video_url, media_items, reason = _classify_media(item)
    _log_media_classification(item, ad_archive_id, fmt, reason)
    return fmt, image_url, video_url, media_items


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
        fmt, image_url, video_url, media_items = classify_and_extract_media(item, ad_archive_id=ad_archive_id)
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
                media_items=media_items,
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

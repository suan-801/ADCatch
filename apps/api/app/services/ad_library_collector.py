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
    snapshot 아래에 내려주는지 확인한다. 2026-09 기준 이 저장소는 실제 Apify raw response
    샘플이나 APIFY_TOKEN이 없어(§14/§16) 이 필드가 실제로 존재하는지, 존재한다면 어떤 값들을
    갖는지 검증하지 못했다 — 그래서 이 값을 아직 분류 규칙에 반영하지 않고, 진단 로그(§15)에만
    실어서 실제 운영 데이터로 확인할 수 있게 해둔다."""
    snap = item.get("snapshot") or {}
    for key in ("display_format", "displayFormat"):
        value = item.get(key) or snap.get(key)
        if value:
            return str(value)
    return None


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


def _classify_media(item: dict) -> tuple[AdFormat, str | None, str | None, list[MediaItem], str]:
    """classify_and_extract_media()의 순수 판별 로직. classification_reason(진단 로그용, §15)을
    5번째 값으로 함께 반환한다.

    reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py::classify_and_extract()
    의 검증된 로직(videos 전체 순회, video_hd_url 우선 SD fallback, 카드 내부 영상 처리)을
    이식했다. 다만 이 저장소에는 실제 Apify raw response 샘플이나 APIFY_TOKEN이 없어(2026-09
    확인) 라이브 재검증은 하지 못했다 — reference 로직을 그대로 신뢰해 이식했고, 실제 운영
    데이터로 재검증이 필요하다(구현 보고서의 "남은 제한사항" 참고).

    **format 결정 규칙 (2026-09 개정 — 카드가 2개 이상일 때만 CAROUSEL로 고정)**:
      A. `snapshot.videos`에 실제 영상 URL이 1개 이상 있으면 → VIDEO.
      B. `snapshot.cards`가 있고 **카드가 2개 이상**이면 → CAROUSEL. 카드 중 일부/전부가 영상이어도
         포맷은 바뀌지 않는다("카드 내부 영상"은 media_items의 개별 항목 type에만 반영된다).
      C. `snapshot.cards`가 **정확히 1개**이고 그 카드에 `video_hd_url`/`video_sd_url`이 있으면 →
         VIDEO로 취급한다. Apify가 단일 영상 광고를 카드 1개짜리 `cards` 배열로 감싸 반환하는
         케이스가 있어(§3-1), 카드 개수가 1개뿐일 때는 "여러 장을 넘겨보는 캐러셀"이라는 실제
         의미가 없으므로 VIDEO로 판정하는 것이 raw semantics에 더 맞는다.
      D. 카드가 1개이고 영상 URL이 없으면(순수 이미지 카드 1장) → IMAGE.
      E. `snapshot.images`만 있으면 → IMAGE.

    **raw display_format 신호는 아직 이 규칙에 반영하지 않는다(§16)** — 실제 Apify 응답에 이
    필드가 존재하는지, 값이 무엇인지 검증할 방법이 이 환경에 없어서 무리하게 우선순위 규칙을
    추가하지 않았다. `_log_media_classification()`이 매 분류마다 raw_display_format을 함께
    기록하므로, 운영 로그를 확인한 뒤 다음 라운드에서 근거를 갖고 규칙을 정할 수 있다.
    """
    snap = item.get("snapshot") or {}
    videos = snap.get("videos") or []
    images = snap.get("images") or []
    cards = snap.get("cards") or []

    if videos:
        first_video = videos[0]
        video_url = first_video.get("video_hd_url") or first_video.get("video_sd_url")
        # 하위 호환: 갤러리 대표 썸네일은 기존과 동일하게 video_preview_image_url을 그대로 쓴다.
        representative_image_url = first_video.get("video_preview_image_url")
        media_items = [
            MediaItem(
                type="video",
                url=(v.get("video_hd_url") or v.get("video_sd_url") or ""),
                preview_url=v.get("video_preview_image_url"),
            )
            for v in videos
            if v.get("video_hd_url") or v.get("video_sd_url")
        ]
        return AdFormat.VIDEO, representative_image_url, video_url, media_items, "videos_present"

    if len(cards) == 1:
        # 규칙 C/D — 카드가 1개뿐이면 "여러 장을 넘겨보는 캐러셀"의 실제 의미가 없다. Apify가
        # 단일 영상 광고를 cards=[{video_hd_url: ...}] 형태 1개짜리 배열로 반환하는 케이스를
        # VIDEO로 정확히 잡아내기 위한 분기(카드가 2개 이상일 때만 CAROUSEL로 고정 — 규칙 B).
        card = cards[0]
        card_video_url = card.get("video_hd_url") or card.get("video_sd_url")
        card_image_url = card.get("original_image_url") or card.get("resized_image_url")
        if card_video_url:
            media_items = [MediaItem(type="video", url=card_video_url, preview_url=card_image_url)]
            return AdFormat.VIDEO, card_image_url, card_video_url, media_items, "single_card_video"
        if card_image_url:
            return (
                AdFormat.IMAGE,
                card_image_url,
                None,
                [MediaItem(type="image", url=card_image_url)],
                "single_card_image",
            )
        return AdFormat.IMAGE, None, None, [], "single_card_empty"

    if cards:
        media_items = []
        representative_image_url: str | None = None
        for card in cards:
            card_video_url = card.get("video_hd_url") or card.get("video_sd_url")
            card_image_url = card.get("original_image_url") or card.get("resized_image_url")
            if card_video_url:
                media_items.append(MediaItem(type="video", url=card_video_url, preview_url=card_image_url))
                # 대표 썸네일 후보 — 첫 카드가 영상이라 자체 이미지가 없어도(포스터가 없는 경우)
                # 갤러리 썸네일이 비지 않도록, 영상 카드의 preview가 있으면 그것도 후보로 삼는다.
                if representative_image_url is None and card_image_url:
                    representative_image_url = card_image_url
            elif card_image_url:
                media_items.append(MediaItem(type="image", url=card_image_url))
                if representative_image_url is None:
                    representative_image_url = card_image_url
        # CAROUSEL은 카드 안에 영상이 섞여 있어도(카드 2개 이상일 때) 포맷이 절대 VIDEO로 바뀌지
        # 않는다. 카드 내부 영상의 다운로드/keyframe 캐싱은 이번 범위 밖(§8) — Drawer는 preview_url을
        # 그대로 보여준다.
        return AdFormat.CAROUSEL, representative_image_url, None, media_items, "multi_cards_fallback"

    if images:
        media_items = [
            MediaItem(type="image", url=(img.get("original_image_url") or img.get("resized_image_url") or ""))
            for img in images
            if img.get("original_image_url") or img.get("resized_image_url")
        ]
        img = images[0]
        representative_image_url = img.get("original_image_url") or img.get("resized_image_url")
        return AdFormat.IMAGE, representative_image_url, None, media_items, "images_present"

    return AdFormat.IMAGE, None, None, [], "no_media"


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

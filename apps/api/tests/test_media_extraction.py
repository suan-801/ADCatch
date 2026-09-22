"""VIDEO/CAROUSEL 판별 — classify_and_extract_media(). reference/marketing-os-course의 검증된
구조(videos[].video_hd_url/video_sd_url, cards[].video_hd_url, images[].original_image_url 등)를
그대로 반영한 fixture dict로 검증한다."""

from app.schemas import AdFormat
from app.services.ad_library_collector import (
    _classify_media,
    _log_media_classification,
    _raw_display_format,
    classify_and_extract_media,
)


def test_videos_only_uses_hd_over_sd_and_keeps_preview_as_representative_image():
    item = {
        "snapshot": {
            "videos": [
                {
                    "video_hd_url": "https://cdn/hd.mp4",
                    "video_sd_url": "https://cdn/sd.mp4",
                    "video_preview_image_url": "https://cdn/preview.jpg",
                }
            ]
        }
    }
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert image_url == "https://cdn/preview.jpg"
    assert video_url == "https://cdn/hd.mp4"
    assert len(media_items) == 1
    assert media_items[0].type == "video"
    assert media_items[0].url == "https://cdn/hd.mp4"


def test_video_falls_back_to_sd_when_hd_missing():
    item = {"snapshot": {"videos": [{"video_sd_url": "https://cdn/sd.mp4"}]}}
    _, _, video_url, media_items = classify_and_extract_media(item)
    assert video_url == "https://cdn/sd.mp4"
    assert media_items[0].url == "https://cdn/sd.mp4"


def test_cards_image_only_carousel():
    item = {
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/c1.jpg"},
                {"original_image_url": "https://cdn/c2.jpg"},
            ]
        }
    }
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.CAROUSEL
    assert image_url == "https://cdn/c1.jpg"
    assert video_url is None
    assert [m.type for m in media_items] == ["image", "image"]


def test_cards_with_video_card_stays_carousel_not_video():
    """핵심 회귀 지점(사용자 리뷰 #7): 카드 중 일부가 영상이어도 format은 절대 VIDEO로
    바뀌지 않는다 — 오직 media_items의 개별 항목 type에만 반영된다."""
    item = {
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/c1.jpg"},
                {
                    "video_hd_url": "https://cdn/c2.mp4",
                    "original_image_url": "https://cdn/c2-poster.jpg",
                },
                {"original_image_url": "https://cdn/c3.jpg"},
            ]
        }
    }
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.CAROUSEL  # VIDEO로 승격되지 않음
    assert video_url is None  # 최상위 video_url은 CAROUSEL에서 항상 NULL
    assert [m.type for m in media_items] == ["image", "video", "image"]
    assert media_items[1].url == "https://cdn/c2.mp4"
    assert media_items[1].preview_url == "https://cdn/c2-poster.jpg"  # 카드 포스터 보존


def test_first_card_is_video_without_poster_still_yields_representative_image():
    """첫 카드가 영상이고 자체 포스터도 없으면, 뒤 카드의 이미지를 대표 썸네일로 채택해
    갤러리 썸네일이 비지 않게 한다(기존 cards[0]만 보던 로직보다 견고함)."""
    item = {
        "snapshot": {
            "cards": [
                {"video_hd_url": "https://cdn/c1.mp4"},
                {"original_image_url": "https://cdn/c2.jpg"},
            ]
        }
    }
    fmt, image_url, _, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.CAROUSEL
    assert image_url == "https://cdn/c2.jpg"
    assert media_items[0].preview_url is None


def test_images_only():
    item = {"snapshot": {"images": [{"original_image_url": "https://cdn/i1.jpg"}]}}
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/i1.jpg"
    assert video_url is None
    assert [m.type for m in media_items] == ["image"]


def test_no_media_at_all():
    fmt, image_url, video_url, media_items = classify_and_extract_media({"snapshot": {}})
    assert fmt == AdFormat.IMAGE
    assert image_url is None
    assert video_url is None
    assert media_items == []


def test_resized_image_url_fallback_when_original_missing():
    item = {"snapshot": {"images": [{"resized_image_url": "https://cdn/resized.jpg"}]}}
    _, image_url, _, _ = classify_and_extract_media(item)
    assert image_url == "https://cdn/resized.jpg"


# ── 2026-09 사용자 피드백: 단일 카드 영상 오분류(카드가 1개뿐이면 CAROUSEL이 아니라 VIDEO) ─────


def test_single_card_with_video_hd_url_is_video_not_carousel():
    """Apify가 단일 영상 광고를 cards=[{video_hd_url: ...}] 형태 1개짜리 배열로 반환하는 실제
    케이스 — 카드가 1개뿐이면 "여러 장 넘겨보는 캐러셀"의 의미가 없으므로 VIDEO로 판정한다."""
    item = {
        "snapshot": {
            "cards": [
                {
                    "video_hd_url": "https://cdn/single.mp4",
                    "original_image_url": "https://cdn/single-poster.jpg",
                }
            ]
        }
    }
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert video_url == "https://cdn/single.mp4"
    assert image_url == "https://cdn/single-poster.jpg"
    assert [m.type for m in media_items] == ["video"]


def test_single_card_with_video_sd_url_only_is_video():
    item = {"snapshot": {"cards": [{"video_sd_url": "https://cdn/single-sd.mp4"}]}}
    fmt, _, video_url, _ = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert video_url == "https://cdn/single-sd.mp4"


def test_single_card_image_only_is_image_not_carousel():
    """카드가 1개이고 영상이 없으면(순수 이미지 카드 1장) IMAGE로 취급한다."""
    item = {"snapshot": {"cards": [{"original_image_url": "https://cdn/single.jpg"}]}}
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/single.jpg"
    assert video_url is None
    assert [m.type for m in media_items] == ["image"]


def test_single_card_with_no_media_at_all():
    item = {"snapshot": {"cards": [{}]}}
    fmt, image_url, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url is None
    assert media_items == []


def test_raw_display_format_reads_top_level_or_snapshot_key():
    assert _raw_display_format({"display_format": "VIDEO"}) == "VIDEO"
    assert _raw_display_format({"displayFormat": "DCO"}) == "DCO"
    assert _raw_display_format({"snapshot": {"display_format": "CAROUSEL"}}) == "CAROUSEL"
    assert _raw_display_format({"snapshot": {"displayFormat": "DPA"}}) == "DPA"
    assert _raw_display_format({}) is None
    assert _raw_display_format({"snapshot": {}}) is None


def test_classify_media_returns_reason_for_each_branch():
    """§15 진단 로그가 쓰는 classification_reason이 각 분기마다 올바르게 붙는지 확인한다."""
    _, _, _, _, reason = _classify_media({"snapshot": {"videos": [{"video_hd_url": "https://cdn/x.mp4"}]}})
    assert reason == "videos_present"

    _, _, _, _, reason = _classify_media({"snapshot": {"cards": [{"video_hd_url": "https://cdn/x.mp4"}]}})
    assert reason == "single_card_video"

    _, _, _, _, reason = _classify_media({"snapshot": {"cards": [{"original_image_url": "https://cdn/x.jpg"}]}})
    assert reason == "single_card_image"

    _, _, _, _, reason = _classify_media({"snapshot": {"cards": [{}]}})
    assert reason == "single_card_empty"

    _, _, _, _, reason = _classify_media(
        {"snapshot": {"cards": [{"original_image_url": "https://cdn/a.jpg"}, {"original_image_url": "https://cdn/b.jpg"}]}}
    )
    assert reason == "multi_cards_fallback"

    _, _, _, _, reason = _classify_media({"snapshot": {"images": [{"original_image_url": "https://cdn/x.jpg"}]}})
    assert reason == "images_present"

    _, _, _, _, reason = _classify_media({"snapshot": {}})
    assert reason == "no_media"


def test_diagnostic_logging_does_not_raise_and_reports_raw_display_format(caplog):
    """§15/§16 회귀: raw_display_format이 VIDEO를 명확히 가리키는데도 카드가 2개 이상이면 현재
    구현은 여전히 CAROUSEL로 판정한다 — display_format 우선순위 규칙은 실제 운영 raw로 검증하기
    전까지 아직 반영하지 않았다(§16). 진단 로그가 이 불일치를 그대로 드러내는지 확인한다."""
    import logging

    item = {
        "display_format": "VIDEO",
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/a.jpg"},
                {"original_image_url": "https://cdn/b.jpg"},
            ]
        },
    }
    with caplog.at_level(logging.INFO, logger="adcatcher.media_classification"):
        fmt, _, _, _ = classify_and_extract_media(item, ad_archive_id="AD123")

    assert fmt == AdFormat.CAROUSEL  # 아직 raw_display_format을 규칙에 반영하지 않음(§16 미해결)
    log_text = caplog.text
    assert "ad_archive_id=AD123" in log_text
    assert "raw_display_format=VIDEO" in log_text
    assert "classified_format=CAROUSEL" in log_text
    assert "classification_reason=multi_cards_fallback" in log_text


def test_diagnostic_logging_reports_absent_when_no_display_format(caplog):
    import logging

    item = {"snapshot": {"images": [{"original_image_url": "https://cdn/x.jpg"}]}}
    with caplog.at_level(logging.INFO, logger="adcatcher.media_classification"):
        classify_and_extract_media(item)
    assert "raw_display_format=absent" in caplog.text


def test_log_media_classification_helper_does_not_raise_on_minimal_item():
    _log_media_classification({}, None, AdFormat.IMAGE, "no_media")


def test_multi_card_all_video_still_carousel():
    """카드가 2개 이상이면 전부 영상이어도 여전히 CAROUSEL이다(규칙 B) — 단일 카드일 때만
    VIDEO로 취급하는 규칙 C와 구분."""
    item = {
        "snapshot": {
            "cards": [
                {"video_hd_url": "https://cdn/c1.mp4"},
                {"video_hd_url": "https://cdn/c2.mp4"},
            ]
        }
    }
    fmt, _, video_url, media_items = classify_and_extract_media(item)
    assert fmt == AdFormat.CAROUSEL
    assert video_url is None
    assert [m.type for m in media_items] == ["video", "video"]

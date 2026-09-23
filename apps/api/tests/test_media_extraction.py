"""IMAGE/VIDEO 2분류 — classify_and_extract_media() (2026-09-23 재설계).

VIDEO는 아주 명확한 경우에만 VIDEO로 판정하고, 그 외 전부(카드가 여러 장인 캐러셀, 카드 안에
영상이 섞여 있는 경우 포함) IMAGE로 취급한다. CAROUSEL이라는 반환값 자체가 없다."""

from app.schemas import AdFormat
from app.services.ad_library_collector import (
    _classify_media,
    _log_media_classification,
    _raw_display_format,
    classify_and_extract_media,
)


def test_videos_present_is_video_uses_hd_over_sd_and_video_preview_as_thumbnail():
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
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert image_url == "https://cdn/preview.jpg"
    assert video_url == "https://cdn/hd.mp4"


def test_video_falls_back_to_sd_when_hd_missing():
    item = {"snapshot": {"videos": [{"video_sd_url": "https://cdn/sd.mp4"}]}}
    _, _, video_url = classify_and_extract_media(item)
    assert video_url == "https://cdn/sd.mp4"


def test_multi_card_images_only_is_image_using_first_card():
    """카드가 여러 장인 캐러셀은 VIDEO로 승격되지 않고 첫 카드 이미지 1장만 대표로 쓴다."""
    item = {
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/c1.jpg"},
                {"original_image_url": "https://cdn/c2.jpg"},
            ]
        }
    }
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/c1.jpg"
    assert video_url is None


def test_multi_card_with_one_video_card_stays_image_not_promoted_to_video():
    """핵심 단순화 규칙: 카드가 2개 이상이면 그중 하나가 영상이어도 VIDEO로 승격하지 않는다 —
    display_format이 명확히 VIDEO를 주장하지 않는 한 항상 IMAGE(첫 카드 대표 이미지)."""
    item = {
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/c1.jpg"},
                {"video_hd_url": "https://cdn/c2.mp4", "video_preview_image_url": "https://cdn/c2-poster.jpg"},
                {"original_image_url": "https://cdn/c3.jpg"},
            ]
        }
    }
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/c1.jpg"  # 첫 카드 이미지(영상 카드가 아님)
    assert video_url is None


def test_multi_card_all_video_still_image_without_explicit_display_format():
    """카드가 전부 영상이어도(2개 이상) display_format이 명확히 VIDEO라고 하지 않으면 IMAGE다 —
    첫 카드에 이미지가 없으면(영상만 있으면) 대표 이미지가 없을 수 있다."""
    item = {
        "snapshot": {
            "cards": [
                {"video_hd_url": "https://cdn/c1.mp4"},
                {"video_hd_url": "https://cdn/c2.mp4"},
            ]
        }
    }
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert video_url is None
    assert image_url is None  # 카드에 original_image_url/resized_image_url이 전혀 없음


def test_images_only():
    item = {"snapshot": {"images": [{"original_image_url": "https://cdn/i1.jpg"}]}}
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/i1.jpg"
    assert video_url is None


def test_no_media_at_all():
    fmt, image_url, video_url = classify_and_extract_media({"snapshot": {}})
    assert fmt == AdFormat.IMAGE
    assert image_url is None
    assert video_url is None


def test_resized_image_url_fallback_when_original_missing():
    item = {"snapshot": {"images": [{"resized_image_url": "https://cdn/resized.jpg"}]}}
    _, image_url, _ = classify_and_extract_media(item)
    assert image_url == "https://cdn/resized.jpg"


def test_cards_fall_back_to_snapshot_images_when_no_card_image():
    """카드가 2장 이상이고 전부 영상뿐이라 카드 자체에서 이미지를 못 찾으면(카드가 1개일 때만
    VIDEO로 승격되므로 이 케이스는 IMAGE로 떨어진다) snapshot.images의 대체 이미지를 쓴다."""
    item = {
        "snapshot": {
            "cards": [{"video_hd_url": "https://cdn/c1.mp4"}, {"video_hd_url": "https://cdn/c2.mp4"}],
            "images": [{"original_image_url": "https://cdn/fallback.jpg"}],
        }
    }
    fmt, image_url, _ = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/fallback.jpg"


# ── 단일 카드 영상 — Apify가 단일 영상 광고를 카드 1개짜리 배열로 감싸는 케이스 ──────────────


def test_single_card_with_video_hd_url_is_video_not_image():
    item = {
        "snapshot": {
            "cards": [
                {
                    "video_hd_url": "https://cdn/single.mp4",
                    "video_preview_image_url": "https://cdn/single-poster.jpg",
                }
            ]
        }
    }
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert video_url == "https://cdn/single.mp4"
    assert image_url == "https://cdn/single-poster.jpg"


def test_single_card_with_video_sd_url_only_is_video():
    item = {"snapshot": {"cards": [{"video_sd_url": "https://cdn/single-sd.mp4"}]}}
    fmt, _, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.VIDEO
    assert video_url == "https://cdn/single-sd.mp4"


def test_single_card_image_only_is_image():
    item = {"snapshot": {"cards": [{"original_image_url": "https://cdn/single.jpg"}]}}
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/single.jpg"
    assert video_url is None


def test_single_card_with_no_media_at_all():
    item = {"snapshot": {"cards": [{}]}}
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url is None
    assert video_url is None


# ── raw display_format — 명시적 VIDEO 신호가 우선 evidence ──────────────────────────────────
# 재현 사례: ad_archive_id=1411948807546506 — Meta Ad Library에서는 VIDEO로 보이지만 예전
# "cards 2개 이상이면 무조건 CAROUSEL" 규칙은 이런 구조를 CAROUSEL로 오분류했었다. 실제 signed
# URL은 fixture에 넣지 않고 가짜 cdn URL만 사용한다.


def test_display_format_video_wins_over_multi_card_structure():
    """핵심 회귀 — 1411948807546506류 재현: display_format=VIDEO이고 cards가 2개 이상이어도 그
    중 한 카드에 유효한 video URL이 있으면 VIDEO로 판정한다(카드 개수와 무관)."""
    item = {
        "ad_archive_id": "1411948807546506",
        "display_format": "video",  # 대소문자 정규화 검증 겸함
        "snapshot": {
            "cards": [
                {
                    "video_hd_url": "https://cdn.example.com/1411948807546506_hd.mp4",
                    "video_preview_image_url": "https://cdn.example.com/1411948807546506_poster.jpg",
                },
                {"original_image_url": "https://cdn.example.com/1411948807546506_variant2.jpg"},
            ]
        },
    }
    fmt, image_url, video_url = classify_and_extract_media(item, ad_archive_id="1411948807546506")
    assert fmt == AdFormat.VIDEO
    assert video_url == "https://cdn.example.com/1411948807546506_hd.mp4"
    assert image_url == "https://cdn.example.com/1411948807546506_poster.jpg"


def test_display_format_video_with_no_valid_video_url_falls_back_to_image():
    """display_format=VIDEO를 주장하지만 videos/cards 어디에도 실제 video URL이 없으면(메타데이터
    불일치) 강제로 VIDEO 판정하지 않고 IMAGE fallback을 쓴다."""
    item = {"display_format": "VIDEO", "snapshot": {"images": [{"original_image_url": "https://cdn/x.jpg"}]}}
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/x.jpg"
    assert video_url is None


def test_display_format_video_with_multi_image_cards_and_no_video_asset_stays_image():
    """display_format=VIDEO라고 해도 카드에 영상이 전혀 없으면(순수 이미지 캐러셀) IMAGE로 남는다."""
    item = {
        "display_format": "VIDEO",
        "snapshot": {
            "cards": [
                {"original_image_url": "https://cdn/a.jpg"},
                {"original_image_url": "https://cdn/b.jpg"},
            ]
        },
    }
    fmt, image_url, video_url = classify_and_extract_media(item)
    assert fmt == AdFormat.IMAGE
    assert image_url == "https://cdn/a.jpg"
    assert video_url is None


def test_display_format_carousel_value_does_not_matter_still_image():
    """display_format이 CAROUSEL/MULTI_IMAGES/DPA/DCO 등 무엇을 주장하든 이제는 분류에 영향을
    주지 않는다 — VIDEO 신호(정확히 VIDEO + 유효 video URL)가 없으면 항상 구조 기반 규칙만 쓴다."""
    for raw_format in ("CAROUSEL", "MULTI_IMAGES", "DPA", "DCO", "unknown_value"):
        item = {
            "display_format": raw_format,
            "snapshot": {
                "cards": [
                    {"original_image_url": "https://cdn/a.jpg"},
                    {"original_image_url": "https://cdn/b.jpg"},
                ]
            },
        }
        fmt, image_url, video_url = classify_and_extract_media(item)
        assert fmt == AdFormat.IMAGE, raw_format
        assert image_url == "https://cdn/a.jpg", raw_format
        assert video_url is None, raw_format


def test_raw_display_format_reads_top_level_or_snapshot_key():
    assert _raw_display_format({"display_format": "VIDEO"}) == "VIDEO"
    assert _raw_display_format({"displayFormat": "DCO"}) == "DCO"
    assert _raw_display_format({"snapshot": {"display_format": "CAROUSEL"}}) == "CAROUSEL"
    assert _raw_display_format({"snapshot": {"displayFormat": "DPA"}}) == "DPA"
    assert _raw_display_format({}) is None
    assert _raw_display_format({"snapshot": {}}) is None


def test_classify_media_returns_reason_for_each_branch():
    _, _, _, reason = _classify_media({"snapshot": {"videos": [{"video_hd_url": "https://cdn/x.mp4"}]}})
    assert reason == "videos_present"

    _, _, _, reason = _classify_media({"snapshot": {"cards": [{"video_hd_url": "https://cdn/x.mp4"}]}})
    assert reason == "single_card_video"

    _, _, _, reason = _classify_media({"snapshot": {"cards": [{"original_image_url": "https://cdn/x.jpg"}]}})
    assert reason == "image_default"

    _, _, _, reason = _classify_media({"snapshot": {}})
    assert reason == "image_default"

    _, _, _, reason = _classify_media(
        {"display_format": "VIDEO", "snapshot": {"cards": [{"video_hd_url": "https://cdn/x.mp4"}, {"video_hd_url": "https://cdn/y.mp4"}]}}
    )
    assert reason == "display_format_video"


def test_diagnostic_logging_does_not_raise_and_reports_fields(caplog):
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
        fmt, _, _ = classify_and_extract_media(item, ad_archive_id="AD123")

    assert fmt == AdFormat.IMAGE
    log_text = caplog.text
    assert "ad_archive_id=AD123" in log_text
    assert "raw_display_format=VIDEO" in log_text
    assert "classified_format=IMAGE" in log_text
    assert "classification_reason=image_default" in log_text


def test_diagnostic_logging_reports_absent_when_no_display_format(caplog):
    import logging

    item = {"snapshot": {"images": [{"original_image_url": "https://cdn/x.jpg"}]}}
    with caplog.at_level(logging.INFO, logger="adcatcher.media_classification"):
        classify_and_extract_media(item)
    assert "raw_display_format=absent" in caplog.text


def test_log_media_classification_helper_does_not_raise_on_minimal_item():
    _log_media_classification({}, None, AdFormat.IMAGE, "image_default")

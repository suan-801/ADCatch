"""VIDEO/CAROUSEL 판별 — classify_and_extract_media(). reference/marketing-os-course의 검증된
구조(videos[].video_hd_url/video_sd_url, cards[].video_hd_url, images[].original_image_url 등)를
그대로 반영한 fixture dict로 검증한다."""

from app.schemas import AdFormat
from app.services.ad_library_collector import classify_and_extract_media


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

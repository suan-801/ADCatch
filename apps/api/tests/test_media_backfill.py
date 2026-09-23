"""기존(재발견된) 소재의 format/video_url/image_url 갱신 — 2026-09-23 단순화.

ffmpeg keyframe 파이프라인과 CAROUSEL을 제거하면서 ad_sync.py의 재발견 분기도 함께 단순화했다:
format이 실제로 바뀌면 최신 판정을 반영하고, video_url은 format이 VIDEO인 동안 최신 값으로
갱신하며(재생하지 않으므로 만료 걱정이 없다), image_url은 비어있거나 format이 교정될 때만
backfill한다. keyframe_* 컬럼은 더 이상 이 로직에서 참조하지 않는다(legacy)."""

from datetime import date

from app.models import Ad
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _run(db, competitor, run_date: date):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


def test_existing_video_ad_backfills_video_url_on_rediscovery(db, competitor):
    # 과거(이 필드가 생기기 전) 수집된 것처럼, video_url 없이 VIDEO ad를 직접 만든다.
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="A1",
        format="VIDEO",
        image_url="https://cdn/preview.jpg",
        status="ACTIVE",
        video_url=None,
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/a1.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/a1.mp4"


# ── ads.video_url은 영구 캐시가 아니라 참고용 원본 URL이다 — fresh 수집 때마다 최신값으로 갱신 ──


def test_video_url_refreshes_to_latest_source_on_every_fresh_collection(db, competitor):
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="A1",
        format="VIDEO",
        image_url="https://cdn/preview.jpg",
        status="ACTIVE",
        video_url="https://cdn/already-cached.mp4",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/different-url.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/different-url.mp4"


def test_video_url_unchanged_when_fresh_item_has_no_video_url(db, competitor):
    """fresh item에 video_url이 없으면(일시적 누락) 기존 값을 그대로 둔다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/preview.jpg", status="ACTIVE",
        video_url="https://cdn/existing.mp4",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO, image_url="https://cdn/preview.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/existing.mp4"


def test_video_corrected_to_image_clears_video_url(db, competitor):
    """VIDEO → IMAGE로 실제 교정되면 더 이상 대표 영상이 아니므로 video_url을 비운다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/poster.jpg", status="ACTIVE", video_url="https://cdn/old.mp4",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE,
        image_url="https://cdn/card1.jpg",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "IMAGE"
    assert ad.video_url is None


# ── image_url backfill (cache-only, Gemini 없음) ────────────────────────────────────


def test_missing_image_url_backfilled_via_cache_only_thumbnail(db, competitor, monkeypatch):
    """기존 image_url=None인 소재는 fresh raw item에서 대표 preview image를 얻으면 backfill된다.
    Gemini 태깅 없이 캐싱만 하는 media.cache_thumbnail_only()가 쓰였는지 확인한다."""
    from app.services import ad_sync

    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="IMAGE",
        image_url=None, status="ACTIVE",
    )
    db.add(ad)
    db.commit()

    calls = []

    def _fake_cache_thumbnail_only(competitor_id, ad_archive_id, image_url):
        calls.append((ad_archive_id, image_url))
        return f"https://storage.example.com/{ad_archive_id}.jpg"

    monkeypatch.setattr(ad_sync.media, "cache_thumbnail_only", _fake_cache_thumbnail_only)

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/fresh.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=True)

    db.refresh(ad)
    assert calls == [("A1", "https://cdn/fresh.jpg")]
    assert ad.image_url == "https://storage.example.com/A1.jpg"


def test_missing_image_url_falls_back_to_raw_url_when_tag_visual_false(db, competitor, monkeypatch):
    """tag_visual=False(기존 다수 테스트가 쓰는 값)면 캐싱 스레드풀 자체가 돌지 않아 네트워크
    호출은 없다 — 다만 video_url이 이미 tag_visual과 무관하게 backfill되는 것과 동일한 원칙으로,
    image_url도 raw item 값 그대로는 채워진다(캐싱된 Storage URL이 아니라 원본 Meta CDN URL이라는
    차이만 있음)."""
    from app.services import ad_sync

    ad = Ad(competitor_id=competitor.id, ad_archive_id="A1", format="IMAGE", image_url=None, status="ACTIVE")
    db.add(ad)
    db.commit()

    called = []
    monkeypatch.setattr(ad_sync.media, "cache_thumbnail_only", lambda *a, **k: called.append(1))

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/fresh.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert called == []  # 캐싱 함수 자체는 호출되지 않음(네트워크 없음)
    assert ad.image_url == "https://cdn/fresh.jpg"  # 그래도 raw URL로는 backfill됨


def test_existing_image_url_never_overwritten_by_backfill(db, competitor, monkeypatch):
    from app.services import ad_sync

    ad = Ad(competitor_id=competitor.id, ad_archive_id="A1", format="IMAGE", image_url="https://cdn/already-set.jpg", status="ACTIVE")
    db.add(ad)
    db.commit()

    monkeypatch.setattr(ad_sync.media, "cache_thumbnail_only", lambda *a, **k: "https://storage.example.com/should-not-be-used.jpg")

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/fresh.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=True)

    db.refresh(ad)
    assert ad.image_url == "https://cdn/already-set.jpg"


def test_new_video_ad_stores_video_url(db, competitor):
    item = RawAdItem(
        ad_archive_id="V1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/v1.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    ad = db.query(Ad).filter_by(ad_archive_id="V1").one()
    assert ad.format == "VIDEO"
    assert ad.video_url == "https://cdn/v1.mp4"


def test_new_image_ad_has_no_video_url(db, competitor):
    item = RawAdItem(ad_archive_id="I1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/i1.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    ad = db.query(Ad).filter_by(ad_archive_id="I1").one()
    assert ad.format == "IMAGE"
    assert ad.video_url is None


# ── format 교정 — 과거에 잘못 판정된 format을 최신 raw 판정으로 바로잡는다 ──────────────────


def test_existing_image_corrected_to_video_when_raw_evidence_is_clear(db, competitor):
    """예전(3-way 시절) CAROUSEL로 저장됐던 광고는 이번 마이그레이션으로 이미 IMAGE로 내려가
    있다 — 다음 재수집에서 명확한 VIDEO 증거가 있으면 VIDEO로 교정되는지 확인한다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="IMAGE",
        image_url="https://cdn/old-poster.jpg", status="ACTIVE", video_url=None,
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/new-poster.jpg", video_url="https://cdn/new.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "VIDEO"
    assert ad.video_url == "https://cdn/new.mp4"


def test_format_not_overwritten_when_raw_evidence_is_empty(db, competitor):
    """raw media 정보가 비어 있거나 불확실한 경우(예: 일시적으로 빈 snapshot) 기존 format을
    임의로 덮어쓰지 않는다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/poster.jpg", status="ACTIVE", video_url="https://cdn/existing.mp4",
    )
    db.add(ad)
    db.commit()

    # snapshot이 비어 사실상 아무 media evidence도 없는 raw item(=classify_and_extract_media가
    # AdFormat.IMAGE, None, None을 반환하는 경우와 동일한 모양).
    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url=None)
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "VIDEO"  # 덮어쓰이지 않음
    assert ad.video_url == "https://cdn/existing.mp4"


# ── 재현 사례 end-to-end: ad_archive_id=1411948807546506류 광고의 IMAGE→VIDEO 자동 교정 ──────
# 실제 signed URL은 쓰지 않고 가짜 cdn URL만 사용한다.


def test_reproduction_case_ad_corrected_to_video_end_to_end(db, competitor):
    """예전 3-way 분류 시절 CAROUSEL(현재는 마이그레이션으로 IMAGE)로 저장됐던 광고가, 다음
    수집에서 raw item에 display_format=VIDEO + 유효한 카드 video URL이 있으면(=1411948807546506류
    구조) VIDEO로 자동 교정되고 대표 썸네일도 채워지는지 parse_items()부터 synchronize_ad_status()
    까지 전체 경로로 검증한다."""
    from app.services.ad_library_collector import parse_items

    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="1411948807546506",
        format="IMAGE",
        image_url="https://cdn.example.com/old-carousel-thumb.jpg",
        status="ACTIVE",
        video_url=None,
    )
    db.add(ad)
    db.commit()

    raw_items = [
        {
            "ad_archive_id": "1411948807546506",
            "display_format": "VIDEO",
            "snapshot": {
                "page_name": "테스트 브랜드",
                "cards": [
                    {
                        "video_hd_url": "https://cdn.example.com/1411948807546506_hd.mp4",
                        "video_preview_image_url": "https://cdn.example.com/1411948807546506_poster.jpg",
                    },
                    {"original_image_url": "https://cdn.example.com/1411948807546506_variant2.jpg"},
                ],
            },
        }
    ]
    fresh_items = parse_items(raw_items, page_id=competitor.page_id)
    assert fresh_items[0].format == AdFormat.VIDEO  # parse 단계에서부터 VIDEO로 판정됨

    synchronize_ad_status(db, competitor.id, fresh_items, _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "VIDEO"
    assert ad.video_url == "https://cdn.example.com/1411948807546506_hd.mp4"
    assert ad.image_url == "https://cdn.example.com/1411948807546506_poster.jpg"

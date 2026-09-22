"""기존(이 컬럼들이 생기기 전에 수집된) VIDEO 소재가 재발견될 때 video_url/media_items/
keyframe_status가 자연스럽게 채워지는지 — 별도 백필 스크립트 없이 다음 수집 사이클에서 처리된다."""

from datetime import date

from app.models import Ad
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _run(db, competitor, run_date: date):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


def test_existing_video_ad_backfills_video_url_on_rediscovery(db, competitor):
    # 과거(이 필드가 생기기 전) 수집된 것처럼, video_url/media_items 없이 VIDEO ad를 직접 만든다.
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="A1",
        format="VIDEO",
        image_url="https://cdn/preview.jpg",
        status="ACTIVE",
        video_url=None,
        media_items=None,
        keyframe_status="NOT_APPLICABLE",
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
    assert ad.keyframe_status == "PENDING"  # 이제 pending 배치 대상이 됨


# ── 2026-09-22 개정: ads.video_url은 영구 캐시가 아니라 Meta signed CDN source URL이다 ─────────
# 예전 규칙("한 번 채워지면 절대 덮어쓰지 않는다")은 signed URL이 만료되는 실제 운영 상황을
# 반영하지 못했다 — fresh 수집 때마다 최신 source URL로 refresh하되, 이미 성공적으로 캐싱된
# keyframe만큼은 source URL이 바뀌어도 삭제/재생성하지 않는다.


def test_video_url_refreshes_to_latest_source_but_keeps_successful_keyframes(db, competitor):
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="A1",
        format="VIDEO",
        image_url="https://cdn/preview.jpg",
        status="ACTIVE",
        video_url="https://cdn/already-cached.mp4",
        keyframe_status="SUCCESS",
        keyframe_urls=["https://cdn/kf1.jpg"],
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/different-url.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/different-url.mp4"  # signed URL은 최신 값으로 refresh됨
    assert ad.keyframe_status == "SUCCESS"  # 이미 성공한 keyframe은 source URL 변경으로 건드리지 않음
    assert ad.keyframe_retry_count == 0
    assert ad.keyframe_urls == ["https://cdn/kf1.jpg"]  # 삭제/재생성 없음


def test_video_url_unchanged_when_fresh_item_has_no_video_url(db, competitor):
    """fresh item에 video_url이 없으면(일시적 누락) 기존 값을 그대로 둔다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/preview.jpg", status="ACTIVE",
        video_url="https://cdn/existing.mp4", keyframe_status="SUCCESS", keyframe_urls=["https://cdn/kf1.jpg"],
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO, image_url="https://cdn/preview.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/existing.mp4"


def test_failed_keyframe_reactivates_when_fresh_video_url_differs(db, competitor):
    """FAILED로 확정된 keyframe도, signed video_url이 최신 수집에서 실제로 달라졌으면(만료된 URL
    때문에 실패를 반복했을 수 있음) PENDING으로 되돌려 재시도 가능하게 만든다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/preview.jpg", status="ACTIVE",
        video_url="https://cdn/old-expired.mp4", keyframe_status="FAILED", keyframe_retry_count=3,
        keyframe_error="영상 다운로드 실패",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/fresh.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.video_url == "https://cdn/fresh.mp4"
    assert ad.keyframe_status == "PENDING"
    assert ad.keyframe_retry_count == 0
    assert ad.keyframe_error is None


def test_failed_keyframe_not_reset_when_video_url_unchanged(db, competitor):
    """video_url이 실제로 바뀌지 않았으면 FAILED는 그대로 유지한다(불필요한 재시도 남발 방지)."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/preview.jpg", status="ACTIVE",
        video_url="https://cdn/same.mp4", keyframe_status="FAILED", keyframe_retry_count=3,
        keyframe_error="영상 다운로드 실패",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/same.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.keyframe_status == "FAILED"
    assert ad.keyframe_retry_count == 3


def test_pending_keyframe_url_change_resets_retry_count(db, competitor):
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/preview.jpg", status="ACTIVE",
        video_url="https://cdn/old.mp4", keyframe_status="PENDING", keyframe_retry_count=2,
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/fresh.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.keyframe_status == "PENDING"
    assert ad.keyframe_retry_count == 0


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
    호출은 없다 — 다만 video_url/media_items가 이미 tag_visual과 무관하게 backfill되는 것과
    동일한 원칙으로, image_url도 raw item 값 그대로는 채워진다(캐싱된 Storage URL이 아니라 원본
    Meta CDN URL이라는 차이만 있음)."""
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


# ── 재현 사례 end-to-end: ad_archive_id=1411948807546506류 광고의 CAROUSEL→VIDEO 자동 교정 ──────
# 실제 signed URL은 쓰지 않고 가짜 cdn URL만 사용한다.


def test_reproduction_case_carousel_ad_corrected_to_video_end_to_end(db, competitor):
    """기존 규칙("cards 2개 이상이면 무조건 CAROUSEL")으로 CAROUSEL 저장된 광고가, 다음
    수집에서 raw item에 display_format=VIDEO + 유효한 카드 video URL이 있으면(=1411948807546506류
    구조) VIDEO로 자동 교정되고 대표 썸네일도 채워지는지 parse_items()부터 synchronize_ad_status()
    까지 전체 경로로 검증한다."""
    from app.services.ad_library_collector import parse_items

    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id="1411948807546506",
        format="CAROUSEL",
        image_url="https://cdn.example.com/old-carousel-thumb.jpg",
        status="ACTIVE",
        video_url=None,
        media_items=[{"type": "image", "url": "https://cdn.example.com/old-carousel-thumb.jpg"}],
        keyframe_status="NOT_APPLICABLE",
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
    assert ad.keyframe_status == "PENDING"  # keyframe pending batch 대상에 새로 들어감
    assert ad.keyframe_retry_count == 0


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


def test_image_format_ad_never_gets_keyframe_pending(db, competitor):
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="IMAGE",
        image_url="https://cdn/i1.jpg", status="ACTIVE", keyframe_status="NOT_APPLICABLE",
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/i1.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.keyframe_status == "NOT_APPLICABLE"


def test_new_video_ad_starts_keyframe_pending_immediately(db, competitor):
    """신규 VIDEO 소재는 생성 시점부터 keyframe_status=PENDING으로 시작한다 — Core Collection
    안에서 ffmpeg를 호출하지 않고 pending 배치가 나중에 처리한다."""
    item = RawAdItem(
        ad_archive_id="V1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/preview.jpg", video_url="https://cdn/v1.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    ad = db.query(Ad).filter_by(ad_archive_id="V1").one()
    assert ad.video_url == "https://cdn/v1.mp4"
    assert ad.keyframe_status == "PENDING"


def test_new_image_ad_keyframe_status_is_not_applicable(db, competitor):
    item = RawAdItem(ad_archive_id="I1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://cdn/i1.jpg")
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    ad = db.query(Ad).filter_by(ad_archive_id="I1").one()
    assert ad.keyframe_status == "NOT_APPLICABLE"


# ── 2026-09 사용자 피드백: 기존 잘못 저장된 format 교정 ──────────────────────────
# 과거엔 video_url/media_items만 backfill하고 existing.format은 절대 교정하지 않았다 — 그 결과
# 과거 CAROUSEL로 저장된 광고가 새 parser에서 VIDEO로 올바르게 재판정돼도 DB에는 계속 CAROUSEL로
# 남아 keyframe pending batch 대상에서 영구히 제외되는 실제 결손이 있었다.


def test_existing_carousel_corrected_to_video_when_raw_evidence_is_clear(db, competitor):
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="CAROUSEL",
        image_url="https://cdn/old-poster.jpg", status="ACTIVE",
        video_url=None, media_items=[{"type": "image", "url": "https://cdn/old-poster.jpg"}],
        keyframe_status="NOT_APPLICABLE",
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
    assert ad.keyframe_status == "PENDING"  # keyframe batch 대상에 새로 들어감
    assert ad.keyframe_retry_count == 0


def test_format_correction_does_not_reset_already_successful_keyframes(db, competitor):
    """이미 SUCCESS인 keyframe은 format이 재확인(VIDEO→VIDEO)돼도 불필요하게 초기화되지 않는다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/poster.jpg", status="ACTIVE",
        video_url="https://cdn/existing.mp4", keyframe_status="SUCCESS",
        keyframe_urls=["https://cdn/kf1.jpg", "https://cdn/kf2.jpg"],
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.VIDEO,
        image_url="https://cdn/poster.jpg", video_url="https://cdn/existing.mp4",
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.keyframe_status == "SUCCESS"
    assert ad.keyframe_urls == ["https://cdn/kf1.jpg", "https://cdn/kf2.jpg"]


def test_existing_video_corrected_to_carousel_does_not_delete_keyframe_urls(db, competitor):
    """VIDEO → CAROUSEL 교정도 fresh evidence가 명확하면 처리하되, 이미 업로드된 keyframe 파일에
    대한 destructive storage cleanup은 하지 않는다(keyframe_urls 배열 자체는 보존, 상태만
    NOT_APPLICABLE로 되돌림)."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/poster.jpg", status="ACTIVE",
        video_url="https://cdn/old.mp4", keyframe_status="SUCCESS",
        keyframe_urls=["https://cdn/kf1.jpg"],
    )
    db.add(ad)
    db.commit()

    item = RawAdItem(
        ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.CAROUSEL,
        image_url="https://cdn/card1.jpg",
        media_items=[
            {"type": "image", "url": "https://cdn/card1.jpg"},
            {"type": "image", "url": "https://cdn/card2.jpg"},
        ],
    )
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "CAROUSEL"
    assert ad.keyframe_status == "NOT_APPLICABLE"
    assert ad.keyframe_urls == ["https://cdn/kf1.jpg"]  # destructive cleanup 없음 — 배열 보존


def test_format_not_overwritten_when_raw_evidence_is_empty(db, competitor):
    """raw media 정보가 비어 있거나 불확실한 경우(예: 일시적으로 빈 snapshot) 기존 format을
    임의로 덮어쓰지 않는다."""
    ad = Ad(
        competitor_id=competitor.id, ad_archive_id="A1", format="VIDEO",
        image_url="https://cdn/poster.jpg", status="ACTIVE",
        video_url="https://cdn/existing.mp4", keyframe_status="SUCCESS",
        keyframe_urls=["https://cdn/kf1.jpg"],
    )
    db.add(ad)
    db.commit()

    # snapshot이 비어 사실상 아무 media evidence도 없는 raw item(=classify_and_extract_media가
    # AdFormat.IMAGE, None, None, []을 반환하는 경우와 동일한 모양).
    item = RawAdItem(ad_archive_id="A1", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url=None)
    synchronize_ad_status(db, competitor.id, [item], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)

    db.refresh(ad)
    assert ad.format == "VIDEO"  # 덮어쓰이지 않음
    assert ad.video_url == "https://cdn/existing.mp4"
    assert ad.keyframe_status == "SUCCESS"

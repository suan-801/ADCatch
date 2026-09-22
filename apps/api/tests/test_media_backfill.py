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


def test_backfill_never_overwrites_already_cached_video_url(db, competitor):
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
    assert ad.video_url == "https://cdn/already-cached.mp4"  # 덮어쓰지 않음
    assert ad.keyframe_status == "SUCCESS"  # 이미 성공한 keyframe 상태도 유지
    assert ad.keyframe_urls == ["https://cdn/kf1.jpg"]


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

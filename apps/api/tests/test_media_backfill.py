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

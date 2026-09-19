"""기존 NEW/ACTIVE/INACTIVE 판정, 생존일수, 14일 아카이빙 로직이
Daily Ad Change History 도입 이후에도 그대로 동작하는지 확인 (브리핑 §47 회귀 테스트)."""

from app.config import settings
from app.models import Ad
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def test_sync_result_contract_unchanged(db, competitor):
    result = synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], collection_history.start_collection_run(db, competitor.id), tag_visual=False
    )
    assert result.competitor_id == competitor.id
    assert result.new_ads == 2
    assert result.reactivated_or_kept_active == 0
    assert result.newly_inactive == 0
    assert result.newly_archived == 0

    result2 = synchronize_ad_status(
        db, competitor.id, [_raw("A")], collection_history.start_collection_run(db, competitor.id), tag_visual=False
    )
    assert result2.new_ads == 0
    assert result2.reactivated_or_kept_active == 1  # A
    assert result2.newly_inactive == 1  # B


def test_archiving_after_consecutive_inactive_days(db, competitor):
    synchronize_ad_status(
        db, competitor.id, [_raw("A")], collection_history.start_collection_run(db, competitor.id), tag_visual=False
    )

    for _ in range(settings.archive_after_inactive_days):
        synchronize_ad_status(
            db, competitor.id, [], collection_history.start_collection_run(db, competitor.id), tag_visual=False
        )

    ad = db.query(Ad).filter(Ad.ad_archive_id == "A").one()
    assert ad.is_archived is True
    assert ad.consecutive_inactive_days == settings.archive_after_inactive_days


# Brand Model Simplification (P0-18/P0-19): is_own_brand=True로 등록된 브랜드도 더 이상
# 제외하지 않는다 — apps/api/tests/test_brand_simplification.py 에서 포함 여부를 직접 검증한다.

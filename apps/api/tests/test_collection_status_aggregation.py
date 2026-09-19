"""P0-15 — 여러 브랜드의 오늘자 수집 상태를 프로젝트 단위로 뭉갤 때, "하나라도 SUCCESS면
전체 SUCCESS"가 아니라 정확한 규칙(전부 같아야 그 상태, 섞이면 PARTIAL)을 따르는지 검증."""

from app.models import Competitor
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def _add_competitor(db, project_id: str, page_id: str) -> Competitor:
    c = Competitor(
        project_id=project_id,
        name=f"브랜드-{page_id}",
        ad_library_url=f"https://www.facebook.com/ads/library/?view_all_page_id={page_id}",
        page_id=page_id,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


# TEST 21 — 2 SUCCESS + 1 FAILED → project status PARTIAL
def test_mixed_success_and_failed_is_project_partial(db, competitor):
    c2 = _add_competitor(db, competitor.project_id, "2")
    c3 = _add_competitor(db, competitor.project_id, "3")

    run1 = collection_history.start_collection_run(db, competitor.id)
    synchronize_ad_status(db, competitor.id, [_raw("A")], run1, tag_visual=False)

    run2 = collection_history.start_collection_run(db, c2.id, run_date=run1.run_date)
    synchronize_ad_status(db, c2.id, [_raw("B")], run2, tag_visual=False)

    failed_run = collection_history.start_collection_run(db, c3.id, run_date=run1.run_date)
    collection_history.fail_collection_run(db, failed_run, "apify timeout")

    changes = collection_history.get_ad_changes(db, competitor.project_id, run1.run_date, None)
    assert changes.collection_status.value == "PARTIAL"
    assert changes.collection_summary.success == 2
    assert changes.collection_summary.failed == 1
    assert changes.collection_summary.partial == 0
    assert changes.collection_summary.no_record == 0


# TEST 22 — 전부 SUCCESS → project status SUCCESS
def test_all_success_is_project_success(db, competitor):
    c2 = _add_competitor(db, competitor.project_id, "2")

    run1 = collection_history.start_collection_run(db, competitor.id)
    synchronize_ad_status(db, competitor.id, [_raw("A")], run1, tag_visual=False)
    run2 = collection_history.start_collection_run(db, c2.id, run_date=run1.run_date)
    synchronize_ad_status(db, c2.id, [_raw("B")], run2, tag_visual=False)

    changes = collection_history.get_ad_changes(db, competitor.project_id, run1.run_date, None)
    assert changes.collection_status.value == "SUCCESS"
    assert changes.collection_summary.success == 2


# TEST 23 — 전부 FAILED → project status FAILED
def test_all_failed_is_project_failed(db, competitor):
    c2 = _add_competitor(db, competitor.project_id, "2")

    run1 = collection_history.start_collection_run(db, competitor.id)
    collection_history.fail_collection_run(db, run1, "boom")
    run2 = collection_history.start_collection_run(db, c2.id, run_date=run1.run_date)
    collection_history.fail_collection_run(db, run2, "boom")

    changes = collection_history.get_ad_changes(db, competitor.project_id, run1.run_date, None)
    assert changes.collection_status.value == "FAILED"
    assert changes.collection_summary.failed == 2


# 기록 자체가 없는 브랜드가 섞이면(SUCCESS + NO_RECORD) PARTIAL로 집계된다
def test_success_and_no_record_is_project_partial(db, competitor):
    _add_competitor(db, competitor.project_id, "2")  # 이 브랜드는 오늘 수집 기록이 없음

    run1 = collection_history.start_collection_run(db, competitor.id)
    synchronize_ad_status(db, competitor.id, [_raw("A")], run1, tag_visual=False)

    changes = collection_history.get_ad_changes(db, competitor.project_id, run1.run_date, None)
    assert changes.collection_status.value == "PARTIAL"
    assert changes.collection_summary.success == 1
    assert changes.collection_summary.no_record == 1

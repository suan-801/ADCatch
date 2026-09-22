"""§6 기간(주간) 조회 API — get_ad_changes_range(). 단일 날짜 get_ad_changes()는 건드리지
않았으므로 회귀 테스트도 함께 포함한다."""

from datetime import date

from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str, **kwargs) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE, **kwargs)


def _run(db, competitor, run_date: date):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


def test_range_is_inclusive_of_both_endpoints(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)  # baseline
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 14)), tag_visual=False
    )  # STARTED on 9/14
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A"), _raw("B")], _run(db, competitor, date(2026, 9, 20)), tag_visual=False
    )  # STARTED B on 9/20

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 14), date(2026, 9, 20), None)
    started_archive_ids = {ad.ad_archive_id for ad in result.started_ads}
    assert started_archive_ids == {"A", "B"}  # 양끝 날짜 모두 포함

    narrower = collection_history.get_ad_changes_range(
        db, competitor.project_id, date(2026, 9, 15), date(2026, 9, 19), None
    )
    assert narrower.started_ads == []  # 경계 밖 날짜만 있는 범위는 빈 결과


def test_started_reactivated_stopped_baseline_counted_correctly(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)  # baseline: A
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor, date(2026, 9, 2)), tag_visual=False)  # A stopped
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 3)), tag_visual=False)  # A reactivated
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor, date(2026, 9, 4)), tag_visual=False
    )  # B started

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 4), None)
    assert result.baseline_discovered_count == 1
    assert result.summary.stopped == 1
    assert result.summary.reactivated == 1
    assert result.summary.started == 1


def test_competitor_filter_scopes_to_single_competitor(db, competitor):
    from app.models import Competitor

    other = Competitor(
        project_id=competitor.project_id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=2", page_id="2",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 5)), tag_visual=False)
    synchronize_ad_status(db, other.id, [_raw("Y")], _run(db, other, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(db, other.id, [_raw("Y"), _raw("X")], _run(db, other, date(2026, 9, 5)), tag_visual=False)

    scoped = collection_history.get_ad_changes_range(
        db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 5), competitor.id
    )
    assert {ad.ad_archive_id for ad in scoped.started_ads} == {"A"}

    all_brands = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 5), None)
    assert {ad.ad_archive_id for ad in all_brands.started_ads} == {"A", "X"}


def test_multiple_events_for_same_ad_preserved_individually(db, competitor):
    """동일 광고가 기간 안에서 여러 이벤트를 가지면(월 STARTED, 수 STOPPED, 금 REACTIVATED)
    event history 의미를 보존한다 — Ad.status 재계산이 아니라 이벤트를 그대로 나열한다."""
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)  # baseline
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 7)), tag_visual=False
    )  # 월: A STARTED
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 9)), tag_visual=False)  # 수: A STOPPED
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 11)), tag_visual=False
    )  # 금: A REACTIVATED

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 7), date(2026, 9, 11), None)
    assert len(result.started_ads) == 1
    assert len(result.stopped_ads) == 1
    assert len(result.reactivated_ads) == 1
    assert result.started_ads[0].event_date == date(2026, 9, 7)
    assert result.stopped_ads[0].event_date == date(2026, 9, 9)
    assert result.reactivated_ads[0].event_date == date(2026, 9, 11)


def test_visual_pattern_dedupes_by_unique_ad(db, competitor):
    """같은 광고가 기간 내 STARTED와 REACTIVATED를 모두 가져도 visual_pattern은 1회만 카운트한다
    (event 기준이 아니라 unique ad 기준) — 사용자 리뷰 #9."""
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 7)), tag_visual=False
    )
    from app.models import Ad

    ad_a = db.query(Ad).filter_by(ad_archive_id="A").one()
    ad_a.visual_type = "PRODUCT"
    db.commit()

    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 9)), tag_visual=False)
    synchronize_ad_status(
        db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor, date(2026, 9, 11)), tag_visual=False
    )

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 7), date(2026, 9, 11), None)
    assert len(result.started_ads) + len(result.reactivated_ads) == 2  # 이벤트는 2건
    assert result.visual_pattern == {"PRODUCT": 1}  # 그러나 unique ad 기준 1건


def test_collection_run_summary_distinguishes_no_attempt_from_failure(db, competitor):
    """자동수집을 켜지 않은 날의 "기록 없음"이 "실패"처럼 보이면 안 된다 — 실제 시도한 run만
    집계하고, dates_with_collection에 시도한 날짜만 포함한다."""
    run1 = collection_history.start_collection_run(db, competitor.id, run_date=date(2026, 9, 1))
    collection_history.complete_collection_run_success(db, run1, fetched_ads_count=1)
    run2 = collection_history.start_collection_run(db, competitor.id, run_date=date(2026, 9, 2))
    collection_history.fail_collection_run(db, run2, "network error")
    db.commit()
    # 9/3~9/5는 아예 시도가 없음.

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 5), None)
    assert result.collection_run_summary.success == 1
    assert result.collection_run_summary.failed == 1
    assert set(result.dates_with_collection) == {date(2026, 9, 1), date(2026, 9, 2)}


def test_empty_project_scope_returns_empty_response(db, competitor):
    import uuid as uuid_module
    from app.models import Project

    empty_project = Project(id=uuid_module.uuid4(), user_id=competitor.project.user_id, name="빈 프로젝트")
    db.add(empty_project)
    db.commit()

    result = collection_history.get_ad_changes_range(db, empty_project.id, date(2026, 9, 1), date(2026, 9, 5), None)
    assert result.summary.started == 0
    assert result.collection_run_summary.success == 0
    assert result.dates_with_collection == []


# ── 회귀: 기존 단일 날짜 get_ad_changes()는 이번 변경으로 전혀 영향받지 않는다 ─────────


def test_single_date_get_ad_changes_unaffected(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    run = _run(db, competitor, date(2026, 9, 5))
    synchronize_ad_status(db, competitor.id, [_raw("Z"), _raw("A")], run, tag_visual=False)

    result = collection_history.get_ad_changes(db, competitor.project_id, date(2026, 9, 5), None)
    assert result.summary.started == 1
    assert result.started_ads[0].ad_archive_id == "A"
    assert result.collection_status.value == "SUCCESS"

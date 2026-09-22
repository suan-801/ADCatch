"""§2/§3/§4 (2026-09) — "선택 기간에 실제로 라이브였던 광고" 기준 집계.

get_alive_ads_in_range()는 AdObservation(성공/부분 수집에서 실제 fetch된 광고에 대해서만 기록되는
직접 관측 데이터)을 근거로 삼는다 — STARTED/REACTIVATED 이벤트가 아니다. visual_pattern/
campaign_mix 둘 다 이 동일한 alive 집합을 분모로 공유한다."""

from datetime import date

from app.models import Ad
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status
from app.services.collection_history import (
    _aggregate_visual_and_campaign_patterns,
    get_alive_ads_in_range,
)
from app.services.campaign_tags import create_campaign_tag


def _raw(archive_id: str, **kwargs) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE, **kwargs)


def _run(db, competitor, run_date: date):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


# ── get_alive_ads_in_range() ────────────────────────────────────────────────


def test_same_ad_observed_seven_days_counted_once(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    for day in range(2, 8):
        synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, day)), tag_visual=False)

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 7))
    assert len(alive) == 1
    assert alive[0].ad_archive_id == "A"


def test_alive_without_started_event_baseline_ad_continuously_observed(db, competitor):
    """baseline에서 발견된 광고는 STARTED 이벤트를 갖지 않는다(BASELINE_DISCOVERED만 생성) — 그래도
    매 수집마다 관측되므로 alive 집합에 포함돼야 한다."""
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)  # baseline
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 5)), tag_visual=False)

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 5), date(2026, 9, 5))
    assert {a.ad_archive_id for a in alive} == {"A"}


def test_alive_without_reactivated_event_ad_never_stopped(db, competitor):
    """한 번도 STOPPED된 적 없는 광고는 REACTIVATED 이벤트도 없다 — 계속 관측되므로 포함돼야 한다."""
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor, date(2026, 9, 3)), tag_visual=False
    )

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 3), date(2026, 9, 3))
    assert {a.ad_archive_id for a in alive} == {"A", "B"}


def test_observations_outside_range_are_excluded(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 30)), tag_visual=False)

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 10), date(2026, 9, 20))
    assert alive == []


def test_competitor_filter_applies_to_alive_ads(db, competitor):
    from app.models import Competitor

    other = Competitor(
        project_id=competitor.project_id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=9", page_id="9",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    synchronize_ad_status(db, other.id, [_raw("Y")], _run(db, other, date(2026, 9, 1)), tag_visual=False)

    alive_scoped = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    assert {a.ad_archive_id for a in alive_scoped} == {"A"}

    alive_all = get_alive_ads_in_range(db, [competitor.id, other.id], date(2026, 9, 1), date(2026, 9, 1))
    assert {a.ad_archive_id for a in alive_all} == {"A", "Y"}


def test_partial_run_observed_ads_are_included(db, competitor):
    """PARTIAL(스냅샷이 잘렸을 수 있는) run이어도, 실제로 fetch되어 관측된 광고는 "그 날 살아
    있었다"는 사실 자체는 유효하므로 alive 집합에 포함한다."""
    run = _run(db, competitor, date(2026, 9, 1))
    synchronize_ad_status(db, competitor.id, [_raw("A")], run, tag_visual=False, snapshot_complete=False)
    assert run.status == "PARTIAL"

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    assert {a.ad_archive_id for a in alive} == {"A"}


def test_failed_run_has_no_observations_and_is_excluded(db, competitor):
    """FAILED run은 애초에 synchronize_ad_status가 호출되지 않으므로(라우터/스케줄러가 fetch
    단계에서 실패를 감지하면 곧바로 fail_collection_run을 호출) AdObservation이 전혀 생성되지
    않는다 — "못 받아온 것"을 "죽었다"로도, "살아있다"로도 추정하지 않는다."""
    run = _run(db, competitor, date(2026, 9, 1))
    collection_history.fail_collection_run(db, run, "apify timeout")

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    assert alive == []


# ── visual_pattern / campaign_mix 집계 (동일 alive 집합 공유) ───────────────────


def _set_visual(db, archive_id: str, visual_type: str | None):
    ad = db.query(Ad).filter_by(ad_archive_id=archive_id).one()
    ad.visual_type = visual_type
    db.commit()


def test_visual_pattern_counts_by_category(db, competitor):
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B"), _raw("C")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False
    )
    _set_visual(db, "A", "PERSON")
    _set_visual(db, "B", "PERSON")
    _set_visual(db, "C", "PRODUCT")

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    visual_pattern, _ = _aggregate_visual_and_campaign_patterns(alive)
    assert visual_pattern == {"PERSON": 2, "PRODUCT": 1}


def test_visual_type_null_is_unanalyzed_not_silently_dropped(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    # visual_type을 세팅하지 않음 — 기본 None.

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    visual_pattern, _ = _aggregate_visual_and_campaign_patterns(alive)
    assert visual_pattern == {"UNANALYZED": 1}


def test_alive_ad_count_matches_visual_pattern_total(db, competitor):
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False
    )
    _set_visual(db, "A", "GRAPHIC")

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 1), None)
    assert result.alive_ad_count == 2
    assert sum(result.visual_pattern.values()) == result.alive_ad_count


def _set_campaign(db, archive_id: str, **kwargs):
    ad = db.query(Ad).filter_by(ad_archive_id=archive_id).one()
    for k, v in kwargs.items():
        setattr(ad, k, v)
    db.commit()


def test_campaign_mix_success_tag_counted_by_tag_id(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    _set_campaign(db, "A", campaign_tag_id=tag.id, campaign_classification_status="SUCCESS")

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    _, campaign_mix = _aggregate_visual_and_campaign_patterns(alive)
    assert campaign_mix == {str(tag.id): 1}


def test_campaign_mix_needs_review_bucket(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False)
    _set_campaign(db, "A", campaign_classification_status="NEEDS_REVIEW")

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    _, campaign_mix = _aggregate_visual_and_campaign_patterns(alive)
    assert campaign_mix == {"NEEDS_REVIEW": 1}


def test_campaign_mix_pending_failed_and_no_tag_are_unclassified(db, competitor):
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B"), _raw("C")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False
    )
    _set_campaign(db, "A", campaign_classification_status="PENDING")
    _set_campaign(db, "B", campaign_classification_status="FAILED")
    # C: campaign_tag_id가 없는데 상태만 SUCCESS인 이례적 케이스도 방어적으로 UNCLASSIFIED 처리.
    _set_campaign(db, "C", campaign_classification_status="SUCCESS", campaign_tag_id=None)

    alive = get_alive_ads_in_range(db, [competitor.id], date(2026, 9, 1), date(2026, 9, 1))
    _, campaign_mix = _aggregate_visual_and_campaign_patterns(alive)
    assert campaign_mix == {"UNCLASSIFIED": 3}


def test_campaign_mix_unique_ad_basis_matches_visual_pattern_denominator(db, competitor):
    """visual_pattern과 campaign_mix는 항상 같은 alive_ads 분모를 공유한다 — 하나는 event 기준,
    다른 하나는 라이브 기준처럼 갈라지지 않는다."""
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor, date(2026, 9, 1)), tag_visual=False
    )
    _set_visual(db, "A", "PERSON")
    _set_campaign(db, "A", campaign_tag_id=tag.id, campaign_classification_status="SUCCESS")

    result = collection_history.get_ad_changes_range(db, competitor.project_id, date(2026, 9, 1), date(2026, 9, 1), None)
    assert sum(result.visual_pattern.values()) == result.alive_ad_count
    assert sum(result.campaign_mix.values()) == result.alive_ad_count

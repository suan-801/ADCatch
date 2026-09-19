"""P0-07/P0-08 — "첫 수집"이 아니라 "첫 COMPLETE SUCCESSFUL SNAPSHOT"이 Baseline이다.

PARTIAL(예: max_ads 상한 도달)로 끝난 첫 수집은 baseline을 확정하지 않는다 — ad row/observation은
저장되지만 어떤 이벤트도 생성되지 않는다. 그 다음 완전한 SUCCESS가 와야 비로소 baseline이 확정된다."""

from app.models import Ad, AdObservation, AdStatusEvent, Competitor
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def _events(db, competitor_id):
    return db.query(AdStatusEvent).filter(AdStatusEvent.competitor_id == competitor_id).all()


def _run(db, competitor):
    return collection_history.start_collection_run(db, competitor.id)


# TEST 9 — 첫 PARTIAL: row/observation은 저장되지만 baseline 미확정, 이벤트 0건
def test_first_partial_does_not_complete_baseline(db, competitor):
    run = _run(db, competitor)
    result = synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], run, tag_visual=False, snapshot_complete=False
    )

    assert run.status == "PARTIAL"
    assert result.new_ads == 2
    assert db.query(Ad).filter(Ad.competitor_id == competitor.id).count() == 2
    assert db.query(AdObservation).filter(AdObservation.competitor_id == competitor.id).count() == 2
    assert _events(db, competitor.id) == []  # BASELINE_DISCOVERED조차 기록되지 않는다

    comp = db.get(Competitor, competitor.id)
    assert comp.baseline_completed_at is None

    changes = collection_history.get_ad_changes(db, competitor.project_id, run.run_date, competitor.id)
    assert changes.summary.started == 0
    assert changes.summary.stopped == 0
    assert changes.baseline_discovered_count == 0


# TEST 10 — 첫 PARTIAL → 그 다음 첫 complete SUCCESS: 이 SUCCESS가 baseline이 되고 STARTED는 0이다
def test_partial_then_complete_success_becomes_baseline(db, competitor):
    partial_run = _run(db, competitor)
    synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B")], partial_run, tag_visual=False, snapshot_complete=False
    )

    success_run = _run(db, competitor)
    result = synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("B"), _raw("C")], success_run, tag_visual=False, snapshot_complete=True
    )

    assert success_run.status == "SUCCESS"
    assert result.is_baseline is True
    assert result.snapshot_complete is True

    comp = db.get(Competitor, competitor.id)
    assert comp.baseline_completed_at is not None

    changes = collection_history.get_ad_changes(db, competitor.project_id, success_run.run_date, competitor.id)
    assert changes.summary.started == 0  # A/B는 기존 row라 STARTED 아님
    assert changes.summary.stopped == 0
    assert changes.baseline_discovered_count == 1  # C는 이 baseline-확정 run에서 처음 발견됨

    # 이후 수집부터는 정상적으로 STARTED/STOPPED가 생성된다
    next_run = _run(db, competitor)
    result2 = synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("B"), _raw("D")], next_run, tag_visual=False)
    assert result2.is_baseline is False
    changes2 = collection_history.get_ad_changes(db, competitor.project_id, next_run.run_date, competitor.id)
    assert changes2.summary.started == 1  # D
    assert changes2.summary.stopped == 1  # C (더 이상 발견되지 않음)


# TEST 11 — Baseline에서 생성된 Ad는 status=ACTIVE이며 Gallery에서 NEW로 표시되지 않는다
def test_baseline_ads_are_active_not_new(db, competitor):
    run = _run(db, competitor)
    synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("B")], run, tag_visual=False)

    ads = db.query(Ad).filter(Ad.competitor_id == competitor.id).all()
    assert all(ad.status == "ACTIVE" for ad in ads)
    assert not any(ad.status == "NEW" for ad in ads)

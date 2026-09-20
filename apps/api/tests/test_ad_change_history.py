"""Daily Ad Change History — 브리핑 PART G(§46) 10개 케이스 검증.

fetch_live_ads()는 호출하지 않는다 (Apify 네트워크 의존 제거). RawAdItem을 직접 구성해
ad_sync.synchronize_ad_status()에 주입하는 방식으로, "collection 성공 시 서버가 실제로
호출하는 것과 동일한 함수"를 그대로 검증한다.
"""

from datetime import date, timedelta

from app.models import Ad, AdStatusEvent
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def _events(db, competitor_id):
    return db.query(AdStatusEvent).filter(AdStatusEvent.competitor_id == competitor_id).all()


def _run(db, competitor, run_date: date | None = None):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


# CASE 1 — 없음 → Ad A 등장 → STARTED (단, 이 경쟁사의 첫 수집이 아닐 때에 한해서 — P0-03)
def test_case1_started(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor), tag_visual=False)  # baseline

    run = _run(db, competitor)
    result = synchronize_ad_status(db, competitor.id, [_raw("Z"), _raw("A")], run, tag_visual=False)

    started = [e for e in _events(db, competitor.id) if e.event_type == "STARTED"]
    assert result.new_ads == 1
    assert len(started) == 1
    assert started[0].previous_status is None
    assert run.status == "SUCCESS"


# CASE 2 — Ad A 계속 존재 → 새 이벤트 없음
def test_case2_no_new_event_when_continuing(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)

    events = _events(db, competitor.id)
    assert len(events) == 1  # 최초 STARTED 1건뿐


# CASE 3 — Ad A 있다가 사라짐 → STOPPED
# (최초 등장 시엔 NEW, 그 다음 재발견되어야 ACTIVE로 전환되는 기존 ad_sync 규칙을 그대로 따르므로
#  "있다가 사라짐"을 제대로 표현하려면 최소 2회 연속 발견 후 사라지는 시나리오여야 한다.)
def test_case3_stopped(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # NEW
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # ACTIVE
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)  # 사라짐

    stopped = [e for e in _events(db, competitor.id) if e.event_type == "STOPPED"]
    assert len(stopped) == 1
    assert stopped[0].previous_status == "ACTIVE"


# CASE 3b — baseline 이후에 등장한 광고가 등장한 첫날 바로 사라져도(=NEW 상태에서 STOPPED)
# 정확히 1건 기록되어야 한다. (baseline 자체에서 발견된 광고는 NEW가 아니라 ACTIVE로 생성되므로
# — P0-09 — "NEW에서 바로 STOPPED"를 재현하려면 baseline 이후에 새로 등장한 광고여야 한다.)
def test_case3b_stopped_directly_from_new(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor), tag_visual=False)  # baseline
    synchronize_ad_status(db, competitor.id, [_raw("Z"), _raw("A")], _run(db, competitor), tag_visual=False)  # A: NEW
    synchronize_ad_status(db, competitor.id, [_raw("Z")], _run(db, competitor), tag_visual=False)  # A 사라짐

    stopped = [e for e in _events(db, competitor.id) if e.event_type == "STOPPED"]
    assert len(stopped) == 1
    assert stopped[0].previous_status == "NEW"


# CASE 4 — 이미 INACTIVE, 다음날도 계속 없음 → STOPPED 추가 생성 금지
def test_case4_no_duplicate_stopped(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)  # STOPPED 1건
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)  # 반복 금지

    stopped = [e for e in _events(db, competitor.id) if e.event_type == "STOPPED"]
    assert len(stopped) == 1


# CASE 5 — STOPPED 이후 다시 등장 → REACTIVATED
def test_case5_reactivated(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)

    reactivated = [e for e in _events(db, competitor.id) if e.event_type == "REACTIVATED"]
    assert len(reactivated) == 1
    assert reactivated[0].previous_status == "INACTIVE"


# CASE 6 — Collection FAILED → 모든 광고 STOPPED 처리 금지 (라우터의 try/except 구조 재현)
def test_case6_failed_collection_does_not_stop_ads(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # ACTIVE로 전환

    failed_run = collection_history.start_collection_run(db, competitor.id)
    try:
        raise RuntimeError("apify timeout")  # fetch_live_ads 실패 시뮬레이션
    except RuntimeError as e:
        collection_history.fail_collection_run(db, failed_run, str(e))
        # synchronize_ad_status는 호출하지 않는다 — ads.py collect_now / run_daily_collection.py와 동일 흐름

    ad = db.query(Ad).filter(Ad.competitor_id == competitor.id, Ad.ad_archive_id == "A").one()
    assert ad.status == "ACTIVE"  # STOPPED로 바뀌면 안 됨
    assert failed_run.status == "FAILED"
    assert not any(e.event_type == "STOPPED" for e in _events(db, competitor.id))


# CASE 7 — 2회 collection failure 후 성공 → 마지막 successful run과 비교
def test_case7_compares_against_last_success_across_failures(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # ACTIVE로 전환

    for _ in range(2):
        failed = collection_history.start_collection_run(db, competitor.id)
        collection_history.fail_collection_run(db, failed, "boom")

    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)

    stopped = [e for e in _events(db, competitor.id) if e.event_type == "STOPPED"]
    assert len(stopped) == 1
    assert stopped[0].previous_status == "ACTIVE"


# CASE 8 — History 도입 이전 날짜 → fake event 생성 금지
def test_case8_no_fake_events_before_history(db, competitor):
    run1 = _run(db, competitor)
    synchronize_ad_status(db, competitor.id, [_raw("A")], run1, tag_visual=False)

    result = collection_history.get_ad_changes(
        db, competitor.project_id, run1.run_date - timedelta(days=1), competitor.id
    )
    assert result.summary.started == 0
    assert result.summary.stopped == 0
    assert result.collection_status.value == "NO_RECORD"
    assert result.history_available_from == run1.run_date


# CASE 9 — 동일 ad_archive_id → 동일 광고
def test_case9_same_archive_id_is_same_ad(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    ad_id_first = db.query(Ad).filter(Ad.ad_archive_id == "A").one().id

    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)
    ads_with_a = db.query(Ad).filter(Ad.ad_archive_id == "A").all()

    assert len(ads_with_a) == 1
    assert ads_with_a[0].id == ad_id_first


# CASE 10 — Daily Visual Pattern: 해당 날짜 STARTED + REACTIVATED 광고만 aggregation
def test_case10_visual_pattern_only_started_and_reactivated(db, competitor):
    day0 = date(2026, 9, 16)
    day1 = date(2026, 9, 17)
    day2 = date(2026, 9, 18)

    synchronize_ad_status(db, competitor.id, [], _run(db, competitor, day0), tag_visual=False)  # baseline(빈 상태)

    synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor, day1), tag_visual=False)
    ad_a = db.query(Ad).filter(Ad.ad_archive_id == "A").one()
    ad_b = db.query(Ad).filter(Ad.ad_archive_id == "B").one()
    ad_a.visual_type, ad_b.visual_type = "PRODUCT", "PERSON"
    db.commit()

    day1_result = collection_history.get_ad_changes(db, competitor.project_id, day1, competitor.id)
    assert day1_result.visual_pattern == {"PRODUCT": 1, "PERSON": 1}

    # day2: A는 계속 노출(이벤트 없음), B는 종료(STOPPED), C는 신규(STARTED)
    synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("C")], _run(db, competitor, day2), tag_visual=False)
    ad_c = db.query(Ad).filter(Ad.ad_archive_id == "C").one()
    ad_c.visual_type = "GRAPHIC"
    db.commit()

    day2_result = collection_history.get_ad_changes(db, competitor.project_id, day2, competitor.id)
    assert day2_result.summary.started == 1
    assert day2_result.summary.stopped == 1
    assert day2_result.visual_pattern == {"GRAPHIC": 1}  # A(계속)/B(종료) 제외, C만 집계


# ── Product Stabilization spec 추가 케이스 (P0-02/03/04/07) ─────────────────


# 첫 성공 수집은 "오늘 켠 광고"가 아니라 baseline이다 — Daily Changes 켠 광고에 집계되면 안 된다.
def test_baseline_does_not_create_started_or_appear_in_daily_changes(db, competitor):
    run = _run(db, competitor)
    result = synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("B")], run, tag_visual=False)

    events = _events(db, competitor.id)
    assert result.new_ads == 2
    assert all(e.event_type == "BASELINE_DISCOVERED" for e in events)
    assert not any(e.event_type == "STARTED" for e in events)

    changes = collection_history.get_ad_changes(db, competitor.project_id, run.run_date, competitor.id)
    assert changes.summary.started == 0
    assert changes.baseline_discovered_count == 2
    assert changes.started_ads == []


# 아카이빙(14일 연속 미노출)된 광고가 같은 ad_archive_id로 재등장하면, 같은 row를 복원해야 한다
# (UNIQUE 제약 위반 없이) — 그리고 REACTIVATED가 기록돼야 한다.
def test_archived_ad_can_reactivate(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # baseline(NEW)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # ACTIVE

    for _ in range(14):
        synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)

    ad = db.query(Ad).filter(Ad.ad_archive_id == "A").one()
    assert ad.is_archived is True
    assert ad.status == "INACTIVE"
    original_id = ad.id

    # 재등장 — 새 row가 생기면(UNIQUE 위반) 여기서 IntegrityError로 즉시 실패한다.
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)

    ads_with_a = db.query(Ad).filter(Ad.ad_archive_id == "A").all()
    assert len(ads_with_a) == 1
    assert ads_with_a[0].id == original_id
    assert ads_with_a[0].is_archived is False
    assert ads_with_a[0].status == "ACTIVE"

    reactivated = [e for e in _events(db, competitor.id) if e.event_type == "REACTIVATED"]
    assert len(reactivated) == 1


# snapshot이 max_ads 상한에 도달해 잘렸을 수 있으면(snapshot_complete=False), 미발견 광고를
# STOPPED로 추론하지 않는다. 발견된 광고의 STARTED/ACTIVE 갱신은 정상 수행된다.
def test_partial_snapshot_creates_no_stopped_events(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A"), _raw("B")], _run(db, competitor), tag_visual=False)

    partial_run = _run(db, competitor)
    result = synchronize_ad_status(
        db, competitor.id, [_raw("A"), _raw("C")], partial_run, tag_visual=False, snapshot_complete=False
    )

    assert partial_run.status == "PARTIAL"
    assert result.newly_inactive == 0
    assert not any(e.event_type == "STOPPED" for e in _events(db, competitor.id))
    # B는 이번 수집에 없었지만 snapshot이 불완전하므로 상태가 건드려지지 않아야 한다
    ad_b = db.query(Ad).filter(Ad.ad_archive_id == "B").one()
    assert ad_b.status != "INACTIVE"
    # C는 정상적으로 새로 기록된다 (발견된 광고 처리는 완전성과 무관)
    assert db.query(Ad).filter(Ad.ad_archive_id == "C").count() == 1


# Gemini/미디어 캐싱 실패가 광고 수집 자체를 무효화하면 안 된다 (P0-07).
def test_media_analysis_failure_does_not_lose_collected_ads(db, competitor, monkeypatch):
    from app.services import media

    def _boom(*args, **kwargs):
        raise RuntimeError("gemini unavailable")

    monkeypatch.setattr(media, "process_ad_image", _boom)

    run = _run(db, competitor)
    result = synchronize_ad_status(
        db,
        competitor.id,
        [RawAdItem(ad_archive_id="A", page_id="1", page_name="p", format=AdFormat.IMAGE, image_url="https://x/a.jpg")],
        run,
        tag_visual=True,  # media.process_ad_image가 실제로 호출되도록
    )

    assert result.new_ads == 1
    assert run.status == "SUCCESS"  # 수집 자체는 여전히 성공
    ad = db.query(Ad).filter(Ad.ad_archive_id == "A").one()
    assert ad.analysis_status == "FAILED"
    assert ad.analysis_error is not None
    assert ad.visual_type is None
    # BASELINE_DISCOVERED든 STARTED든, 이벤트가 정상적으로 기록됐는지도 함께 확인
    assert len(_events(db, competitor.id)) == 1


# Part C-03 — 광고 1건의 event history를 오래된 순으로 반환한다.
def test_get_ad_history_returns_events_oldest_first(db, competitor):
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # baseline(NEW)
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # ACTIVE
    synchronize_ad_status(db, competitor.id, [], _run(db, competitor), tag_visual=False)  # STOPPED
    synchronize_ad_status(db, competitor.id, [_raw("A")], _run(db, competitor), tag_visual=False)  # REACTIVATED

    ad = db.query(Ad).filter(Ad.ad_archive_id == "A").one()
    history = collection_history.get_ad_history(db, ad.id)

    assert [e.event_type.value for e in history] == ["BASELINE_DISCOVERED", "STOPPED", "REACTIVATED"]
    assert history == sorted(history, key=lambda e: e.event_date)

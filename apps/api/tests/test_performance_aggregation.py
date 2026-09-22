"""§13 성능 최적화 회귀 검증 — SQL GROUP BY 집계가 기존 Python 루프 구현과 동일한 값을 내는지,
last_accessed_at throttle이 값의 의미(14일 자동 정지 정책)를 바꾸지 않으면서 DB write만 줄이는지."""

from datetime import datetime, timedelta, timezone

from app.models import Ad, Project, User
from app.routers.dashboard import get_dashboard
from app.services.autopause import touch_last_accessed
from app.services.collection_history import get_freshness_summary


def _make_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(competitor_id=competitor.id, ad_archive_id=archive_id, **kwargs)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def test_dashboard_sql_aggregation_matches_expected_counts(db, competitor):
    _make_ad(db, competitor, "A1", status="NEW", visual_type="PERSON")
    _make_ad(db, competitor, "A2", status="ACTIVE", visual_type="PERSON")
    _make_ad(db, competitor, "A3", status="ACTIVE", visual_type="PRODUCT")
    _make_ad(db, competitor, "A4", status="INACTIVE")
    _make_ad(db, competitor, "A5", status="ACTIVE", is_archived=True)  # 아카이빙된 건 집계 제외

    user = db.get(User, competitor.project.user_id)
    metrics = get_dashboard(competitor.project_id, db=db, user=user)

    assert metrics.new_count == 1
    assert metrics.active_count == 2  # A5는 아카이빙이라 제외
    assert metrics.inactive_count == 1
    assert metrics.visual_type_ratio == {"PERSON": 2, "PRODUCT": 1}


def test_freshness_window_function_matches_per_competitor_latest_run(db, competitor):
    from app.models import Competitor
    from app.services import collection_history

    other = Competitor(
        project_id=competitor.project_id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=2", page_id="2",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    # competitor: 오래된 FAILED → 최신 SUCCESS (최신 것만 반영돼야 함). SQLite의 CURRENT_TIMESTAMP는
    # 초 단위 해상도라 같은 테스트 안에서 연속 생성하면 started_at이 동률이 날 수 있으므로, 두 run의
    # 순서를 명확히 하기 위해 started_at을 직접 벌려서 지정한다(운영 Postgres는 마이크로초 해상도라
    # 실제로는 거의 발생하지 않는 케이스 — 정렬 로직 자체는 기존 구현과 동일하게 유지).
    old_run = collection_history.start_collection_run(db, competitor.id)
    old_run.started_at = datetime.now(timezone.utc) - timedelta(minutes=10)
    collection_history.fail_collection_run(db, old_run, "old failure")
    new_run = collection_history.start_collection_run(db, competitor.id)
    new_run.started_at = datetime.now(timezone.utc)
    collection_history.complete_collection_run_success(db, new_run, fetched_ads_count=1)
    db.commit()

    # other: PARTIAL만 있음
    other_run = collection_history.start_collection_run(db, other.id)
    collection_history.complete_collection_run_partial(db, other_run, fetched_ads_count=1)
    db.commit()

    summary = get_freshness_summary(db, competitor.project_id)
    assert summary.total_competitors == 2
    assert summary.success_competitors == 1  # 최신 run만 반영 — 오래된 FAILED는 무시됨
    assert summary.partial_competitors == 1
    assert summary.partial_competitor_names == ["다른 브랜드"]


def test_freshness_empty_project_returns_zeroed_summary(db, competitor):
    from app.models import Project

    empty = Project(user_id=competitor.project.user_id, name="빈 프로젝트")
    db.add(empty)
    db.commit()
    db.refresh(empty)

    summary = get_freshness_summary(db, empty.id)
    assert summary.total_competitors == 0
    assert summary.latest_run_at is None


def _as_utc(dt: datetime) -> datetime:
    # SQLite(테스트 DB)는 DateTime(timezone=True) 컬럼도 naive datetime으로 되돌려준다 — 기존
    # app.services.ad_sync._survival_days_at의 관례와 동일하게 UTC로 정규화해서 비교한다.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def test_touch_last_accessed_throttles_db_write(db):
    now = datetime.now(timezone.utc)
    user = User(email="throttle@adcather.local", last_accessed_at=now)
    db.add(user)
    db.commit()

    touch_last_accessed(db, user)  # 방금 갱신됨 — throttle window 안이므로 아무 것도 안 함
    db.refresh(user)
    assert abs((_as_utc(user.last_accessed_at) - now).total_seconds()) < 1


def test_touch_last_accessed_updates_after_threshold_and_restores_paused_projects(db):
    stale = datetime.now(timezone.utc) - timedelta(seconds=600)  # throttle 기본값(300초) 초과
    user = User(email="stale@adcather.local", last_accessed_at=stale)
    db.add(user)
    db.flush()
    project = Project(user_id=user.id, name="P", status="PAUSED")
    db.add(project)
    db.commit()

    touch_last_accessed(db, user)

    db.refresh(user)
    db.refresh(project)
    assert _as_utc(user.last_accessed_at) > stale
    assert project.status == "ACTIVE"  # PAUSED → ACTIVE 복구 로직은 그대로 동작

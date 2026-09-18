"""Initial Baseline + Daily Catch Opt-in UX — §34 테스트 케이스.

CASE 2/3/4(CTA 표시/클릭 반응)는 프론트엔드 상태이므로 여기서는 그 근거가 되는
백엔드 계약(SyncResult.is_baseline/snapshot_complete, PATCH /projects/{id})을 검증한다.
"""

from sqlalchemy import select

from app.models import Ad, AdObservation, AdStatusEvent, Project
from app.schemas import AdFormat, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def _run(db, competitor, run_date=None):
    return collection_history.start_collection_run(db, competitor.id, run_date=run_date)


# CASE 1 — 새 경쟁사 + 첫 성공/완전 수집(20건) → 전부 저장되지만 이벤트는 없음, is_baseline=True
def test_case1_first_complete_collection_is_baseline(db, competitor):
    items = [_raw(f"A{i}") for i in range(20)]
    run = _run(db, competitor)
    result = synchronize_ad_status(db, competitor.id, items, run, tag_visual=False)

    assert result.new_ads == 20
    assert result.is_baseline is True
    assert result.snapshot_complete is True
    assert db.query(Ad).filter(Ad.competitor_id == competitor.id).count() == 20
    assert db.query(AdObservation).filter(AdObservation.competitor_id == competitor.id).count() == 20

    events = db.query(AdStatusEvent).filter(AdStatusEvent.competitor_id == competitor.id).all()
    assert len(events) == 20
    assert all(e.event_type == "BASELINE_DISCOVERED" for e in events)
    assert not any(e.event_type in ("STARTED", "STOPPED", "REACTIVATED") for e in events)

    changes = collection_history.get_ad_changes(db, competitor.project_id, run.run_date, competitor.id)
    assert changes.summary.started == 0
    assert changes.baseline_discovered_count == 20


# CASE 5/6 — 스케줄러가 실제로 사용하는 쿼리 조건: auto_collect_enabled=false면 제외, true면 포함
def test_scheduler_query_respects_auto_collect_enabled(db, competitor):
    project = db.get(Project, competitor.project_id)

    project.auto_collect_enabled = False
    project.status = "ACTIVE"
    db.commit()
    scheduled = db.scalars(
        select(Project).where(Project.status == "ACTIVE", Project.auto_collect_enabled.is_(True))
    ).all()
    assert project.id not in [p.id for p in scheduled]

    project.auto_collect_enabled = True
    db.commit()
    scheduled = db.scalars(
        select(Project).where(Project.status == "ACTIVE", Project.auto_collect_enabled.is_(True))
    ).all()
    assert project.id in [p.id for p in scheduled]


# CASE 9 — 이미 auto_collect_enabled=true인 프로젝트에 새 경쟁사를 추가해도,
# 그 경쟁사의 첫 수집은 여전히 baseline이다 (project-level opt-in과 competitor-level baseline은 별개).
def test_new_competitor_baseline_independent_of_project_optin(db, competitor):
    from app.models import Competitor

    project = db.get(Project, competitor.project_id)
    project.auto_collect_enabled = True
    db.commit()

    new_competitor = Competitor(
        project_id=project.id,
        name="신규경쟁사",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=2",
        page_id="2",
    )
    db.add(new_competitor)
    db.commit()
    db.refresh(new_competitor)

    run = _run(db, new_competitor)
    result = synchronize_ad_status(db, new_competitor.id, [_raw("X"), _raw("Y")], run, tag_visual=False)

    assert result.is_baseline is True
    events = db.query(AdStatusEvent).filter(AdStatusEvent.competitor_id == new_competitor.id).all()
    assert all(e.event_type == "BASELINE_DISCOVERED" for e in events)


# 신규 프로젝트 기본값 — 기존 프로젝트를 되돌리지 않고, 신규 생성만 false
# (SQLAlchemy 컬럼 default는 flush/insert 시점에 적용되므로, 실제 INSERT를 거쳐 확인한다.)
def test_new_project_defaults_auto_collect_disabled(db):
    from app.models import User

    user = User(email="owner2@adcather.local")
    db.add(user)
    db.flush()

    project = Project(user_id=user.id, name="새 프로젝트")
    db.add(project)
    db.flush()

    assert project.auto_collect_enabled is False


# PATCH /projects/{id} — Baseline CTA의 Primary/Secondary 버튼이 호출하는 API 계약.
# 라우터 함수를 직접 호출해 검증한다 (HTTP/TestClient는 app.database.engine에 바인딩된
# 별도 세션을 쓰므로, 테스트용 인메모리 db fixture와 분리되어 있다).
def test_patch_project_toggles_auto_collect(db, competitor):
    from app.models import Project as ProjectModel
    from app.models import User
    from app.routers.projects import update_project
    from app.schemas import ProjectUpdate

    project = db.get(ProjectModel, competitor.project_id)
    owner = db.get(User, project.user_id)

    updated = update_project(project.id, ProjectUpdate(auto_collect_enabled=True), db=db, user=owner)
    assert updated.auto_collect_enabled is True

    updated = update_project(project.id, ProjectUpdate(auto_collect_enabled=False), db=db, user=owner)
    assert updated.auto_collect_enabled is False

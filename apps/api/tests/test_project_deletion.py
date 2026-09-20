"""Part H — Project Delete: cascade가 해당 Project 소속 데이터만 지우고, 다른 Project는
전혀 건드리지 않는지 검증한다. HTTP/TestClient 대신 기존 테스트 관례대로 라우터 함수를
in-memory db fixture로 직접 호출한다(test_baseline_optin.py 주석 참고)."""

import uuid
from datetime import date

import pytest
from fastapi import HTTPException

from app.models import Ad, AdObservation, AdStatusEvent, Competitor, CollectionRun, Project, User
from app.routers.projects import delete_project


def _make_project_with_data(db, user, name: str):
    project = Project(id=uuid.uuid4(), user_id=user.id, name=name)
    db.add(project)
    db.flush()

    comp = Competitor(
        id=uuid.uuid4(),
        project_id=project.id,
        name=f"{name}-brand",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=1",
        page_id="1",
        baseline_completed_at=None,
    )
    db.add(comp)
    db.flush()

    ad = Ad(id=uuid.uuid4(), competitor_id=comp.id, ad_archive_id=f"{name}-ad-1", status="ACTIVE")
    db.add(ad)
    db.flush()

    run = CollectionRun(id=uuid.uuid4(), competitor_id=comp.id, run_date=date(2026, 9, 19), status="SUCCESS")
    db.add(run)
    db.flush()

    obs = AdObservation(id=uuid.uuid4(), collection_run_id=run.id, competitor_id=comp.id, ad_id=ad.id)
    db.add(obs)

    event = AdStatusEvent(
        id=uuid.uuid4(),
        ad_id=ad.id,
        competitor_id=comp.id,
        collection_run_id=run.id,
        event_type="BASELINE_DISCOVERED",
        event_date=date(2026, 9, 19),
        new_status="ACTIVE",
    )
    db.add(event)
    db.commit()
    # id만 미리 뽑아둔다 — 삭제 후 만료된 ORM 인스턴스의 속성에 접근하면
    # ObjectDeletedError가 나므로, 검증에는 항상 이 plain uuid 값들만 쓴다.
    return {
        "project_id": project.id,
        "competitor_id": comp.id,
        "ad_id": ad.id,
        "run_id": run.id,
    }


@pytest.fixture(autouse=True)
def _no_network_storage_cleanup(monkeypatch):
    # 실제 Supabase Storage 호출 없이 best-effort cleanup 경로만 검증한다.
    monkeypatch.setattr("app.routers.projects.storage.cleanup_prefix", lambda prefix: True)


def test_delete_project_cascades_only_its_own_data(db):
    owner = User(id=uuid.uuid4(), email="owner@adcather.local")
    db.add(owner)
    db.flush()

    target = _make_project_with_data(db, owner, "target")
    other = _make_project_with_data(db, owner, "other")

    delete_project(target["project_id"], db=db, user=owner)
    # 벌크 delete(synchronize_session=False) 이후 커밋되면 세션의 identity map이 expire되므로,
    # db.get() 대신 항상 새 SELECT를 날리는 filter_by(...).first()로 확인한다.
    db.expire_all()

    # 대상 프로젝트와 그 소속 row는 모두 사라진다.
    assert db.query(Project).filter_by(id=target["project_id"]).first() is None
    assert db.query(Competitor).filter_by(id=target["competitor_id"]).first() is None
    assert db.query(Ad).filter_by(id=target["ad_id"]).first() is None
    assert db.query(CollectionRun).filter_by(id=target["run_id"]).first() is None
    assert db.query(AdObservation).filter_by(competitor_id=target["competitor_id"]).count() == 0
    assert db.query(AdStatusEvent).filter_by(competitor_id=target["competitor_id"]).count() == 0

    # 다른 프로젝트 데이터는 전혀 영향받지 않는다.
    assert db.query(Project).filter_by(id=other["project_id"]).first() is not None
    assert db.query(Competitor).filter_by(id=other["competitor_id"]).first() is not None
    assert db.query(Ad).filter_by(id=other["ad_id"]).first() is not None
    assert db.query(CollectionRun).filter_by(id=other["run_id"]).first() is not None
    assert db.query(AdObservation).filter_by(competitor_id=other["competitor_id"]).count() == 1
    assert db.query(AdStatusEvent).filter_by(competitor_id=other["competitor_id"]).count() == 1


def test_delete_project_requires_ownership(db):
    owner = User(id=uuid.uuid4(), email="owner@adcather.local")
    intruder = User(id=uuid.uuid4(), email="intruder@adcather.local")
    db.add_all([owner, intruder])
    db.flush()

    made = _make_project_with_data(db, owner, "private")

    with pytest.raises(HTTPException) as exc_info:
        delete_project(made["project_id"], db=db, user=intruder)
    assert exc_info.value.status_code == 404

    # 소유자가 아닌 요청으로는 삭제되지 않았어야 한다.
    assert db.get(Project, made["project_id"]) is not None


def test_delete_project_missing_returns_404(db):
    owner = User(id=uuid.uuid4(), email="owner@adcather.local")
    db.add(owner)
    db.flush()

    with pytest.raises(HTTPException) as exc_info:
        delete_project(uuid.uuid4(), db=db, user=owner)
    assert exc_info.value.status_code == 404

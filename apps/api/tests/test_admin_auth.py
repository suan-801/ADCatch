"""Viewer/Admin 권한 — 쿠키 세션이 핵심이라 라우터 함수 직접 호출이 아니라 실제 HTTP
요청(TestClient)으로 검증한다 (다른 테스트 파일들의 관례와 다른 이유는 conftest.py 상단 주석 참고:
그 관례는 DB 로직 검증용이고, 이 파일은 인증 미들웨어/쿠키 자체를 검증한다)."""

import uuid

import bcrypt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import config
from app.database import Base, get_db
from app.main import app
from app.models import Project, User
from app.services import admin_auth

RAW_PASSWORD = "correct-horse-battery-staple"


@pytest.fixture(autouse=True)
def _reset_rate_limit_state():
    admin_auth._failed_attempts.clear()
    yield
    admin_auth._failed_attempts.clear()


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    TestSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    monkeypatch.setattr(
        config.settings, "admin_password_hash", bcrypt.hashpw(RAW_PASSWORD.encode(), bcrypt.gensalt()).decode()
    )
    monkeypatch.setattr(config.settings, "admin_session_secret", "test-session-secret")
    monkeypatch.setattr(config.settings, "admin_login_max_attempts", 3)
    monkeypatch.setattr(config.settings, "admin_login_lockout_seconds", 300)

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


@pytest.fixture()
def seeded_project(client):
    """default_admin 소유의 Project 1개를 미리 DB에 넣어둔다 (Viewer의 GET 성공 경로 검증용)."""
    override = app.dependency_overrides[get_db]
    db = next(override())
    try:
        user = User(id=uuid.uuid4(), email=config.settings.default_admin_email)
        db.add(user)
        db.flush()
        project = Project(id=uuid.uuid4(), user_id=user.id, name="Seeded")
        db.add(project)
        db.commit()
        db.refresh(project)
        return project.id
    finally:
        db.close()


# ── Viewer (인증 없음) ────────────────────────────────────────────────────

def test_viewer_can_read_projects(client, seeded_project):
    res = client.get("/projects")
    assert res.status_code == 200
    assert any(p["id"] == str(seeded_project) for p in res.json())


def test_viewer_can_read_competitors(client, seeded_project):
    res = client.get(f"/projects/{seeded_project}/competitors")
    assert res.status_code == 200
    assert res.json() == []


def test_viewer_cannot_create_project(client):
    res = client.post("/projects", json={"name": "hacked"})
    assert res.status_code == 401


def test_viewer_cannot_update_project(client, seeded_project):
    res = client.patch(f"/projects/{seeded_project}", json={"auto_collect_enabled": True})
    assert res.status_code == 401


def test_viewer_cannot_delete_project(client, seeded_project):
    res = client.delete(f"/projects/{seeded_project}")
    assert res.status_code == 401


def test_viewer_cannot_create_competitor(client, seeded_project):
    res = client.post(
        f"/projects/{seeded_project}/competitors",
        json={"name": "brand", "ad_library_url": "https://www.facebook.com/ads/library/?view_all_page_id=1"},
    )
    assert res.status_code == 401


def test_viewer_cannot_trigger_collect(client):
    res = client.post(f"/competitors/{uuid.uuid4()}/ads/collect")
    assert res.status_code == 401


# ── 로그인 ────────────────────────────────────────────────────────────────

def test_login_with_wrong_password_fails(client):
    res = client.post("/auth/admin", json={"password": "wrong"})
    assert res.status_code == 401
    assert "hash" not in res.text.lower()  # 서버 내부 정보(해시 등) 노출 금지


def test_login_rate_limited_after_max_attempts(client):
    for _ in range(3):
        res = client.post("/auth/admin", json={"password": "wrong"})
        assert res.status_code == 401
    res = client.post("/auth/admin", json={"password": "wrong"})
    assert res.status_code == 429


def test_login_success_sets_cookie_and_status_reflects_it(client):
    res = client.post("/auth/admin", json={"password": RAW_PASSWORD})
    assert res.status_code == 200
    assert res.json() == {"is_admin": True}
    assert admin_auth.ADMIN_COOKIE_NAME in res.cookies

    status_res = client.get("/auth/status")
    assert status_res.json() == {"is_admin": True}


# ── Admin 인증 후 ─────────────────────────────────────────────────────────

def test_admin_can_create_update_delete_project(client):
    login = client.post("/auth/admin", json={"password": RAW_PASSWORD})
    assert login.status_code == 200

    create_res = client.post("/projects", json={"name": "새 프로젝트"})
    assert create_res.status_code == 200
    project_id = create_res.json()["id"]

    update_res = client.patch(f"/projects/{project_id}", json={"auto_collect_enabled": True})
    assert update_res.status_code == 200
    assert update_res.json()["auto_collect_enabled"] is True

    delete_res = client.delete(f"/projects/{project_id}")
    assert delete_res.status_code == 204


def test_admin_can_create_competitor(client):
    client.post("/auth/admin", json={"password": RAW_PASSWORD})
    project_id = client.post("/projects", json={"name": "브랜드테스트"}).json()["id"]

    res = client.post(
        f"/projects/{project_id}/competitors",
        json={"name": "브랜드A", "ad_library_url": "https://www.facebook.com/ads/library/?view_all_page_id=1"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "브랜드A"


def test_admin_collect_passes_auth_gate(client, monkeypatch):
    """실제 Apify 호출 없이, 401/403이 아니라 인증을 통과해 라우트 본문까지 도달하는지만 검증한다."""
    client.post("/auth/admin", json={"password": RAW_PASSWORD})
    project_id = client.post("/projects", json={"name": "수집테스트"}).json()["id"]
    competitor_id = client.post(
        f"/projects/{project_id}/competitors",
        json={"name": "브랜드A", "ad_library_url": "https://www.facebook.com/ads/library/?view_all_page_id=1"},
    ).json()["id"]

    monkeypatch.setattr("app.routers.ads.fetch_live_ads", lambda *a, **k: [])

    res = client.post(f"/competitors/{competitor_id}/ads/collect")
    assert res.status_code != 401
    assert res.status_code != 403


# ── 로그아웃 ──────────────────────────────────────────────────────────────

def test_logout_revokes_session(client):
    client.post("/auth/admin", json={"password": RAW_PASSWORD})
    assert client.get("/auth/status").json()["is_admin"] is True

    logout_res = client.post("/auth/logout")
    assert logout_res.status_code == 200
    assert logout_res.json() == {"is_admin": False}

    assert client.get("/auth/status").json()["is_admin"] is False
    assert client.post("/projects", json={"name": "after-logout"}).status_code == 401

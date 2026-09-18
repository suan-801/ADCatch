"""SQLite 인메모리 DB로 도는 유닛테스트 fixture.

app.models 의 Uuid 타입은 SQLAlchemy 2.0 범용 Uuid라 Postgres 없이도 동일 모델로
동작한다 (models.py 상단 주석 참고). 실제 배포 DB(Postgres/Supabase)를 띄우지 않고도
이벤트 판정 로직(ad_sync.synchronize_ad_status)을 빠르게 검증하기 위한 용도다.
"""

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Competitor, Project, User


@pytest.fixture()
def db() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def competitor(db: Session) -> Competitor:
    user = User(id=uuid.uuid4(), email="test@adcather.local")
    db.add(user)
    db.flush()
    project = Project(id=uuid.uuid4(), user_id=user.id, name="TEST")
    db.add(project)
    db.flush()
    comp = Competitor(
        id=uuid.uuid4(),
        project_id=project.id,
        name="경쟁사A",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=1",
        page_id="1",
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp

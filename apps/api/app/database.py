from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings

# Supabase 대시보드에서 그대로 복사한 연결 문자열은 드라이버 없이 "postgresql://"로
# 오는데, 우리는 psycopg2가 아닌 psycopg3(psycopg[binary])를 설치해뒀으므로
# 드라이버가 명시되지 않은 경우에만 +psycopg를 붙여 정규화한다.
_database_url = settings.database_url
if _database_url.startswith("postgresql://"):
    _database_url = _database_url.replace("postgresql://", "postgresql+psycopg://", 1)

engine = create_engine(_database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

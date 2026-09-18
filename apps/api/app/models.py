import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

# SQLAlchemy 2.0의 범용 Uuid 타입 사용 — Postgres에서는 네이티브 UUID로,
# SQLite(로컬 테스트) 등 다른 백엔드에서도 동일 모델로 동작한다.
UUID = Uuid

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    last_accessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    projects: Mapped[list["Project"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # ACTIVE | PAUSED
    auto_collect_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="projects")
    competitors: Mapped[list["Competitor"]] = relationship(back_populates="project", cascade="all, delete-orphan")


class Competitor(Base):
    __tablename__ = "competitors"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    ad_library_url: Mapped[str] = mapped_column(Text, nullable=False)
    page_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    # PRD 3.1: 프로젝트(워크스페이스) = 자사 1 + 경쟁사 N. 자사도 동일 테이블의 한 row로 등록하되
    # 대시보드 신규/종료 카운트·갤러리 집계에서는 제외한다.
    is_own_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="competitors")
    ads: Mapped[list["Ad"]] = relationship(back_populates="competitor", cascade="all, delete-orphan")


class Ad(Base):
    __tablename__ = "ads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    ad_archive_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW | ACTIVE | INACTIVE
    visual_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)  # IMAGE | VIDEO | CAROUSEL
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consecutive_inactive_days: Mapped[int] = mapped_column(Integer, default=0)
    # PRD 3.3: INACTIVE 전환 후 14일 연속 미노출 시 수집 대상에서 아카이빙.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    competitor: Mapped["Competitor"] = relationship(back_populates="ads")


# ── Daily Ad Change History (additive, 2026-09) ────────────────────────────
# ads 테이블은 "현재 상태"만 담당한다. 아래 3개 테이블이 각각 수집 실행 기록/관측 증거/
# 상태 변화 이력을 분리해서 담당한다 (기존 ads 테이블 구조는 변경하지 않음).


class CollectionRun(Base):
    """경쟁사 1곳에 대한 수집 시도 1회. 성공/실패를 명시적으로 남겨, 이후 "실패"와
    "경쟁사가 광고를 모두 껐음"을 절대 혼동하지 않도록 한다 (다음 비교는 항상 직전
    SUCCESS run과만 수행)."""

    __tablename__ = "collection_runs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # KST(Asia/Seoul) 캘린더 날짜로 시작 시점에 고정 — 날짜별 조회를 TIMESTAMPTZ→DATE 변환 없이
    # 단순 동등비교로 처리하기 위함 (app.services.collection_history.today_kst).
    run_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING | SUCCESS | FAILED
    fetched_ads_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdObservation(Base):
    """SUCCESS인 collection_run에서 실제로 발견된(라이브였던) 광고 1건.
    "이전 성공 스냅샷 vs 이번 성공 스냅샷" 비교의 근거가 되는 관측 증거."""

    __tablename__ = "ad_observations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    collection_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collection_runs.id", ondelete="CASCADE"))
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    ad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AdStatusEvent(Base):
    """상태 "전환이 발생한 순간"에만 1건 생성된다 (같은 상태가 계속되는 동안 반복 생성되지 않음).
    event_date는 KST(Asia/Seoul) 기준 캘린더 날짜로 고정해 저장 — 조회 시 UTC 경계로
    하루씩 밀리는 문제를 피한다 (app.services.collection_history.today_kst 참고)."""

    __tablename__ = "ad_status_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"))
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    collection_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collection_runs.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STARTED | STOPPED | REACTIVATED
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

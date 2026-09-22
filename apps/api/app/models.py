import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, String, Text, Uuid, func
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
    # 새 프로젝트는 명시적 opt-in 전까지 자동 수집하지 않는다 (2026-09, Baseline+Opt-in UX).
    # 기존 row는 마이그레이션하지 않는다 — 이 default는 신규 INSERT에만 적용된다.
    auto_collect_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
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
    # DEPRECATED (2026-09, Brand Model Simplification / P0-18~22): Project 안의 모든 등록 대상은
    # 동일한 "추적 브랜드"로 취급한다 — 자사/경쟁사 구분은 더 이상 business logic에서 사용하지 않는다.
    # 기존 데이터 보존을 위해 column만 남겨둔다(신규 조회/집계 로직은 이 필드를 참조하지 않음).
    # 향후 실제 role 구분이 필요해지면 boolean이 아닌 generic한 brand_role/tags 필드를 검토한다.
    is_own_brand: Mapped[bool] = mapped_column(Boolean, default=False)
    # P0-08: "첫 수집"이 아니라 "첫 COMPLETE SUCCESSFUL SNAPSHOT"이 Baseline이다. NULL이면 아직
    # baseline이 확정되지 않은 상태(PARTIAL만 있었거나 아예 수집 이력이 없음) — 이 경우 STARTED/STOPPED/
    # REACTIVATED 이벤트를 생성하지 않는다 (app.services.ad_sync 참고).
    baseline_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
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
    # 수집기가 파싱한 Meta 소재상의 실제 집행 시작일 (모르면 NULL) — ADCatcher가 "처음 관측한"
    # first_seen_at과는 별개 개념이다 (P0-06). UI는 이 값이 있으면 "집행 N일", 없으면 "추적 N일".
    source_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW | ACTIVE | INACTIVE
    visual_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    format: Mapped[str | None] = mapped_column(String(20), nullable=True)  # IMAGE | VIDEO | CAROUSEL
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    copy_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    cta_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consecutive_inactive_days: Mapped[int] = mapped_column(Integer, default=0)
    # PRD 3.3: INACTIVE 전환 후 14일 연속 미노출 시 수집 대상에서 아카이빙.
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False)
    # Gemini/썸네일 캐싱(enrichment)은 수집(core data)과 완전히 분리된 상태로 추적한다 (P0-07).
    # 분석이 실패해도 ads row 자체는 항상 정상 생성/유지된다.
    analysis_status: Mapped[str] = mapped_column(String(20), default="PENDING")  # PENDING | SUCCESS | FAILED
    analysis_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    analysis_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # ── Campaign Tag 자동 분류 (additive, 2026-09) ──────────────────────
    # assignment_source("누가 지정했는가")와 classification_status("상태")를 분리한다 — 상태값을
    # source 필드에 섞어 넣지 않는다(NEEDS_REVIEW는 상태이지 지정 주체가 아니다).
    campaign_tag_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("campaign_tags.id", ondelete="SET NULL"), nullable=True
    )
    campaign_tag_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    campaign_tag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'AI' | 'USER' | NULL(아직 아무도 지정하지 않음)
    campaign_tag_assignment_source: Mapped[str | None] = mapped_column(String(10), nullable=True)
    campaign_tag_classified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # 'PENDING' | 'SUCCESS' | 'NEEDS_REVIEW' | 'FAILED' — analysis_status와 동일한 lifecycle 패턴.
    campaign_classification_status: Mapped[str] = mapped_column(String(20), default="PENDING")
    campaign_classification_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    campaign_classification_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── VIDEO/CAROUSEL 미디어 메타데이터 (additive, 2026-09) ─────────────
    # image_url은 기존과 동일하게 "대표 썸네일 1장"으로 계속 쓰인다. video_url/media_items는
    # 원본 구조를 추가로 보존해 VIDEO 상세(keyframe)/CAROUSEL 상세(카드 구성) UI에 쓴다.
    video_url: Mapped[str | None] = mapped_column(Text, nullable=True)  # VIDEO 포맷 전용, HD 우선
    media_items: Mapped[list | None] = mapped_column(JSON, nullable=True)  # [{type, url, preview_url}]
    keyframe_urls: Mapped[list | None] = mapped_column(JSON, nullable=True)  # 캐싱된 keyframe URL 최대 4개
    # NOT_APPLICABLE(비-VIDEO) | PENDING | SUCCESS | FAILED
    keyframe_status: Mapped[str] = mapped_column(String(20), default="NOT_APPLICABLE")
    keyframe_retry_count: Mapped[int] = mapped_column(Integer, default=0)
    keyframe_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    competitor: Mapped["Competitor"] = relationship(back_populates="ads")
    campaign_tag: Mapped["CampaignTag | None"] = relationship()


class CampaignTag(Base):
    """프로젝트별로 사용자가 직접 정의하는 캠페인 분류 태그 (additive, 2026-09).
    시스템에 고정된 카테고리를 두지 않고, 프로젝트마다 태그명+정의를 자유롭게 관리한다."""

    __tablename__ = "campaign_tags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    definition: Mapped[str] = mapped_column(Text, nullable=False)
    # 삭제는 soft delete(is_active=False)다 — 과거 소재에 이미 붙은 태그 표시/이력을 보존하기 위해
    # hard delete를 하지 않는다. 비활성 태그는 Gemini 분류 입력/수동 지정 후보에서 항상 제외된다.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


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
    # PARTIAL = fetch 자체는 성공했지만 max_ads 상한에 도달해 전체 스냅샷을 보장할 수 없음 (P0-02).
    # PARTIAL인 run은 STOPPED 판정에 절대 사용되지 않는다.
    status: Mapped[str] = mapped_column(String(20), default="RUNNING")  # RUNNING | SUCCESS | PARTIAL | FAILED
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

    # 운영 중 실측 버그: relationship()이 없으면 SQLAlchemy unit-of-work가 같은 flush 안에서
    # ads INSERT를 ad_observations INSERT보다 먼저 실행해야 한다는 걸 감지하지 못해 신규 Ad를
    # 참조하는 ad_observations insert가 ForeignKeyViolation으로 실패했다(순수 Column(ForeignKey)만으로는
    # unit-of-work의 flush 순서 계산에 반영되지 않는다 — Table 메타데이터의 FK와는 별개). 이 관계를
    # 명시해 Ad가 항상 먼저 flush되도록 보장한다.
    ad: Mapped["Ad"] = relationship()


class AdStatusEvent(Base):
    """상태 "전환이 발생한 순간"에만 1건 생성된다 (같은 상태가 계속되는 동안 반복 생성되지 않음).
    event_date는 KST(Asia/Seoul) 기준 캘린더 날짜로 고정해 저장 — 조회 시 UTC 경계로
    하루씩 밀리는 문제를 피한다 (app.services.collection_history.today_kst 참고)."""

    __tablename__ = "ad_status_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ad_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ads.id", ondelete="CASCADE"))
    competitor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("competitors.id", ondelete="CASCADE"))
    collection_run_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("collection_runs.id", ondelete="CASCADE"))
    event_type: Mapped[str] = mapped_column(String(20), nullable=False)  # STARTED | STOPPED | REACTIVATED | BASELINE_DISCOVERED
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    previous_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    new_status: Mapped[str] = mapped_column(String(20), nullable=False)
    # P1-01: 이 이벤트가 발생한 "그 순간"의 집행/추적 일수를 고정 저장한다. Ad row는 이후에도 계속
    # 갱신되므로(예: 이후 REACTIVATED로 last_seen_at이 앞으로 밀림), 과거 이벤트를 나중에 다시 조회할 때
    # ad의 현재 값으로 재계산하면 숫자가 바뀌어버린다 — 이를 막기 위한 snapshot. 과거(이 필드 도입 이전)
    # 이벤트는 NULL이며, 이 경우 fake backfill을 하지 않고 프론트가 라이브 계산으로 폴백한다.
    survival_days_at_event: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # AdObservation과 동일한 이유로 필요 — 위 주석 참고.
    ad: Mapped["Ad"] = relationship()

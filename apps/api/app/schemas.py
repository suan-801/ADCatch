import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class AdStatus(str, Enum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"


class VisualType(str, Enum):
    PERSON = "PERSON"
    PRODUCT = "PRODUCT"
    TEXT_HEAVY = "TEXT_HEAVY"
    GRAPHIC = "GRAPHIC"


class AdFormat(str, Enum):
    IMAGE = "IMAGE"
    VIDEO = "VIDEO"
    CAROUSEL = "CAROUSEL"


class ProjectStatus(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"


# ── Raw collector output (per-fetch, before DB sync) ──────────────────────

class RawAdItem(BaseModel):
    ad_archive_id: str
    page_id: str
    page_name: str
    copy_text: str | None = None
    cta_text: str | None = None
    image_url: str | None = None
    format: AdFormat
    start_date: datetime | None = None


# ── API request/response models ───────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str


class ProjectUpdate(BaseModel):
    """현재는 auto_collect_enabled 토글 전용 (Baseline opt-in CTA / Project Header 설정).
    부분 업데이트이므로 전달된 필드만 반영한다."""

    auto_collect_enabled: bool | None = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: ProjectStatus
    auto_collect_enabled: bool
    created_at: datetime


class CompetitorCreate(BaseModel):
    name: str
    ad_library_url: str
    # DEPRECATED (P0-21/P0-18~22): Brand Model Simplification 이후 새 클라이언트는 이 필드를
    # 보낼 필요가 없다. 하위호환을 위해 optional로 남겨두되 business logic에서는 무시된다.
    is_own_brand: bool = False


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    ad_library_url: str
    page_id: str | None
    # DEPRECATED — 더 이상 UI/집계 로직에서 사용하지 않는다. 하위호환을 위해 응답에는 남겨둔다.
    is_own_brand: bool
    created_at: datetime


class AdOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    ad_archive_id: str
    status: AdStatus
    visual_type: VisualType | None
    format: AdFormat | None
    image_url: str | None
    copy_text: str | None
    cta_text: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    # 소재상의 실제 집행 시작일 (P0-06). ADCatcher가 처음 관측한 first_seen_at과는 다른 개념.
    source_started_at: datetime | None
    consecutive_inactive_days: int
    is_archived: bool

    @property
    def survival_days(self) -> int:
        return max((self.last_seen_at - self.first_seen_at).days, 0)


class DashboardMetrics(BaseModel):
    project_id: uuid.UUID
    new_count: int
    active_count: int
    inactive_count: int
    visual_type_ratio: dict[str, int]


class SyncResult(BaseModel):
    competitor_id: uuid.UUID
    new_ads: int
    reactivated_or_kept_active: int
    newly_inactive: int
    newly_archived: int
    # Baseline + Daily Catch Opt-in UX: 이 수집이 해당 경쟁사의 "첫 성공 수집"이었는지, 그리고
    # snapshot이 완전했는지(=STOPPED 판정 신뢰 가능한지). 프론트는 is_baseline && snapshot_complete
    # 일 때만 Baseline CTA를 보여준다 (§25 — 실패/부분 수집 결과는 기준점으로 삼지 않음).
    is_baseline: bool
    snapshot_complete: bool


# ── Daily Ad Change History (additive) ─────────────────────────────────────

class AdChangeEventType(str, Enum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    REACTIVATED = "REACTIVATED"
    # 경쟁사 등록 후 첫 성공 수집에서 발견된 기존 집행 소재 (P0-03) — "오늘 켠 광고"가 아니라
    # "처음 확인한 현재 집행 목록"이므로 Daily Changes의 켠/끈 광고 집계에서 제외된다.
    BASELINE_DISCOVERED = "BASELINE_DISCOVERED"


class CollectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    NO_RECORD = "NO_RECORD"


class ChangedAdOut(BaseModel):
    """AdOut + 이 날짜에 발생한 이벤트 배지. 기존 AdOut 필드를 그대로 포함해
    프론트가 기존 Ad Card 컴포넌트를 그대로 재사용할 수 있게 한다."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    competitor_id: uuid.UUID
    ad_archive_id: str
    status: AdStatus
    visual_type: VisualType | None
    format: AdFormat | None
    image_url: str | None
    copy_text: str | None
    cta_text: str | None
    first_seen_at: datetime
    last_seen_at: datetime
    source_started_at: datetime | None
    consecutive_inactive_days: int
    is_archived: bool
    event_type: AdChangeEventType
    competitor_name: str
    # P1-01: 이 이벤트가 발생한 순간에 고정된 집행/추적 일수. None이면(이 필드 도입 이전 이벤트)
    # 프론트가 현재 ad 값 기준으로 라이브 계산한다(fake backfill 금지).
    survival_days_at_event: int | None = None


class AdChangeSummary(BaseModel):
    started: int
    reactivated: int
    stopped: int


class CollectionStatusSummary(BaseModel):
    """P0-15: 프로젝트 단위 수집 상태를 단일 값으로 뭉개지 않고, 브랜드별 상태 분포를 함께 제공한다."""

    success: int
    partial: int
    failed: int
    no_record: int


class AdChangesResponse(BaseModel):
    project_id: uuid.UUID
    date: date
    competitor_id: uuid.UUID | None
    collection_status: CollectionStatus
    # P0-15: 하나의 값(collection_status)만으로는 "일부만 실패"가 감춰지므로, 브랜드별 상태 분포도 함께 제공한다.
    collection_summary: CollectionStatusSummary
    history_available_from: date | None
    # 이 날짜가 브랜드 등록 직후의 baseline 수집일이면 > 0 (P0-03). summary의 started/reactivated와는
    # 별개로 집계되며, 프론트는 이 값이 있을 때 "오늘 N개를 켰어요"가 아니라 "N개를 처음 확인했어요"로 표기한다.
    baseline_discovered_count: int
    summary: AdChangeSummary
    started_ads: list[ChangedAdOut]
    reactivated_ads: list[ChangedAdOut]
    stopped_ads: list[ChangedAdOut]
    visual_pattern: dict[str, int]


class CollectionFreshness(BaseModel):
    """프로젝트 헤더 근처에 표시할 '이 데이터를 믿어도 되는가' 요약 (P0-09/P0-16)."""

    project_id: uuid.UUID
    latest_run_at: datetime | None
    total_competitors: int
    # 하위호환: SUCCESS + PARTIAL 합계(기존 의미 그대로 유지).
    healthy_competitors: int
    # P0-16: PARTIAL을 SUCCESS와 동일하게 "정상"으로 뭉개지 않기 위한 세부 분해.
    success_competitors: int
    partial_competitors: int
    partial_competitor_names: list[str]
    failed_competitor_names: list[str]

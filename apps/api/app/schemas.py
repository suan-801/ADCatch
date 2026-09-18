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
    is_own_brand: bool = False


class CompetitorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    ad_library_url: str
    page_id: str | None
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


# ── Daily Ad Change History (additive) ─────────────────────────────────────

class AdChangeEventType(str, Enum):
    STARTED = "STARTED"
    STOPPED = "STOPPED"
    REACTIVATED = "REACTIVATED"


class CollectionStatus(str, Enum):
    SUCCESS = "SUCCESS"
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
    consecutive_inactive_days: int
    is_archived: bool
    event_type: AdChangeEventType
    competitor_name: str


class AdChangeSummary(BaseModel):
    started: int
    reactivated: int
    stopped: int


class AdChangesResponse(BaseModel):
    project_id: uuid.UUID
    date: date
    competitor_id: uuid.UUID | None
    collection_status: CollectionStatus
    history_available_from: date | None
    summary: AdChangeSummary
    started_ads: list[ChangedAdOut]
    reactivated_ads: list[ChangedAdOut]
    stopped_ads: list[ChangedAdOut]
    visual_pattern: dict[str, int]

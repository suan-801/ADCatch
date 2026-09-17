import uuid
from datetime import datetime
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

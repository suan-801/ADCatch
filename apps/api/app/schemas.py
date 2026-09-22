import uuid
from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, field_validator


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


# ── Campaign Tag 자동 분류 (additive, 2026-09) ─────────────────────────────
# assignment_source("누가 지정했는가")와 classification_status("상태")는 서로 다른 축이다 —
# NEEDS_REVIEW는 상태이지 지정 주체가 아니므로 source enum에 섞지 않는다.

class CampaignTagAssignmentSource(str, Enum):
    AI = "AI"
    USER = "USER"


class CampaignClassificationStatus(str, Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    FAILED = "FAILED"


# ── VIDEO/CAROUSEL 미디어 메타데이터 (additive, 2026-09) ───────────────────

class MediaItem(BaseModel):
    type: str  # "image" | "video"
    url: str
    preview_url: str | None = None


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
    # VIDEO 포맷 전용 대표 영상 URL(HD 우선, SD fallback). CAROUSEL/IMAGE는 NULL — 개별 카드 영상은
    # media_items에만 담긴다.
    video_url: str | None = None
    media_items: list[MediaItem] = []


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


class AdminLoginRequest(BaseModel):
    password: str


class AdminStatusOut(BaseModel):
    is_admin: bool


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


class CampaignTagCreate(BaseModel):
    name: str
    definition: str


class CampaignTagUpdate(BaseModel):
    """부분 업데이트 — 전달된 필드만 반영한다."""

    name: str | None = None
    definition: str | None = None


class CampaignTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    name: str
    definition: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CampaignTagReclassifyRequest(BaseModel):
    # USER가 직접 지정한 소재까지 재분류 대상에 포함할지 — 기본 false(사용자 지정값은 항상 보존).
    include_user_assigned: bool = False


class CampaignTagReclassifyResult(BaseModel):
    # SUCCESS/NEEDS_REVIEW/FAILED에서 PENDING으로 실제 리셋한 개수.
    reset_count: int
    # 이미 PENDING이라 리셋할 필요는 없지만, 활성 태그 기준 pending 배치의 대상인 기존 광고 수
    # (예: 태그가 없던 시절 생성된 광고) — reset_count에 포함되지 않아도 "기존 광고 반영"
    # 대상임을 사용자에게 명확히 보여주기 위한 값.
    already_pending_count: int
    # reset_count + already_pending_count — 이번 "기존 광고 반영"의 전체 대상 수.
    total_target_count: int


class CampaignTagClassificationStatusOut(BaseModel):
    """§2-2 — "이번 재분류 진행률"이 아니라 "현재 프로젝트 소재 분류 상태" 스냅샷이다. 별도
    job/batch 추적 테이블 없이 Ad.campaign_classification_status를 그대로 집계한 값이므로,
    이전에 이미 분류됐던 소재의 SUCCESS도 포함된다 — UI에서 "이번 재분류 대상 수"
    (CampaignTagReclassifyResult)와 혼동되지 않도록 별도 레이블로 표시해야 한다."""

    pending: int
    success: int
    needs_review: int
    failed: int


class CampaignTagProcessPendingRequest(BaseModel):
    limit: int | None = None


class CampaignTagProcessPendingResult(BaseModel):
    processed: int
    succeeded: int
    needs_review: int
    still_pending: int
    failed: int
    quota_stopped: bool
    # 이 배치 실행 후에도 프로젝트에 남아있는 PENDING 소재 수(참고용 — Daily Scheduler가
    # 사용자가 페이지를 떠난 뒤에도 계속 처리한다).
    pending_remaining: int


class AdCampaignTagUpdate(BaseModel):
    campaign_tag_id: uuid.UUID


# ── Ad 미디어/캠페인 태그 공용 필드 믹스인 ──────────────────────────────────
# AdOut/ChangedAdOut가 이 필드셋을 공유한다 (Campaign Tag + VIDEO/CAROUSEL 미디어, 둘 다 additive).

class _AdMediaAndCampaignFields(BaseModel):
    campaign_tag_id: uuid.UUID | None = None
    campaign_tag_confidence: float | None = None
    campaign_tag_reason: str | None = None
    campaign_tag_assignment_source: CampaignTagAssignmentSource | None = None
    campaign_tag_classified_at: datetime | None = None
    campaign_classification_status: CampaignClassificationStatus = CampaignClassificationStatus.PENDING
    video_url: str | None = None
    media_items: list[MediaItem] = []
    keyframe_urls: list[str] = []
    keyframe_status: str = "NOT_APPLICABLE"

    # DB 컬럼은 nullable JSON이라 미설정 행은 NULL(=Python None)이다 — 빈 리스트로 정규화해
    # 프론트가 항상 배열을 받을 수 있게 한다(null 체크를 프론트 곳곳에 흩뿌리지 않기 위함).
    @field_validator("media_items", "keyframe_urls", mode="before")
    @classmethod
    def _default_empty_list(cls, v: object) -> object:
        return v or []


class AdOut(_AdMediaAndCampaignFields):
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
    # Part C — Ad Detail Drawer: 분석 상태를 노출해 "비주얼 분석 대기/실패"를 보여줄 수 있게 한다.
    analysis_status: str
    analysis_error: str | None

    @property
    def survival_days(self) -> int:
        return max((self.last_seen_at - self.first_seen_at).days, 0)


class AdWithCompetitorOut(AdOut):
    """프로젝트 전체 Ad 목록(성능 최적화용 신규 엔드포인트)에서 브랜드명을 함께 반환한다."""

    competitor_name: str


class DashboardMetrics(BaseModel):
    project_id: uuid.UUID
    new_count: int
    active_count: int
    inactive_count: int
    visual_type_ratio: dict[str, int]
    # §6-1 성능 최적화(Gallery Lazy Load) — 전체 Ad row를 가져오지 않고도 갤러리 개수를 보여주기
    # 위한 값. new_count+active_count+inactive_count와 항상 동일하다(이 세 상태가 is_archived=false
    # 소재를 정확히 분할하므로) — 별도 쿼리 없이 파생시킨다. Gallery의 "현재 추적 소재 N개"와
    # 동일한 기준(Ad.is_archived == false)을 사용한다.
    live_ad_count: int


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


class ChangedAdOut(_AdMediaAndCampaignFields):
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
    # 기간(Range) 조회에서만 채워진다 — 동일 광고가 기간 내 여러 이벤트를 가질 때 각각을 구분하기
    # 위함. 단일 날짜 조회(get_ad_changes)는 이 필드를 채우지 않는다(항상 None) — 이미 date로
    # 스코프됐으므로 불필요.
    event_date: date | None = None


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


class AdHistoryEvent(BaseModel):
    """Part C-03 — Ad Detail Drawer의 event history 한 줄."""

    model_config = ConfigDict(from_attributes=True)

    event_type: AdChangeEventType
    event_date: date
    survival_days_at_event: int | None = None


class AdHistoryResponse(BaseModel):
    ad_id: uuid.UUID
    events: list[AdHistoryEvent]


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


# ── 기간(주간) 조회 API (additive, 2026-09) ─────────────────────────────────

class CollectionRunSummary(BaseModel):
    """범위 내 실제 CollectionRun 시도만 status별로 집계한 값 — "시도 안 함"(해당 날짜가
    dates_with_collection에 없음)과 "시도했지만 실패"(failed에 포함)를 명확히 구분한다.
    (경쟁사×날짜) 그리드를 억지로 채워 단일 SUCCESS/PARTIAL/FAILED/NO_RECORD 값으로 뭉개지 않는다 —
    자동수집을 켜지 않은 날의 "기록 없음"이 "실패"처럼 보이는 것을 방지하기 위함."""

    success: int
    partial: int
    failed: int


class AdChangesRangeResponse(BaseModel):
    project_id: uuid.UUID
    start_date: date
    end_date: date
    competitor_id: uuid.UUID | None
    collection_run_summary: CollectionRunSummary
    dates_with_collection: list[date]
    latest_collection_at: datetime | None
    history_available_from: date | None
    baseline_discovered_count: int
    summary: AdChangeSummary
    started_ads: list[ChangedAdOut]
    reactivated_ads: list[ChangedAdOut]
    stopped_ads: list[ChangedAdOut]
    # unique 광고 기준 집계(§6-1) — 동일 광고가 기간 내 STARTED+REACTIVATED를 모두 가져도 1회만
    # 카운트한다. 변화 목록(started_ads 등)은 event 기준으로 dedupe하지 않는다.
    visual_pattern: dict[str, int]
    # 캠페인 태그 이름이 아니라 campaign_tag_id(str) 또는 "NEEDS_REVIEW"를 키로 사용한다 — 프론트가
    # 프로젝트의 캠페인 태그 목록과 join해 이름을 표시한다. 재분류 시 과거 기간 집계도 함께 바뀐다
    # (현재 태그 분류 기준으로 항상 재계산 — docs/DATA_SEMANTICS.md 참고).
    campaign_mix: dict[str, int]


# ── 성능 최적화용 통합 조회 API (additive, 2026-09) ─────────────────────────

class ProjectSummaryOut(BaseModel):
    """랜딩 페이지 프로젝트 카드용 — 기존 listProjects+N×(listCompetitors+getDashboard) 조합을
    단일 호출로 대체한다(§13 성능 최적화). 값의 의미는 기존 조합과 동일하다."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    status: ProjectStatus
    auto_collect_enabled: bool
    created_at: datetime
    competitor_count: int
    active_ad_count: int

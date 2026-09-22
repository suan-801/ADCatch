export type AdStatus = "NEW" | "ACTIVE" | "INACTIVE";
export type VisualType = "PERSON" | "PRODUCT" | "TEXT_HEAVY" | "GRAPHIC";
export type AdFormat = "IMAGE" | "VIDEO" | "CAROUSEL";
export type ProjectStatus = "ACTIVE" | "PAUSED";

// ── Campaign Tag 자동 분류 (additive) ────────────────────────────────────
// assignment_source("누가 지정했는가")와 classification_status("상태")는 서로 다른 축이다 —
// NEEDS_REVIEW는 상태이지 지정 주체가 아니다.
export type CampaignTagAssignmentSource = "AI" | "USER";
export type CampaignClassificationStatus = "PENDING" | "SUCCESS" | "NEEDS_REVIEW" | "FAILED";

export interface CampaignTag {
  id: string;
  project_id: string;
  name: string;
  definition: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

// §2-1 — "기존 광고 반영" 결과. reset_count만으로는 상태를 온전히 표현하지 못한다(태그가 없던
// 시절 생성된 광고는 이미 PENDING이라 reset 대상이 아니지만 여전히 "반영 대상"이다).
export interface CampaignTagReclassifyResult {
  reset_count: number;
  already_pending_count: number;
  total_target_count: number;
}

// §2-2 — "이번 재분류의 진행률"이 아니라 "현재 프로젝트 소재 분류 상태" 스냅샷.
export interface CampaignTagClassificationStatusSummary {
  pending: number;
  success: number;
  needs_review: number;
  failed: number;
}

// §2-3 — "지금 재분류 실행"(bounded batch) 결과.
export interface CampaignTagProcessPendingResult {
  processed: number;
  succeeded: number;
  needs_review: number;
  still_pending: number;
  failed: number;
  quota_stopped: boolean;
  pending_remaining: number;
}

// §9/§10 — 대시보드 "분석 업데이트"(Gemini Vision, visual_type) 버튼 결과. campaign-tags의
// process-pending과 동일한 모양(needs_review 필드만 없음 — visual 분석은 SUCCESS/FAILED뿐).
export interface VisualAnalysisProcessPendingResult {
  processed: number;
  succeeded: number;
  still_pending: number;
  failed: number;
  quota_stopped: boolean;
  pending_remaining: number;
}

// ── VIDEO/CAROUSEL 미디어 메타데이터 (additive) ─────────────────────────
export interface MediaItem {
  type: "image" | "video";
  url: string;
  preview_url: string | null;
}

export type KeyframeStatus = "NOT_APPLICABLE" | "PENDING" | "SUCCESS" | "FAILED";

// 여러 화면(Ad Detail Drawer, 기간별 변화 카드)이 공유하는 라벨 — 중복 정의 방지.
export const FORMAT_LABEL: Record<string, string> = { IMAGE: "이미지", VIDEO: "영상", CAROUSEL: "캐러셀" };
export const VISUAL_LABEL: Record<string, string> = {
  PERSON: "인물",
  PRODUCT: "제품",
  TEXT_HEAVY: "텍스트 중심",
  GRAPHIC: "그래픽",
};

export interface Project {
  id: string;
  name: string;
  status: ProjectStatus;
  auto_collect_enabled: boolean;
  created_at: string;
}

export interface Competitor {
  id: string;
  project_id: string;
  name: string;
  ad_library_url: string;
  page_id: string | null;
  // DEPRECATED — Brand Model Simplification 이후 UI/집계 어디에서도 사용하지 않는다.
  // 하위호환을 위해 API 응답에는 남아있다.
  is_own_brand: boolean;
  created_at: string;
}

export type AnalysisStatus = "PENDING" | "SUCCESS" | "FAILED";

export interface Ad {
  id: string;
  competitor_id: string;
  ad_archive_id: string;
  status: AdStatus;
  visual_type: VisualType | null;
  format: AdFormat | null;
  image_url: string | null;
  copy_text: string | null;
  cta_text: string | null;
  first_seen_at: string;
  last_seen_at: string;
  // 소재상의 실제 집행 시작일 (모르면 null) — first_seen_at(ADCatcher가 처음 관측한 시점)과는 다른 개념.
  source_started_at: string | null;
  consecutive_inactive_days: number;
  is_archived: boolean;
  // Part C/A — Gemini 비주얼 분석 상태. PENDING/FAILED여도 광고 자체는 Gallery에 정상 표시한다(A-09).
  analysis_status: AnalysisStatus;
  analysis_error: string | null;
  // Campaign Tag 자동 분류 (additive) — 사용자가 직접 수정한 값(USER)이 AI 값보다 항상 우선한다.
  campaign_tag_id: string | null;
  campaign_tag_confidence: number | null;
  campaign_tag_reason: string | null;
  campaign_tag_assignment_source: CampaignTagAssignmentSource | null;
  campaign_tag_classified_at: string | null;
  campaign_classification_status: CampaignClassificationStatus;
  // VIDEO/CAROUSEL 미디어 메타데이터 (additive) — image_url은 기존과 동일하게 대표 썸네일 1장.
  video_url: string | null;
  media_items: MediaItem[];
  keyframe_urls: string[];
  keyframe_status: KeyframeStatus;
}

// Part C-03 — Ad Detail Drawer의 event history.
export interface AdHistoryEvent {
  event_type: AdChangeEventType;
  event_date: string;
  survival_days_at_event: number | null;
}

export interface AdHistoryResponse {
  ad_id: string;
  events: AdHistoryEvent[];
}

export interface DashboardMetrics {
  project_id: string;
  new_count: number;
  active_count: number;
  inactive_count: number;
  visual_type_ratio: Partial<Record<VisualType, number>>;
  // §6-1 Gallery Lazy Load — 전체 Ad row 없이 "현재 추적 소재 N개"를 보여주기 위한 값.
  live_ad_count: number;
}

export function survivalDays(ad: Ad): number {
  const first = new Date(ad.first_seen_at).getTime();
  const last = new Date(ad.last_seen_at).getTime();
  return Math.max(Math.round((last - first) / (1000 * 60 * 60 * 24)), 0);
}

// P0-06: source_started_at(소재의 실제 집행 시작일)을 알면 "집행 N일", 모르면(=ADCatcher가
// 처음 관측한 시점부터만 셀 수 있음) "추적 N일"로 구분해서 보여준다. 둘을 같은 것처럼 섞지 않는다.
export function runningDays(ad: Ad): { days: number; label: "집행" | "추적" } {
  if (ad.source_started_at) {
    const start = new Date(ad.source_started_at).getTime();
    const end = new Date(ad.last_seen_at).getTime();
    return { days: Math.max(Math.round((end - start) / (1000 * 60 * 60 * 24)), 0), label: "집행" };
  }
  return { days: survivalDays(ad), label: "추적" };
}

// 서버(app/services/collection_history.py)와 동일하게 KST 캘린더 날짜를 기준으로 삼는다.
export function todayKst(): string {
  const kst = new Date(Date.now() + 9 * 60 * 60 * 1000);
  return kst.toISOString().slice(0, 10);
}

// ── Daily Ad Change History (additive) ──────────────────────────────────
export type AdChangeEventType = "STARTED" | "STOPPED" | "REACTIVATED" | "BASELINE_DISCOVERED";
export type CollectionStatus = "SUCCESS" | "PARTIAL" | "FAILED" | "NO_RECORD";

export interface ChangedAd extends Ad {
  event_type: AdChangeEventType;
  competitor_name: string;
  // P1-01: 이 이벤트가 발생한 순간에 고정된 집행/추적 일수. null이면(구 이벤트) 라이브 계산으로 폴백.
  survival_days_at_event: number | null;
  // 기간(Range) 조회에서만 채워진다 — 동일 광고가 기간 내 여러 이벤트를 가질 때 구분하기 위함.
  // 단일 날짜 조회(getAdChanges)는 항상 null.
  event_date: string | null;
}

export interface AdChangeSummary {
  started: number;
  reactivated: number;
  stopped: number;
}

// P0-15: 프로젝트 단위 하나의 값으로 뭉개지 않고, 브랜드별 상태 분포를 함께 제공한다.
export interface CollectionStatusSummary {
  success: number;
  partial: number;
  failed: number;
  no_record: number;
}

export interface AdChangesResponse {
  project_id: string;
  date: string;
  competitor_id: string | null;
  collection_status: CollectionStatus;
  collection_summary: CollectionStatusSummary;
  history_available_from: string | null;
  baseline_discovered_count: number;
  summary: AdChangeSummary;
  started_ads: ChangedAd[];
  reactivated_ads: ChangedAd[];
  stopped_ads: ChangedAd[];
  visual_pattern: Partial<Record<VisualType, number>>;
}

export interface CollectionFreshness {
  project_id: string;
  latest_run_at: string | null;
  total_competitors: number;
  // 하위호환: SUCCESS + PARTIAL 합계.
  healthy_competitors: number;
  // P0-16: PARTIAL을 SUCCESS와 동일하게 표시하지 않기 위한 세부 분해.
  success_competitors: number;
  partial_competitors: number;
  partial_competitor_names: string[];
  failed_competitor_names: string[];
}

// P0-16: "오늘"을 하드코딩하지 않고 실제 날짜 관계(오늘/어제/그 이전)를 KST 기준으로 표시한다.
export function formatRelativeKstTime(iso: string): string {
  const d = new Date(iso);
  const kst = new Date(d.getTime() + 9 * 60 * 60 * 1000);
  const time = `${String(kst.getUTCHours()).padStart(2, "0")}:${String(kst.getUTCMinutes()).padStart(2, "0")}`;

  const dateStr = kst.toISOString().slice(0, 10);
  const today = todayKst();
  const yesterday = (() => {
    const t = new Date(Date.now() + 9 * 60 * 60 * 1000);
    t.setUTCDate(t.getUTCDate() - 1);
    return t.toISOString().slice(0, 10);
  })();

  if (dateStr === today) return `오늘 ${time}`;
  if (dateStr === yesterday) return `어제 ${time}`;
  const [, month, day] = dateStr.split("-");
  return `${Number(month)}월 ${Number(day)}일 ${time}`;
}

// ── 기간(주간) 조회 API (additive) ───────────────────────────────────────
// (경쟁사×날짜) 그리드로 억지로 채운 단일 SUCCESS/PARTIAL/FAILED/NO_RECORD 값 대신, 실제
// CollectionRun 시도만 status별로 집계한다 — "자동수집 안 켠 날"의 기록 없음이 "실패"처럼
// 보이지 않게 하기 위함. 프론트는 이 값과 기존 CollectionFreshness를 함께 보여준다.
export interface CollectionRunSummary {
  success: number;
  partial: number;
  failed: number;
}

export interface AdChangesRangeResponse {
  project_id: string;
  start_date: string;
  end_date: string;
  competitor_id: string | null;
  collection_run_summary: CollectionRunSummary;
  dates_with_collection: string[];
  latest_collection_at: string | null;
  history_available_from: string | null;
  baseline_discovered_count: number;
  summary: AdChangeSummary;
  started_ads: ChangedAd[];
  reactivated_ads: ChangedAd[];
  stopped_ads: ChangedAd[];
  // 2026-09 개정 — "선택 기간에 한 번이라도 실제 라이브로 관측된(AdObservation 기준) unique 광고
  // 수". visual_pattern/campaign_mix 값의 합과 항상 같다. STARTED/REACTIVATED 이벤트가 없어도
  // 계속 라이브였던 광고까지 포함한다(이전엔 이 광고들이 빠져 비주얼 패턴이 텅 비어 보였다).
  alive_ad_count: number;
  // alive_ad_count와 동일한 분모. visual_type이 없는 광고는 "UNANALYZED" 키로 명시한다(조용히
  // 제외하지 않음 — VisualType 외 문자열 키가 있을 수 있어 Record<string, number>로 넓힌다).
  visual_pattern: Record<string, number>;
  // 캠페인 태그 id(string) 또는 "NEEDS_REVIEW"/"UNCLASSIFIED"를 키로 사용 — 프로젝트의 캠페인
  // 태그 목록과 join해 이름을 표시한다. 재분류 시 과거 기간 집계도 함께 바뀐다(현재 태그 분류
  // 기준으로 항상 재계산).
  campaign_mix: Record<string, number>;
}

// ── 성능 최적화용 통합 조회 API (additive) ───────────────────────────────
export interface ProjectSummary extends Project {
  competitor_count: number;
  active_ad_count: number;
}

export interface SyncResult {
  competitor_id: string;
  new_ads: number;
  reactivated_or_kept_active: number;
  newly_inactive: number;
  newly_archived: number;
  // 이 경쟁사의 "첫 성공 수집"이었는지, snapshot이 완전했는지 — Baseline CTA는
  // is_baseline && snapshot_complete 일 때만 보여준다.
  is_baseline: boolean;
  snapshot_complete: boolean;
}

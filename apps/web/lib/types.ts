export type AdStatus = "NEW" | "ACTIVE" | "INACTIVE";
export type VisualType = "PERSON" | "PRODUCT" | "TEXT_HEAVY" | "GRAPHIC";
export type AdFormat = "IMAGE" | "VIDEO" | "CAROUSEL";
export type ProjectStatus = "ACTIVE" | "PAUSED";

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

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
  is_own_brand: boolean;
  created_at: string;
}

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
}

export interface AdChangeSummary {
  started: number;
  reactivated: number;
  stopped: number;
}

export interface AdChangesResponse {
  project_id: string;
  date: string;
  competitor_id: string | null;
  collection_status: CollectionStatus;
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
  healthy_competitors: number;
  failed_competitor_names: string[];
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

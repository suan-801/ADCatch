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

// ── Daily Ad Change History (additive) ──────────────────────────────────
export type AdChangeEventType = "STARTED" | "STOPPED" | "REACTIVATED";
export type CollectionStatus = "SUCCESS" | "FAILED" | "NO_RECORD";

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
  summary: AdChangeSummary;
  started_ads: ChangedAd[];
  reactivated_ads: ChangedAd[];
  stopped_ads: ChangedAd[];
  visual_pattern: Partial<Record<VisualType, number>>;
}

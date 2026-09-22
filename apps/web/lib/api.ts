import type {
  Ad,
  AdChangesRangeResponse,
  AdChangesResponse,
  AdHistoryResponse,
  CampaignTag,
  Competitor,
  CollectionFreshness,
  DashboardMetrics,
  Project,
  ProjectSummary,
  SyncResult,
} from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// Viewer/Admin 권한: Admin 세션은 HttpOnly 쿠키로 유지되므로(비밀번호/토큰을 localStorage 등에
// 저장하지 않는다) 모든 요청에 credentials: "include"가 필요하다. 로컬 개발(localhost:3000 →
// localhost:8000)은 same-site라 문제 없이 동작하고, frontend/backend가 다른 도메인으로 배포되면
// (예: Vercel) ADMIN_COOKIE_SAMESITE=none + Secure=true, CORS_ALLOWED_ORIGINS에 정확한 프론트
// origin을 등록해야 한다 (apps/api/.env.example 참고).
class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!res.ok) {
    if (res.status === 401 && typeof window !== "undefined") {
      // Admin 세션 만료/부재 — AuthContext가 이 이벤트를 듣고 isAdmin을 내린다.
      window.dispatchEvent(new CustomEvent("adcatcher:admin-unauthorized"));
    }
    throw new ApiError(`API ${path} failed: ${res.status} ${await res.text()}`, res.status);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  // §13-2 성능 최적화 — 랜딩 페이지 카드용, listProjects+N×(listCompetitors+getDashboard) 대체.
  listProjectsSummary: () => request<ProjectSummary[]>("/projects/summary"),
  createProject: (name: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  updateProject: (projectId: string, payload: { auto_collect_enabled?: boolean }) =>
    request<Project>(`/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: async (projectId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: "DELETE", credentials: "include" });
    if (!res.ok) {
      if (res.status === 401 && typeof window !== "undefined") {
        window.dispatchEvent(new CustomEvent("adcatcher:admin-unauthorized"));
      }
      throw new ApiError(`API /projects/${projectId} delete failed: ${res.status} ${await res.text()}`, res.status);
    }
  },

  getProject: (projectId: string) => request<Project>(`/projects/${projectId}`),

  listCompetitors: (projectId: string) =>
    request<Competitor[]>(`/projects/${projectId}/competitors`),
  // P0-20/P0-21: 새 클라이언트는 is_own_brand를 보내지 않는다(브랜드 구분 UI 제거).
  createCompetitor: (projectId: string, payload: { name: string; ad_library_url: string }) =>
    request<Competitor>(`/projects/${projectId}/competitors`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDashboard: (projectId: string) =>
    request<DashboardMetrics>(`/projects/${projectId}/dashboard`),
  getFreshness: (projectId: string) =>
    request<CollectionFreshness>(`/projects/${projectId}/dashboard/freshness`),

  listAds: (competitorId: string) => request<Ad[]>(`/competitors/${competitorId}/ads`),
  // §13-1 성능 최적화 — 브랜드별 listAds() N회 호출 대신 프로젝트 전체를 1회로 조회한다.
  // 기존 listAds(competitorId)는 삭제하지 않고 그대로 유지한다.
  listProjectAds: (projectId: string) =>
    request<(Ad & { competitor_name: string })[]>(`/projects/${projectId}/ads`),
  collectNow: (competitorId: string) =>
    request<SyncResult>(`/competitors/${competitorId}/ads/collect`, { method: "POST" }),
  getAdHistory: (adId: string) => request<AdHistoryResponse>(`/ads/${adId}/history`),
  updateAdCampaignTag: (adId: string, campaignTagId: string) =>
    request<Ad>(`/ads/${adId}/campaign-tag`, {
      method: "PATCH",
      body: JSON.stringify({ campaign_tag_id: campaignTagId }),
    }),

  getAdChanges: (projectId: string, params: { date: string; competitorId?: string }) => {
    const qs = new URLSearchParams({ date: params.date });
    if (params.competitorId) qs.set("competitor_id", params.competitorId);
    return request<AdChangesResponse>(`/projects/${projectId}/ad-changes?${qs.toString()}`);
  },
  // §6 — 기간(주간) 조회. 기존 getAdChanges(단일 날짜)는 그대로 유지된다.
  getAdChangesRange: (
    projectId: string,
    params: { startDate: string; endDate: string; competitorId?: string },
  ) => {
    const qs = new URLSearchParams({ start_date: params.startDate, end_date: params.endDate });
    if (params.competitorId) qs.set("competitor_id", params.competitorId);
    return request<AdChangesRangeResponse>(`/projects/${projectId}/ad-changes/range?${qs.toString()}`);
  },

  listCampaignTags: (projectId: string, includeInactive = false) => {
    const qs = new URLSearchParams({ include_inactive: String(includeInactive) });
    return request<CampaignTag[]>(`/projects/${projectId}/campaign-tags?${qs.toString()}`);
  },
  createCampaignTag: (projectId: string, payload: { name: string; definition: string }) =>
    request<CampaignTag>(`/projects/${projectId}/campaign-tags`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateCampaignTag: (tagId: string, payload: { name?: string; definition?: string }) =>
    request<CampaignTag>(`/campaign-tags/${tagId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteCampaignTag: (tagId: string) =>
    request<CampaignTag>(`/campaign-tags/${tagId}`, { method: "DELETE" }),
  reclassifyCampaignTags: (projectId: string, includeUserAssigned = false) =>
    request<{ reset_count: number }>(`/projects/${projectId}/campaign-tags/reclassify`, {
      method: "POST",
      body: JSON.stringify({ include_user_assigned: includeUserAssigned }),
    }),

  adminLogin: (password: string) =>
    request<{ is_admin: boolean }>("/auth/admin", { method: "POST", body: JSON.stringify({ password }) }),
  adminLogout: () => request<{ is_admin: boolean }>("/auth/logout", { method: "POST" }),
  adminStatus: () => request<{ is_admin: boolean }>("/auth/status"),
};

export { ApiError };

import type { Ad, AdChangesResponse, Competitor, CollectionFreshness, DashboardMetrics, Project, SyncResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    throw new Error(`API ${path} failed: ${res.status} ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  updateProject: (projectId: string, payload: { auto_collect_enabled?: boolean }) =>
    request<Project>(`/projects/${projectId}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteProject: async (projectId: string): Promise<void> => {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, { method: "DELETE" });
    if (!res.ok) throw new Error(`API /projects/${projectId} delete failed: ${res.status} ${await res.text()}`);
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
  collectNow: (competitorId: string) =>
    request<SyncResult>(`/competitors/${competitorId}/ads/collect`, { method: "POST" }),

  getAdChanges: (projectId: string, params: { date: string; competitorId?: string }) => {
    const qs = new URLSearchParams({ date: params.date });
    if (params.competitorId) qs.set("competitor_id", params.competitorId);
    return request<AdChangesResponse>(`/projects/${projectId}/ad-changes?${qs.toString()}`);
  },
};

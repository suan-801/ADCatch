import type { Ad, Competitor, DashboardMetrics, Project } from "./types";

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

  listCompetitors: (projectId: string) =>
    request<Competitor[]>(`/projects/${projectId}/competitors`),
  createCompetitor: (projectId: string, payload: { name: string; ad_library_url: string; is_own_brand?: boolean }) =>
    request<Competitor>(`/projects/${projectId}/competitors`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getDashboard: (projectId: string) =>
    request<DashboardMetrics>(`/projects/${projectId}/dashboard`),

  listAds: (competitorId: string) => request<Ad[]>(`/competitors/${competitorId}/ads`),
  collectNow: (competitorId: string) =>
    request(`/competitors/${competitorId}/ads/collect`, { method: "POST" }),
};

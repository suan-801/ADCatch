"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Ad, Competitor, DashboardMetrics, Project } from "@/lib/types";
import { ProjectSidebar } from "@/components/project-sidebar";
import { CompetitorPanel } from "@/components/competitor-panel";
import { MetricCard } from "@/components/metric-card";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { AdGallery } from "@/components/ad-gallery";
import { MascotWidget } from "@/components/mascot-widget";

export default function DashboardPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [ads, setAds] = useState<Ad[]>([]);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listProjects()
      .then((data) => {
        setProjects(data);
        if (data.length > 0) setSelectedProjectId(data[0].id);
      })
      .catch((e) => setError(String(e)));
  }, []);

  useEffect(() => {
    if (!selectedProjectId) return;
    api.listCompetitors(selectedProjectId).then(setCompetitors).catch((e) => setError(String(e)));
    api.getDashboard(selectedProjectId).then(setMetrics).catch((e) => setError(String(e)));
    setSelectedCompetitorId(null);
    setAds([]);
  }, [selectedProjectId]);

  useEffect(() => {
    if (!selectedCompetitorId) return;
    api.listAds(selectedCompetitorId).then(setAds).catch((e) => setError(String(e)));
  }, [selectedCompetitorId]);

  const refreshDashboard = async () => {
    if (!selectedProjectId) return;
    setMetrics(await api.getDashboard(selectedProjectId));
  };

  const handleCreateProject = async (name: string) => {
    const project = await api.createProject(name);
    setProjects((prev) => [...prev, project]);
    setSelectedProjectId(project.id);
  };

  const handleCreateCompetitor = async (payload: { name: string; ad_library_url: string; is_own_brand: boolean }) => {
    if (!selectedProjectId) return;
    const competitor = await api.createCompetitor(selectedProjectId, payload);
    setCompetitors((prev) => [...prev, competitor]);
  };

  const handleCollect = async (competitorId: string) => {
    setCollecting(true);
    setError(null);
    try {
      await api.collectNow(competitorId);
      setAds(await api.listAds(competitorId));
      await refreshDashboard();
    } catch (e) {
      setError(String(e));
    } finally {
      setCollecting(false);
    }
  };

  return (
    <div className="flex min-h-screen">
      <ProjectSidebar
        projects={projects}
        selectedId={selectedProjectId}
        onSelect={setSelectedProjectId}
        onCreate={handleCreateProject}
      />

      <main className="min-w-0 flex-1 space-y-6 p-6">
        <header>
          <h1 className="text-lg font-semibold text-foreground">AdCatch</h1>
          <p className="text-xs text-muted">경쟁사 메타 소재 트래커</p>
        </header>

        {error && (
          <div className="rounded border border-status-inactive/30 bg-slate-50 p-3 text-xs text-status-inactive">
            API 연동 오류: {error}. 백엔드(apps/api)가 실행 중인지, .env의 NEXT_PUBLIC_API_URL이 맞는지 확인하세요.
          </div>
        )}

        {selectedProjectId && (
          <>
            {metrics && (
              <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <MetricCard label="신규 (New)" value={metrics.new_count} tone="new" />
                <MetricCard label="유지 (Active)" value={metrics.active_count} tone="active" />
                <MetricCard label="종료 (Inactive)" value={metrics.inactive_count} tone="inactive" />
                <VisualFormatChart ratio={metrics.visual_type_ratio} />
              </section>
            )}

            <CompetitorPanel
              competitors={competitors}
              selectedId={selectedCompetitorId}
              onSelect={setSelectedCompetitorId}
              onCreate={handleCreateCompetitor}
              onCollect={handleCollect}
              collecting={collecting}
            />

            <section>
              <h2 className="mb-3 text-sm font-semibold text-foreground">라이브 소재 갤러리 (생존기간 순)</h2>
              <AdGallery ads={ads} />
            </section>
          </>
        )}
      </main>

      <MascotWidget newCount={metrics?.new_count ?? 0} />
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Ad, Competitor, DashboardMetrics } from "@/lib/types";
import { CompetitorPanel } from "@/components/competitor-panel";
import { TodayCatch } from "@/components/today-catch";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { AdGallery } from "@/components/ad-gallery";
import { MascotWidget } from "@/components/mascot-widget";

// 브리핑 §19 hierarchy: 1) Today's Catch  2) Live Ad Gallery  3) Visual Pattern  4) Competitor Management.
// 광고 소재(Live Ad Gallery)를 Competitor 관리보다 위로 승격한다.
export default function CurrentDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();

  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [selectedCompetitorId, setSelectedCompetitorId] = useState<string | null>(
    searchParams.get("competitor"),
  );
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [ads, setAds] = useState<Ad[]>([]);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api.listCompetitors(projectId).then(setCompetitors).catch((e) => setError(String(e)));
    api.getDashboard(projectId).then(setMetrics).catch((e) => setError(String(e)));
  }, [projectId]);

  useEffect(() => {
    if (!selectedCompetitorId) return;
    api.listAds(selectedCompetitorId).then(setAds).catch((e) => setError(String(e)));
  }, [selectedCompetitorId]);

  const refreshDashboard = async () => {
    setMetrics(await api.getDashboard(projectId));
  };

  const handleCreateCompetitor = async (payload: { name: string; ad_library_url: string; is_own_brand: boolean }) => {
    const competitor = await api.createCompetitor(projectId, payload);
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

  const mascotMessage = collecting
    ? "지금 소재를 수집하고 있어요..."
    : (metrics?.new_count ?? 0) > 0
      ? `새로운 광고 ${metrics!.new_count}개를 잡았어요!`
      : competitors.length === 0
        ? "아직 경쟁사가 없어요. 등록해볼까요?"
        : "아직 새로운 광고가 없어요.";

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-xl border border-status-inactive/30 bg-slate-50 p-4 text-xs text-status-inactive">
          API 연동 오류: {error}. 백엔드(apps/api)가 실행 중인지, .env의 NEXT_PUBLIC_API_URL이 맞는지 확인하세요.
        </div>
      )}

      {metrics && <TodayCatch metrics={metrics} />}

      <section>
        <h2 className="mb-4 text-lg font-bold text-foreground">라이브 소재 갤러리 (생존기간 순)</h2>
        <AdGallery ads={ads} />
      </section>

      {metrics && (
        <section className="max-w-sm">
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

      <MascotWidget message={mascotMessage} happy={(metrics?.new_count ?? 0) > 0 && !collecting} />
    </div>
  );
}

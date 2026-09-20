"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Ad, AdChangesResponse, Competitor, DashboardMetrics } from "@/lib/types";
import { todayKst } from "@/lib/types";
import { useProjectContext } from "@/lib/project-context";
import { CompetitorPanel } from "@/components/competitor-panel";
import { CompetitorFilter } from "@/components/daily-changes/competitor-filter";
import { TodayCatch } from "@/components/today-catch";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { AdGallery } from "@/components/ad-gallery";
import { MascotWidget } from "@/components/mascot-widget";
import { BaselineCTA } from "@/components/baseline-cta";

// 브리핑 §19 hierarchy: 1) Today's Catch  2) Live Ad Gallery  3) Visual Pattern  4) Competitor Management.
// 광고 소재(Live Ad Gallery)를 Competitor 관리보다 위로 승격한다.
//
// P0-08: 갤러리는 경쟁사를 아무것도 고르지 않아도 항상 무언가를 보여준다 — 기본값은 "전체"
// (모든 경쟁사 소재를 합쳐서 표시), 필터는 갤러리 바로 위에 둔다. "지금 수집 실행"은 여전히
// 경쟁사 1곳을 대상으로만 동작하므로(Apify 호출 단위), 그 target 선택은 CompetitorPanel이
// 별도로 관리한다(중복이지만 두 선택의 의미가 달라 안전하게 분리했다).
export default function CurrentDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();

  const { project, updateAutoCollect } = useProjectContext();
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [galleryCompetitorId, setGalleryCompetitorId] = useState<string | null>(searchParams.get("competitor"));
  const [collectTargetId, setCollectTargetId] = useState<string | null>(searchParams.get("competitor"));
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [todayChanges, setTodayChanges] = useState<AdChangesResponse | null>(null);
  const [ads, setAds] = useState<(Ad & { competitor_name?: string })[]>([]);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // Initial Baseline + Daily Catch Opt-in UX — 방금 완료된 baseline 수집에 대한 CTA(있으면).
  const [baselineCta, setBaselineCta] = useState<{
    competitorName: string;
    adCount: number;
    alreadyEnabled: boolean;
  } | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api.listCompetitors(projectId).then(setCompetitors).catch((e) => setError(String(e)));
  }, [projectId]);

  const refreshDashboard = async () => {
    const [m, tc] = await Promise.all([
      api.getDashboard(projectId),
      api.getAdChanges(projectId, { date: todayKst() }),
    ]);
    setMetrics(m);
    setTodayChanges(tc);
  };

  useEffect(() => {
    if (!projectId) return;
    refreshDashboard().catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId]);

  useEffect(() => {
    if (competitors.length === 0) {
      setAds([]);
      return;
    }
    const nameOf = new Map(competitors.map((c) => [c.id, c.name]));

    if (galleryCompetitorId) {
      api
        .listAds(galleryCompetitorId)
        .then((list) => setAds(list.map((a) => ({ ...a, competitor_name: nameOf.get(a.competitor_id) }))))
        .catch((e) => setError(String(e)));
      return;
    }

    // "전체" — 경쟁사별로 병렬 조회 후 합친다 (별도 project-wide 엔드포인트 없이 기존 API 재사용).
    Promise.all(competitors.map((c) => api.listAds(c.id).catch(() => [])))
      .then((lists) =>
        setAds(lists.flat().map((a) => ({ ...a, competitor_name: nameOf.get(a.competitor_id) }))),
      )
      .catch((e) => setError(String(e)));
  }, [competitors, galleryCompetitorId]);

  const handleCreateCompetitor = async (payload: { name: string; ad_library_url: string }) => {
    const competitor = await api.createCompetitor(projectId, payload);
    setCompetitors((prev) => [...prev, competitor]);
    setCollectTargetId(competitor.id);
    // Part F-03/F-04: 기존 프로젝트에 브랜드를 새로 추가하면 첫 Collection을 바로 시작한다 —
    // 기존 handleCollect(baseline 판정 포함)를 그대로 재사용한다(별도 로직 신설 금지).
    await handleCollect(competitor.id);
  };

  const handleCollect = async (competitorId: string) => {
    setCollecting(true);
    setError(null);
    try {
      const result = await api.collectNow(competitorId);
      await refreshDashboard();

      // 갤러리가 "전체"거나 지금 수집한 경쟁사를 보고 있었다면, 그 경쟁사분만 갱신해 합친다.
      if (!galleryCompetitorId || galleryCompetitorId === competitorId) {
        const nameOf = new Map(competitors.map((c) => [c.id, c.name]));
        const refreshed = await api.listAds(competitorId);
        const merged = refreshed.map((a) => ({ ...a, competitor_name: nameOf.get(a.competitor_id) }));
        setAds((prev) => [...prev.filter((a) => a.competitor_id !== competitorId), ...merged]);
      }

      // §25: 실패/부분 수집은 절대 baseline 기준점으로 삼지 않는다 — SUCCESS(snapshot 완전)일 때만.
      if (result.is_baseline && result.snapshot_complete) {
        const name = competitors.find((c) => c.id === competitorId)?.name ?? "브랜드";
        setBaselineCta({
          competitorName: name,
          adCount: result.new_ads,
          alreadyEnabled: project?.auto_collect_enabled ?? false,
        });
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setCollecting(false);
    }
  };

  const handleOptIn = () => updateAutoCollect(true);

  const todayStartedCount = (todayChanges?.summary.started ?? 0) + (todayChanges?.summary.reactivated ?? 0);

  const mascotMessage = collecting
    ? "지금 소재를 수집하고 있어요..."
    : error
      ? "앗, 수집 중 문제가 생겼어요."
      : todayStartedCount > 0
        ? `새로운 광고 ${todayStartedCount}개를 잡았어요!`
        : competitors.length === 0
          ? "아직 브랜드가 없어요. 등록해볼까요?"
          : "아직 새로운 광고가 없어요.";

  // P1-03: 챗봇처럼 매번 자동으로 열지 않는다 — 의미 있는 순간(온보딩/수집 중/수집 완료·실패/
  // baseline 완료/신규 변화 감지)에만 이 key가 바뀌어 말풍선이 자동으로 열린다.
  const mascotOpenSignal = `${collecting ? "collecting" : "idle"}|${error ?? ""}|${
    baselineCta ? `${baselineCta.competitorName}-${baselineCta.adCount}` : ""
  }|${todayStartedCount}|${competitors.length === 0 ? "onboarding" : ""}`;

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-xl border border-status-inactive/30 bg-slate-50 p-4 text-xs text-status-inactive">
          API 연동 오류: {error}. 백엔드(apps/api)가 실행 중인지, .env의 NEXT_PUBLIC_API_URL이 맞는지 확인하세요.
        </div>
      )}

      {/* §13: Project Header ↓ Baseline CTA ↓ Live Ads. 사용자가 응답하지 않아도 아래 갤러리를 바로 본다. */}
      {baselineCta && (
        <BaselineCTA
          competitorName={baselineCta.competitorName}
          adCount={baselineCta.adCount}
          alreadyEnabled={baselineCta.alreadyEnabled}
          onOptIn={handleOptIn}
          onDismiss={() => setBaselineCta(null)}
        />
      )}

      {metrics && (
        <TodayCatch
          metrics={metrics}
          todayStartedCount={todayStartedCount}
          todayBaselineCount={todayChanges?.baseline_discovered_count ?? 0}
        />
      )}

      {/* Part F-01: 브랜드 등록은 광고 분석보다 앞단의 primary setup action이므로
          더 이상 페이지 최하단에 두지 않고 Live Ads 바로 위로 올린다. */}
      <CompetitorPanel
        competitors={competitors}
        selectedId={collectTargetId}
        onSelect={setCollectTargetId}
        onCreate={handleCreateCompetitor}
        onCollect={handleCollect}
        collecting={collecting}
      />

      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-bold text-foreground">
            라이브 소재 갤러리 <span className="ml-1 text-sm font-medium text-muted">{ads.length}</span>
          </h2>
          <CompetitorFilter competitors={competitors} selectedId={galleryCompetitorId} onSelect={setGalleryCompetitorId} />
        </div>
        <AdGallery ads={ads} />
      </section>

      {metrics && (
        <section className="max-w-sm">
          <VisualFormatChart ratio={metrics.visual_type_ratio} />
        </section>
      )}

      <MascotWidget
        message={mascotMessage}
        happy={todayStartedCount > 0 && !collecting}
        openSignal={mascotOpenSignal}
      />
    </div>
  );
}

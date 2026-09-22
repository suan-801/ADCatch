"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { Ad, AdChangesRangeResponse, AdChangesResponse, DashboardMetrics } from "@/lib/types";
import { todayKst } from "@/lib/types";
import { useProjectContext } from "@/lib/project-context";
import { CompetitorPanel } from "@/components/competitor-panel";
import { CompetitorFilter } from "@/components/daily-changes/competitor-filter";
import { WeekNav, weekRangeOf } from "@/components/daily-changes/week-nav";
import { TodayCatch } from "@/components/today-catch";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { PeriodChangesPanel } from "@/components/dashboard/period-changes-panel";
import { CampaignMixChart } from "@/components/dashboard/campaign-mix-chart";
import { AdGallery } from "@/components/gallery/ad-gallery";
import { GalleryFilters, DEFAULT_GALLERY_FILTERS, applyGalleryFilters } from "@/components/gallery/gallery-filters";
import { AdDetailDrawer } from "@/components/gallery/ad-detail-drawer";
import { MascotWidget } from "@/components/mascot-widget";
import { BaselineCTA } from "@/components/baseline-cta";

// §9 분석 중심 재편: ① 비주얼 패턴 요약 ② 기간별 광고 변화(주간 기본) ③ 캠페인 태그 구성 비중
// ④ 라이브 소재 갤러리 ⑤ 브랜드/수집 관리. 브랜드가 하나도 없는 새 프로젝트는 예외적으로 분석
// 섹션 대신 브랜드 등록 UI를 최우선으로 보여준다(텅 빈 분석 화면 4개를 지나게 하지 않기 위함).
export default function CurrentDashboardPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const searchParams = useSearchParams();

  const { project, updateAutoCollect, competitors, refreshCompetitors, campaignTags } = useProjectContext();
  const [galleryCompetitorId, setGalleryCompetitorId] = useState<string | null>(searchParams.get("competitor"));
  const [collectTargetId, setCollectTargetId] = useState<string | null>(searchParams.get("competitor"));
  const [metrics, setMetrics] = useState<DashboardMetrics | null>(null);
  const [todayChanges, setTodayChanges] = useState<AdChangesResponse | null>(null);
  const [range, setRange] = useState<AdChangesRangeResponse | null>(null);
  const [week, setWeek] = useState(() => weekRangeOf(todayKst()));
  const [ads, setAds] = useState<(Ad & { competitor_name?: string })[]>([]);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [galleryFilters, setGalleryFilters] = useState(DEFAULT_GALLERY_FILTERS);
  const [selectedAd, setSelectedAd] = useState<(Ad & { competitor_name?: string }) | null>(null);
  // §6 Gallery Lazy Load — 첫 진입 시 전체 Ad를 가져오지 않는다. 사용자가 "더 자세히 보기"를
  // 눌렀을 때 최초 1회만 fetch하고, 그 뒤로는 같은 페이지 session 안에서 재사용한다(접기/열기 시
  // 재요청하지 않음).
  const [galleryExpanded, setGalleryExpanded] = useState(false);
  const [galleryLoaded, setGalleryLoaded] = useState(false);
  const [galleryLoading, setGalleryLoading] = useState(false);
  // Initial Baseline + Daily Catch Opt-in UX — 방금 완료된 baseline 수집에 대한 CTA(있으면).
  const [baselineCta, setBaselineCta] = useState<{
    competitorName: string;
    adCount: number;
    alreadyEnabled: boolean;
  } | null>(null);

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

  // §6 — 기간(주간) 조회. galleryCompetitorId(브랜드 필터)와 week(기간) 상태를 그대로 공유한다 —
  // "지금 보고 있는 브랜드"의 기간별 변화를 함께 보여주는 것이 자연스럽다.
  useEffect(() => {
    if (!projectId) return;
    api
      .getAdChangesRange(projectId, {
        startDate: week.start,
        endDate: week.end,
        competitorId: galleryCompetitorId ?? undefined,
      })
      .then(setRange)
      .catch((e) => setError(String(e)));
  }, [projectId, week, galleryCompetitorId]);

  // 브랜드가 하나도 없어지면(삭제 등) 갤러리 상태도 초기화한다 — 다음에 브랜드가 생기면 다시
  // "더 자세히 보기"를 눌러야 fetch한다(자동으로 다시 불러오지 않음).
  useEffect(() => {
    if (competitors.length === 0) {
      setAds([]);
      setGalleryLoaded(false);
      setGalleryExpanded(false);
    }
  }, [competitors]);

  // §6 Gallery Lazy Load — "더 자세히 보기"를 눌렀을 때만(§13-1의 project-wide 엔드포인트를 그대로
  // 재사용) 최초 1회 호출한다. 첫 dashboard 진입 시에는 이 API를 전혀 호출하지 않는다.
  const handleToggleGallery = async () => {
    if (galleryExpanded) {
      setGalleryExpanded(false); // 카드 UI는 접어서 숨긴다 — ads state는 유지하므로 다시 열어도 재요청 없음
      return;
    }
    if (!galleryLoaded) {
      setGalleryLoading(true);
      setError(null);
      try {
        const list = await api.listProjectAds(projectId);
        setAds(list);
        setGalleryLoaded(true);
      } catch (e) {
        setError(String(e));
        setGalleryLoading(false);
        return;
      }
      setGalleryLoading(false);
    }
    setGalleryExpanded(true);
  };

  const handleCreateCompetitor = async (payload: { name: string; ad_library_url: string }) => {
    const competitor = await api.createCompetitor(projectId, payload);
    await refreshCompetitors();
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
      // §6-4: 상단 분석(metrics/range/freshness)은 항상 최신화하되, 사용자가 갤러리를 아직 열지
      // 않았다면 전체 Ad fetch는 하지 않는다.
      await refreshDashboard();
      if (galleryLoaded) {
        await api
          .listProjectAds(projectId)
          .then(setAds)
          .catch(() => {});
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

  const handleAdUpdated = (updated: Ad & { competitor_name?: string }) => {
    setAds((prev) => prev.map((a) => (a.id === updated.id ? { ...a, ...updated } : a)));
    setSelectedAd((prev) => (prev && prev.id === updated.id ? { ...prev, ...updated } : prev));
  };

  const filteredAds = applyGalleryFilters(ads, galleryFilters);

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

  const competitorLabel = galleryCompetitorId
    ? (competitors.find((c) => c.id === galleryCompetitorId)?.name ?? "전체")
    : "전체 브랜드";

  return (
    <div className="space-y-8">
      {error && (
        <div className="rounded-xl border border-status-inactive/30 bg-slate-50 p-4 text-xs text-status-inactive">
          API 연동 오류: {error}. 백엔드(apps/api)가 실행 중인지, .env의 NEXT_PUBLIC_API_URL이 맞는지 확인하세요.
        </div>
      )}

      {/* §13: Project Header ↓ Baseline CTA ↓ 분석/Live Ads. 사용자가 응답하지 않아도 아래를 바로 본다. */}
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

      {competitors.length === 0 ? (
        // 브랜드가 하나도 없으면 텅 빈 분석 섹션 4개를 보여주지 않고 등록 UI를 바로 노출한다.
        <CompetitorPanel
          competitors={competitors}
          selectedId={collectTargetId}
          onSelect={setCollectTargetId}
          onCreate={handleCreateCompetitor}
          onCollect={handleCollect}
          collecting={collecting}
        />
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <WeekNav
              start={week.start}
              end={week.end}
              onChange={(start, end) => setWeek({ start, end })}
              minDate={range?.history_available_from}
            />
            <CompetitorFilter competitors={competitors} selectedId={galleryCompetitorId} onSelect={setGalleryCompetitorId} />
          </div>

          {range && (
            <section className="max-w-sm">
              <VisualFormatChart ratio={range.visual_pattern} title="비주얼 패턴" />
            </section>
          )}

          {range && (
            <PeriodChangesPanel projectId={projectId} range={range} competitorLabel={competitorLabel} />
          )}

          {range && Object.keys(range.campaign_mix).length > 0 && (
            <section className="max-w-sm">
              <CampaignMixChart mix={range.campaign_mix} campaignTags={campaignTags} />
            </section>
          )}

          <section>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              {/* B-07: 필터가 걸려있으면 "필터결과 / 전체"로, 아니면 전체 개수만 보여준다.
                  §6 Gallery Lazy Load: 갤러리를 열기 전에는 전체 Ad row 없이도 DashboardMetrics의
                  live_ad_count(SQL COUNT 기반, Gallery와 동일하게 is_archived=false 기준)로 개수를
                  보여준다. */}
              <h2 className="text-lg font-bold text-foreground">
                라이브 소재 갤러리{" "}
                <span className="ml-1 text-sm font-medium text-muted">
                  {galleryLoaded
                    ? filteredAds.length === ads.length
                      ? ads.length
                      : `${filteredAds.length} / ${ads.length}`
                    : (metrics?.live_ad_count ?? "")}
                </span>
              </h2>
              {galleryExpanded && (
                <button
                  type="button"
                  onClick={handleToggleGallery}
                  className="text-xs font-semibold text-muted hover:text-foreground"
                >
                  접기 ↑
                </button>
              )}
            </div>

            {!galleryExpanded ? (
              <div className="rounded-2xl border border-dashed border-border p-8 text-center">
                <p className="text-sm text-muted">
                  {metrics ? `현재 추적 소재 ${metrics.live_ad_count}개` : "불러오는 중..."}
                  <br />
                  필터를 이용해 전체 광고 소재를 확인할 수 있습니다.
                </p>
                <button
                  type="button"
                  onClick={handleToggleGallery}
                  disabled={galleryLoading}
                  className="mt-4 rounded-full bg-brand px-5 py-2.5 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-60"
                >
                  {galleryLoading ? "소재를 불러오는 중..." : "더 자세히 보기 ↓"}
                </button>
              </div>
            ) : (
              <>
                {/* §6-5: 갤러리가 접혀 있을 때는 무거운 GalleryFilters를 아예 렌더링하지 않는다 —
                    "더 자세히 보기" 이후에만 노출한다. */}
                <div className="mb-4">
                  <GalleryFilters value={galleryFilters} onChange={setGalleryFilters} campaignTags={campaignTags} />
                </div>
                <AdGallery
                  ads={filteredAds}
                  totalCount={ads.length}
                  onCardClick={setSelectedAd}
                  campaignTags={campaignTags}
                />
              </>
            )}
          </section>

          {/* Part F-01: 브랜드 관리는 분석 섹션보다 아래로 내린다 — 메인 화면의 주인공은
              기간별 변화/비주얼 패턴/캠페인 구성이다(§9). */}
          <CompetitorPanel
            competitors={competitors}
            selectedId={collectTargetId}
            onSelect={setCollectTargetId}
            onCreate={handleCreateCompetitor}
            onCollect={handleCollect}
            collecting={collecting}
          />
        </>
      )}

      <MascotWidget
        message={mascotMessage}
        happy={todayStartedCount > 0 && !collecting}
        openSignal={mascotOpenSignal}
      />

      <AdDetailDrawer
        ad={selectedAd}
        onClose={() => setSelectedAd(null)}
        campaignTags={campaignTags}
        onAdUpdated={handleAdUpdated}
      />
    </div>
  );
}

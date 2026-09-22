"use client";

import { useEffect, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { api } from "@/lib/api";
import type { ProjectAdsFilterParams } from "@/lib/api";
import type { Ad, AdChangesRangeResponse, AdChangesResponse, DashboardMetrics } from "@/lib/types";
import { todayKst } from "@/lib/types";
import { useProjectContext } from "@/lib/project-context";
import { CompetitorPanel } from "@/components/competitor-panel";
import { CompetitorFilter } from "@/components/daily-changes/competitor-filter";
import { WeekNav, weekRangeOf } from "@/components/daily-changes/week-nav";
import { TodayCatch } from "@/components/today-catch";
import { VisualPatternPanel } from "@/components/dashboard/visual-pattern-panel";
import { PeriodChangesPanel } from "@/components/dashboard/period-changes-panel";
import { CampaignMixChart } from "@/components/dashboard/campaign-mix-chart";
import { AdGallery } from "@/components/gallery/ad-gallery";
import { GalleryFilters, DEFAULT_GALLERY_FILTERS, type GalleryFilterState } from "@/components/gallery/gallery-filters";
import { AdDetailDrawer } from "@/components/gallery/ad-detail-drawer";
import { MascotWidget } from "@/components/mascot-widget";
import { BaselineCTA } from "@/components/baseline-cta";

function filtersToParams(f: GalleryFilterState): ProjectAdsFilterParams {
  return {
    competitorId: f.competitorId !== "ALL" ? f.competitorId : undefined,
    status: f.status !== "ALL" ? f.status : undefined,
    format: f.format !== "ALL" ? f.format : undefined,
    visualType: f.visual !== "ALL" ? f.visual : undefined,
    campaignTagId: f.campaignTagId !== "ALL" ? f.campaignTagId : undefined,
    search: f.search.trim() || undefined,
  };
}

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
  const [selectedAd, setSelectedAd] = useState<(Ad & { competitor_name?: string }) | null>(null);
  // §11/§12 Gallery — "필터 먼저 → 조회하기" 구조. galleryFilters는 아직 적용되지 않은 draft이고,
  // appliedGalleryFilters는 마지막으로 실제 조회에 쓰인 필터(수집 후 refresh에 재사용). 3가지
  // 상태를 구분한다: A) 한 번도 조회하지 않음(gallerySearched=false), B) 조회했으나 접힘
  // (searched && !expanded), C) 펼쳐짐(searched && expanded) — A/B가 같은 UI로 보이던 문제를 고친다.
  const [galleryFilters, setGalleryFilters] = useState<GalleryFilterState>(DEFAULT_GALLERY_FILTERS);
  const [appliedGalleryFilters, setAppliedGalleryFilters] = useState<GalleryFilterState | null>(null);
  const [gallerySearched, setGallerySearched] = useState(false);
  const [galleryExpanded, setGalleryExpanded] = useState(false);
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
  // "지금 보고 있는 브랜드"의 기간별 변화를 함께 보여주는 것이 자연스럽다. 이 상태는 Gallery 자체의
  // 브랜드 필터(galleryFilters.competitorId)와는 별개다(분석 섹션 스코프 vs 갤러리 조회 조건).
  const refreshRange = () => {
    if (!projectId) return;
    api
      .getAdChangesRange(projectId, {
        startDate: week.start,
        endDate: week.end,
        competitorId: galleryCompetitorId ?? undefined,
      })
      .then(setRange)
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    refreshRange();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, week, galleryCompetitorId]);

  // 브랜드가 하나도 없어지면(삭제 등) 갤러리 상태도 초기화한다 — 다음에 브랜드가 생기면 다시
  // "조회하기"를 눌러야 fetch한다(자동으로 다시 불러오지 않음).
  useEffect(() => {
    if (competitors.length === 0) {
      setAds([]);
      setGallerySearched(false);
      setGalleryExpanded(false);
      setAppliedGalleryFilters(null);
    }
  }, [competitors]);

  // §11/§12 Gallery — "조회하기" 버튼을 눌렀을 때만 서버에 질의한다(§13 query param 필터). filter
  // 값을 바꾸는 것만으로는 절대 API 요청을 하지 않는다.
  const handleSearchGallery = async () => {
    setGalleryLoading(true);
    setError(null);
    try {
      const list = await api.listProjectAds(projectId, filtersToParams(galleryFilters));
      setAds(list);
      setAppliedGalleryFilters(galleryFilters);
      setGallerySearched(true);
      setGalleryExpanded(true);
    } catch (e) {
      setError(String(e));
    } finally {
      setGalleryLoading(false);
    }
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
      // §6-4: 상단 분석(metrics/range/freshness)은 항상 최신화하되, 사용자가 갤러리를 아직 조회하지
      // 않았다면 전체 Ad fetch는 하지 않는다. 이미 조회했다면 마지막으로 적용한 필터 그대로 재조회한다.
      await refreshDashboard();
      refreshRange();
      if (gallerySearched && appliedGalleryFilters) {
        await api
          .listProjectAds(projectId, filtersToParams(appliedGalleryFilters))
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

          {/* §2/§3 — 비주얼 패턴은 STARTED/REACTIVATED 이벤트가 아니라 "선택 기간에 실제로
              라이브였던 광고"(AdObservation 기준) 전체를 분모로 삼는다(docs/DATA_SEMANTICS.md §11). */}
          {range && <VisualPatternPanel projectId={projectId} range={range} onProcessed={refreshRange} />}

          {range && <PeriodChangesPanel projectId={projectId} range={range} competitorLabel={competitorLabel} />}

          {/* §4/§5 — 캠페인 패턴도 비주얼 패턴과 동일한 alive_ad_count 분모를 공유한다(절대 기준이
              갈라지지 않게 한다). alive_ad_count>0이면 항상 무언가(태그/검토 필요/미분류)로
              분류되므로, campaign_mix 존재 여부가 아니라 alive_ad_count로 렌더링 여부를 결정한다. */}
          {range && range.alive_ad_count > 0 && (
            <section className="max-w-sm">
              <CampaignMixChart mix={range.campaign_mix} campaignTags={campaignTags} />
            </section>
          )}

          <section>
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <h2 className="text-lg font-bold text-foreground">
                라이브 소재 갤러리{" "}
                <span className="ml-1 text-sm font-medium text-muted">
                  {gallerySearched ? ads.length : (metrics?.live_ad_count ?? "")}
                </span>
              </h2>
              {gallerySearched && (
                <button
                  type="button"
                  onClick={() => setGalleryExpanded((prev) => !prev)}
                  className="text-xs font-semibold text-muted hover:text-foreground"
                >
                  {galleryExpanded ? "접기 ↑" : "펼치기 ↓"}
                </button>
              )}
            </div>

            {!gallerySearched && (
              <p className="mb-3 text-xs text-muted">
                {metrics ? `현재 추적 소재 ${metrics.live_ad_count}개` : "불러오는 중..."} — 필터를 먼저 선택하고
                조회하기를 눌러주세요.
              </p>
            )}

            {/* §11: A(한 번도 조회 안 함)와 C(조회 후 펼침)에서만 필터 폼을 보여준다. B(조회했으나
                접힘)는 compact 헤더만 보이고 필터 폼/결과 그리드를 다시 보여주지 않는다. */}
            {(!gallerySearched || galleryExpanded) && (
              <>
                <div className="mb-3">
                  <GalleryFilters
                    value={galleryFilters}
                    onChange={setGalleryFilters}
                    competitors={competitors}
                    campaignTags={campaignTags}
                  />
                </div>
                <button
                  type="button"
                  onClick={handleSearchGallery}
                  disabled={galleryLoading}
                  className="mb-4 rounded-full bg-brand px-5 py-2 text-xs font-semibold text-white hover:opacity-90 disabled:opacity-60"
                >
                  {galleryLoading ? "조회 중..." : "조회하기"}
                </button>
              </>
            )}

            {gallerySearched && galleryExpanded && (
              <AdGallery
                ads={ads}
                totalCount={metrics?.live_ad_count ?? 0}
                onCardClick={setSelectedAd}
                campaignTags={campaignTags}
              />
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

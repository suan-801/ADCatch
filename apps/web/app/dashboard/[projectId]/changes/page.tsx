"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { AdChangesResponse, Competitor } from "@/lib/types";
import { todayKst } from "@/lib/types";
import { DateNav } from "@/components/daily-changes/date-nav";
import { CompetitorFilter } from "@/components/daily-changes/competitor-filter";
import { DailySummary } from "@/components/daily-changes/daily-summary";
import { ChangedAdSection } from "@/components/daily-changes/changed-ad-section";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { MascotWidget } from "@/components/mascot-widget";

// 브리핑 §35: 빈 상태 3종을 서로 다른 문구로 명확히 구분한다.
// P0-03: baseline 수집일은 "오늘 켠 광고"가 아니라 "처음 확인한 현재 집행 목록"으로 별도 안내한다.
function emptyStateMessage(result: AdChangesResponse): string | null {
  const hasChanges = result.summary.started + result.summary.reactivated + result.summary.stopped > 0;
  if (hasChanges) return null;
  if (result.baseline_discovered_count > 0) {
    return `현재 집행 중인 광고 ${result.baseline_discovered_count}개를 처음 확인했어요.`;
  }
  if (!result.history_available_from || result.date < result.history_available_from) {
    return "이 날짜는 추적 기능 적용 이전이라 광고 변화 기록을 제공하지 않아요.";
  }
  if (result.collection_status === "SUCCESS") return "이날은 광고 변화가 없었어요.";
  if (result.collection_status === "PARTIAL") return "이날은 일부 소재만 수집돼 변화 정보가 아직 없어요.";
  return "이 날짜에는 정상적인 수집 기록이 없습니다.";
}

export default function DailyChangesPage() {
  const { projectId } = useParams<{ projectId: string }>();

  const [date, setDate] = useState(todayKst);
  const [competitors, setCompetitors] = useState<Competitor[]>([]);
  const [competitorId, setCompetitorId] = useState<string | null>(null);
  const [result, setResult] = useState<AdChangesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api.listCompetitors(projectId).then(setCompetitors).catch(() => {});
  }, [projectId]);

  useEffect(() => {
    if (!projectId) return;
    setResult(null);
    api
      .getAdChanges(projectId, { date, competitorId: competitorId ?? undefined })
      .then(setResult)
      .catch((e) => setError(String(e)));
  }, [projectId, date, competitorId]);

  const competitorLabel = competitorId
    ? (competitors.find((c) => c.id === competitorId)?.name ?? "전체")
    : "전체 브랜드";

  const startedAndReactivated = result ? [...result.started_ads, ...result.reactivated_ads] : [];
  const message = emptyStateMessage(result ?? ({ summary: { started: 0, reactivated: 0, stopped: 0 } } as AdChangesResponse));

  const mascotMessage = !result
    ? "그날의 변화를 불러오고 있어요..."
    : result.summary.started + result.summary.reactivated > 0
      ? `이날 새 광고 ${result.summary.started + result.summary.reactivated}개를 잡았어요.`
      : result.summary.stopped > 0
        ? `이날은 ${result.summary.stopped}개 광고가 종료됐어요.`
        : "이날은 큰 변화가 없었어요.";

  // P1-03: "신규 변화 감지"일 때만 자동으로 말풍선을 연다 — 변화가 없는 날은 조용히 있는다.
  const hasChanges = !!result && result.summary.started + result.summary.reactivated + result.summary.stopped > 0;
  const mascotOpenSignal = hasChanges ? `${date}-${competitorId ?? "all"}` : undefined;

  return (
    <div className="space-y-8">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <DateNav date={date} onChange={setDate} minDate={result?.history_available_from} />
        <CompetitorFilter competitors={competitors} selectedId={competitorId} onSelect={setCompetitorId} />
      </div>

      {error && (
        <div className="rounded-xl border border-status-inactive/30 bg-slate-50 p-4 text-xs text-status-inactive">
          API 연동 오류: {error}
        </div>
      )}

      {result && (
        <>
          <DailySummary competitorLabel={competitorLabel} date={date} summary={result.summary} />

          {result.collection_status === "PARTIAL" && (result.summary.started + result.summary.reactivated) > 0 && (
            <p className="rounded-xl border border-brand/30 bg-brand-cream p-3 text-xs text-brand-dark">
              이날 수집은 일부만 완료됐어요 — &quot;끈 광고&quot; 수치는 이 날짜엔 집계되지 않았을 수 있어요.
            </p>
          )}

          {message ? (
            <p className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted">
              {message}
            </p>
          ) : (
            <>
              <ChangedAdSection title="켠 광고" ads={startedAndReactivated} />
              <ChangedAdSection title="끈 광고" ads={result.stopped_ads} />

              {Object.keys(result.visual_pattern).length > 0 && (
                <section className="max-w-sm">
                  <VisualFormatChart ratio={result.visual_pattern} title="오늘의 패턴" />
                </section>
              )}
            </>
          )}
        </>
      )}

      <MascotWidget
        message={mascotMessage}
        happy={(result?.summary.started ?? 0) > 0}
        openSignal={mascotOpenSignal}
      />
    </div>
  );
}

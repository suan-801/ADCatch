import type { DashboardMetrics } from "@/lib/types";

// 브리핑 §22: 동일 크기 KPI 카드 3개를 제거하고 NEW를 압도적 primary metric으로 강조.
//
// §23: "새로운 광고"는 Ad.status==NEW의 구조적 카운트(metrics.new_count)가 아니라, 오늘 실제
// STARTED/REACTIVATED된 개수(todayStartedCount, /ad-changes에서 옴)를 보여준다 — 그래야 baseline
// 수집 직후 "37개의 광고를 오늘 켰다"는 거짓 신호를 만들지 않는다. Ad.status 구조 자체는 바꾸지 않는다.
export function TodayCatch({
  metrics,
  todayStartedCount,
  todayBaselineCount,
}: {
  metrics: DashboardMetrics;
  todayStartedCount: number;
  todayBaselineCount: number;
}) {
  return (
    <div className="border-b border-border pb-8">
      <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-brand-dark">Today&apos;s Catch</p>
      <div className="mt-2 flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <span className="text-6xl font-extrabold leading-none tabular-nums text-foreground sm:text-7xl">
          {todayStartedCount}
        </span>
        <span className="text-lg font-semibold text-muted">새로운 광고</span>
      </div>

      {todayBaselineCount > 0 && (
        <p className="mt-2 text-xs text-muted">오늘 {todayBaselineCount}개 소재를 처음 확인했어요.</p>
      )}

      <div className="mt-5 flex flex-wrap gap-x-6 gap-y-2 text-sm">
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-status-active" />
          <b className="tabular-nums text-foreground">{metrics.active_count}</b>
          <span className="text-muted">ACTIVE</span>
        </span>
        <span className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-status-inactive" />
          <b className="tabular-nums text-foreground">{metrics.inactive_count}</b>
          <span className="text-muted">INACTIVE</span>
        </span>
      </div>
    </div>
  );
}

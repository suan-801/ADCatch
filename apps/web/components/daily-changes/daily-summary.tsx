import type { AdChangeSummary } from "@/lib/types";

function formatKoreanMonthDay(dateStr: string): string {
  const [, m, d] = dateStr.split("-");
  return `${parseInt(m, 10)}월 ${parseInt(d, 10)}일`;
}

// 브리핑 §31: 일반 Analytics Table이 아니라 "Daily Competitor Briefing" 톤.
// 개발 용어(STARTED/STOPPED)보다 "켠 광고"/"끈 광고"를 우선 사용한다.
export function DailySummary({
  competitorLabel,
  date,
  summary,
}: {
  competitorLabel: string;
  date: string;
  summary: AdChangeSummary;
}) {
  return (
    <div className="border-b border-border pb-8">
      <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-brand-dark">{competitorLabel}</p>
      <h2 className="mt-2 text-2xl font-extrabold leading-snug text-foreground sm:text-3xl">
        {formatKoreanMonthDay(date)},
        <br />
        이런 광고 변화가 있었어요.
      </h2>

      <div className="mt-6 flex flex-wrap gap-x-10 gap-y-4">
        <div>
          <p className="text-5xl font-extrabold tabular-nums text-foreground">{summary.started + summary.reactivated}</p>
          <p className="mt-1 text-sm font-semibold text-muted">켠 광고</p>
        </div>
        <div>
          <p className="text-5xl font-extrabold tabular-nums text-foreground">{summary.stopped}</p>
          <p className="mt-1 text-sm font-semibold text-muted">끈 광고</p>
        </div>
      </div>

      {(summary.started > 0 || summary.reactivated > 0) && (
        <p className="mt-4 text-xs text-muted">
          NEW {summary.started}
          {summary.reactivated > 0 && ` · REACTIVATED ${summary.reactivated}`}
        </p>
      )}
    </div>
  );
}

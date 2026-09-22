import Link from "next/link";
import type { AdChangesRangeResponse } from "@/lib/types";
import { ChangedAdSection } from "@/components/daily-changes/changed-ad-section";

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-3xl font-extrabold tabular-nums text-foreground">{value}</p>
      <p className="mt-1 text-xs font-semibold text-muted">{label}</p>
    </div>
  );
}

// §9 — 기간별 광고 변화를 메인 대시보드의 주인공으로 승격한다(갤러리가 아니라). 기존
// ChangedAdSection/ChangedAdCard를 그대로 재사용해 "동일 컴포넌트 재사용"으로 /changes 라우트와
// 일관성을 유지하고, "날짜별로 자세히 보기" 링크로 기존 단일 날짜 상세 화면과 연결한다
// (라우트를 삭제하지 않고 backward compatibility를 유지).
export function PeriodChangesPanel({
  projectId,
  range,
  competitorLabel,
}: {
  projectId: string;
  range: AdChangesRangeResponse;
  competitorLabel: string;
}) {
  const startedAndReactivated = [...range.started_ads, ...range.reactivated_ads];
  const hasChanges = range.summary.started + range.summary.reactivated + range.summary.stopped > 0;

  return (
    <section className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-foreground">
            기간별 광고 변화 <span className="ml-1 text-sm font-medium text-muted">{competitorLabel}</span>
          </h2>
        </div>
        <Link
          href={`/dashboard/${projectId}/changes`}
          className="text-xs font-semibold text-brand-dark hover:underline"
        >
          날짜별로 자세히 보기 →
        </Link>
      </div>

      <div className="flex flex-wrap gap-x-10 gap-y-3 rounded-2xl border border-border bg-white p-5">
        <Stat label="켠 광고" value={range.summary.started + range.summary.reactivated} />
        <Stat label="끈 광고" value={range.summary.stopped} />
        <Stat label="기존 집행 확인" value={range.baseline_discovered_count} />
      </div>

      {/* collection_run_summary는 (경쟁사×날짜) 그리드를 채우지 않고 "실제 수집 시도"만 집계한다 —
          자동수집을 켜지 않은 날의 "기록 없음"을 "실패"처럼 보여주지 않기 위함. */}
      <p className="text-xs text-muted">
        이 기간 {range.dates_with_collection.length}일 수집됨
        {range.collection_run_summary.failed > 0 && ` · 수집 실패 ${range.collection_run_summary.failed}건`}
        {range.collection_run_summary.partial > 0 && ` · 부분 수집 ${range.collection_run_summary.partial}건`}
      </p>

      {hasChanges ? (
        <div className="space-y-6">
          <ChangedAdSection title="켠 광고" ads={startedAndReactivated} />
          <ChangedAdSection title="끈 광고" ads={range.stopped_ads} />
        </div>
      ) : (
        <p className="rounded-2xl border border-dashed border-border p-8 text-center text-sm text-muted">
          이 기간엔 광고 변화가 없었어요.
        </p>
      )}
    </section>
  );
}

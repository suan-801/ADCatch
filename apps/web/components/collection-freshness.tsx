"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { formatRelativeKstTime, type CollectionFreshness } from "@/lib/types";

// P0-09/P0-16: "이 데이터를 믿어도 되는가"를 Project Header 근처에서 바로 보여준다.
// PARTIAL(부분 수집)을 SUCCESS와 동일한 "정상"으로 뭉개지 않고, FAILED와도 구분해서 보여준다.
// latest_run_at도 항상 "오늘"로 하드코딩하지 않고 실제 날짜 관계(오늘/어제/그 이전)로 표시한다.
export function CollectionFreshnessBadge({ projectId }: { projectId: string }) {
  const [freshness, setFreshness] = useState<CollectionFreshness | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api.getFreshness(projectId).then(setFreshness).catch(() => {});
  }, [projectId]);

  if (!freshness || freshness.total_competitors === 0) return null;

  const allSuccess = freshness.success_competitors === freshness.total_competitors;
  const hasFailed = freshness.failed_competitor_names.length > 0;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span
        className={`h-1.5 w-1.5 rounded-full ${allSuccess ? "bg-status-active" : hasFailed ? "bg-status-inactive" : "bg-brand"}`}
      />
      {allSuccess ? (
        <span className="font-semibold text-foreground">● 정상 수집</span>
      ) : (
        <span className="font-semibold text-brand-dark">
          {freshness.success_competitors} / {freshness.total_competitors} 정상 수집
        </span>
      )}
      {freshness.latest_run_at && (
        <span className="text-muted">{formatRelativeKstTime(freshness.latest_run_at)}</span>
      )}
      {freshness.partial_competitors > 0 && (
        <span className="text-brand-dark">
          ⚠ {freshness.partial_competitors}개 부분 수집 (종료 광고 판정 보류)
        </span>
      )}
      {hasFailed && (
        <span className="text-status-inactive">
          ⚠ {freshness.failed_competitor_names.slice(0, 3).join(", ")} 수집 실패
        </span>
      )}
    </div>
  );
}

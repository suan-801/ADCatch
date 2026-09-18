"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { CollectionFreshness } from "@/lib/types";

function formatTime(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

// P0-09: "이 데이터를 믿어도 되는가"를 Project Header 근처에서 바로 보여준다.
export function CollectionFreshnessBadge({ projectId }: { projectId: string }) {
  const [freshness, setFreshness] = useState<CollectionFreshness | null>(null);

  useEffect(() => {
    if (!projectId) return;
    api.getFreshness(projectId).then(setFreshness).catch(() => {});
  }, [projectId]);

  if (!freshness || freshness.total_competitors === 0) return null;

  const allHealthy = freshness.healthy_competitors === freshness.total_competitors;

  return (
    <div className="flex flex-wrap items-center gap-2 text-xs">
      <span className={`h-1.5 w-1.5 rounded-full ${allHealthy ? "bg-status-active" : "bg-brand"}`} />
      {allHealthy ? (
        <span className="font-semibold text-foreground">최신 수집 완료</span>
      ) : (
        <span className="font-semibold text-brand-dark">
          {freshness.healthy_competitors} / {freshness.total_competitors} 수집 완료
        </span>
      )}
      {freshness.latest_run_at && <span className="text-muted">오늘 {formatTime(freshness.latest_run_at)}</span>}
      {!allHealthy && freshness.failed_competitor_names.length > 0 && (
        <span className="text-muted">
          — {freshness.failed_competitor_names.slice(0, 3).join(", ")} 수집 실패
        </span>
      )}
    </div>
  );
}

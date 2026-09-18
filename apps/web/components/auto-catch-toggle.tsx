"use client";

import { useState } from "react";
import type { Project } from "@/lib/types";

// §17/18: Baseline CTA에서 "나중에"를 눌렀어도 언제든 다시 켤 수 있어야 한다.
// 큰 배지가 아니라 subtle한 텍스트 토글로 — Project Header 영역에 배치.
export function AutoCatchToggle({
  project,
  onToggle,
}: {
  project: Project;
  onToggle: (enabled: boolean) => Promise<void>;
}) {
  const [loading, setLoading] = useState(false);
  const enabled = project.auto_collect_enabled;

  const handleClick = async () => {
    setLoading(true);
    try {
      await onToggle(!enabled);
    } finally {
      setLoading(false);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={loading}
      className="flex items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-xs font-medium text-muted transition-colors hover:border-brand/40 hover:text-foreground disabled:opacity-60"
    >
      <span className={`h-1.5 w-1.5 rounded-full ${enabled ? "bg-status-active" : "bg-border"}`} />
      {loading ? "변경 중..." : enabled ? "매일 변화 CATCH 중" : "자동 추적 꺼짐"}
    </button>
  );
}

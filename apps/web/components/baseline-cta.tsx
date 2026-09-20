"use client";

import { useEffect, useState } from "react";

// Initial Baseline + Daily Catch Opt-in UX.
// §14: consent modal이 아니라 Dashboard inline panel — 사용자는 답하지 않아도 갤러리를 바로 볼 수 있다.
// §21: 이미 auto_collect_enabled=true인 프로젝트에 새 경쟁사를 추가한 경우엔 opt-in 버튼 없이
//      작은 확인만 보여준다 (alreadyEnabled=true).
export function BaselineCTA({
  competitorName,
  adCount,
  alreadyEnabled,
  onOptIn,
  onDismiss,
}: {
  competitorName: string;
  adCount: number;
  alreadyEnabled: boolean;
  onOptIn: () => Promise<void>;
  onDismiss: () => void;
}) {
  const [state, setState] = useState<"idle" | "submitting" | "success">("idle");

  useEffect(() => {
    if (alreadyEnabled) {
      const t = setTimeout(onDismiss, 4000);
      return () => clearTimeout(t);
    }
  }, [alreadyEnabled, onDismiss]);

  useEffect(() => {
    if (state !== "success") return;
    const t = setTimeout(onDismiss, 2500);
    return () => clearTimeout(t);
  }, [state, onDismiss]);

  const handleOptIn = async () => {
    setState("submitting");
    try {
      await onOptIn();
      setState("success");
    } catch {
      setState("idle");
    }
  };

  // §21 — 이미 opt-in된 프로젝트에 경쟁사 추가: 버튼 없는 작은 확인 배너
  if (alreadyEnabled) {
    return (
      <div className="flex items-center gap-2 rounded-xl border border-border bg-white px-4 py-3 text-sm text-foreground">
        <span className="text-status-active">✓</span>
        <span>
          {competitorName} 광고 {adCount}개를 기준으로 저장했어요.
        </span>
      </div>
    );
  }

  return (
    <div className="relative overflow-hidden rounded-2xl border border-border bg-white p-6 sm:p-8">
      <div className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-brand/5 blur-3xl" />

      {state === "success" ? (
        <div className="flex items-center gap-4">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/mascot/catcher-hero.webp" alt="캐쳐" className="w-16 shrink-0 sm:w-20" />
          <div>
            <p className="text-base font-extrabold text-status-active">✓ 매일 변화를 CATCH할게요</p>
            <p className="mt-1 text-sm text-muted">새로운 광고가 등장하거나 사라지면 ADCatcher가 기록해둘게요.</p>
          </div>
        </div>
      ) : (
        <div className="flex flex-col items-start gap-6 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex-1">
            <p className="text-xs font-extrabold uppercase tracking-[0.2em] text-brand-dark">Baseline Ready</p>

            <p className="mt-3 flex items-baseline gap-2">
              <span className="text-5xl font-extrabold leading-none tabular-nums text-foreground sm:text-6xl">
                {adCount}
              </span>
              <span className="text-lg font-semibold text-foreground">개의 광고를 수집했어요!</span>
            </p>

            <p className="mt-3 text-sm text-muted">
              현재 {competitorName}에서 집행 중인 광고를 기준으로 저장했어요.
            </p>

            <p className="mt-5 text-lg font-bold text-foreground">앞으로 매일 변화를 CATCH하시겠어요?</p>
            <p className="mt-1 text-xs text-muted">매일 자동으로 새로운 광고와 종료된 광고를 확인해드려요.</p>

            <div className="mt-5 flex flex-col items-start gap-2 sm:flex-row sm:items-center">
              <button
                type="button"
                onClick={handleOptIn}
                disabled={state === "submitting"}
                className="w-full rounded-full bg-brand px-6 py-3 text-sm font-bold text-white transition-transform hover:opacity-90 active:translate-y-0 disabled:opacity-60 sm:w-auto sm:hover:-translate-y-px"
              >
                {state === "submitting" ? "설정 중..." : "매일 변화 CATCH하기"}
              </button>
              <button
                type="button"
                onClick={onDismiss}
                disabled={state === "submitting"}
                className="rounded-full px-4 py-2 text-sm font-medium text-muted hover:text-foreground disabled:opacity-60"
              >
                나중에
              </button>
            </div>
          </div>

          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/mascot/catcher-hero.webp"
            alt="캐쳐"
            className="w-20 shrink-0 self-center sm:w-28"
          />
        </div>
      )}
    </div>
  );
}

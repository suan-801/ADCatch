"use client";

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";
import type { AdChangesRangeResponse } from "@/lib/types";
import { VisualFormatChart } from "@/components/visual-format-chart";
import { useAuth } from "@/lib/auth-context";

const AUTO_CONTINUE_DELAY_MS = 800;

// §5 — 비주얼 패턴은 항상 "선택 기간 라이브 소재 기준"으로 표시한다(캠페인 패턴과 동일한 분모).
const SUBTITLE = "선택 기간 라이브 소재 기준";

// §9/§10 — alive_ad_count > 0인데 미분석(UNANALYZED) 소재가 있으면 Admin 전용 "분석 업데이트"
// 버튼을 보여준다. 한 HTTP 요청은 항상 bounded batch만 처리하고(서버가 상한 강제), 프론트가
// pending_remaining>0인 동안 짧은 delay를 두고 자동으로 다음 batch를 호출한다 — 브라우저가 작업
// queue를 소유하는 구조는 아니다(페이지를 떠나면 이 루프도 멈추고, 남은 PENDING은 기존 Daily
// Scheduler가 계속 처리한다). 캠페인 태그의 "지금 재분류 실행"과 동일한 UX 원칙을 재사용한다.
export function VisualPatternPanel({
  projectId,
  range,
  onProcessed,
}: {
  projectId: string;
  range: AdChangesRangeResponse;
  /** 배치가 끝날 때마다(또는 완전히 끝난 뒤) Range API를 다시 fetch해 비주얼 패턴을 갱신하도록
   * 부모에게 알린다. */
  onProcessed: () => void;
}) {
  const { isAdmin } = useAuth();
  const [running, setRunning] = useState(false);
  const [cumulative, setCumulative] = useState<{ processed: number; succeeded: number; failed: number } | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const stopRef = useRef(false);

  useEffect(() => {
    return () => {
      stopRef.current = true; // 페이지를 떠나면(unmount) 다음 batch를 예약하지 않는다.
    };
  }, []);

  const unanalyzedCount = range.visual_pattern.UNANALYZED ?? 0;
  const showUpdateButton = isAdmin && range.alive_ad_count > 0 && unanalyzedCount > 0;

  const runLoop = async () => {
    stopRef.current = false;
    setRunning(true);
    setStatusMessage(null);
    let totals = { processed: 0, succeeded: 0, failed: 0 };
    setCumulative(totals);

    try {
      for (;;) {
        if (stopRef.current) {
          setStatusMessage("중지했어요. 나머지는 Daily Scheduler가 처리해요.");
          break;
        }
        const result = await api.processPendingVisualAnalysis(projectId);
        totals = {
          processed: totals.processed + result.processed,
          succeeded: totals.succeeded + result.succeeded,
          failed: totals.failed + result.failed,
        };
        setCumulative(totals);
        onProcessed();

        if (result.quota_stopped) {
          setStatusMessage("Gemini 할당량 초과로 중단됐어요. 나머지는 Daily Scheduler가 처리해요.");
          break;
        }
        if (result.pending_remaining === 0) {
          setStatusMessage("완료했어요.");
          break;
        }
        if (stopRef.current) {
          setStatusMessage("중지했어요. 나머지는 Daily Scheduler가 처리해요.");
          break;
        }
        await new Promise((resolve) => setTimeout(resolve, AUTO_CONTINUE_DELAY_MS));
      }
    } catch (e) {
      setStatusMessage(`오류가 발생해 중단했어요: ${e}`);
    } finally {
      setRunning(false);
    }
  };

  return (
    <section className="max-w-sm space-y-2">
      <VisualFormatChart
        ratio={range.visual_pattern}
        title="비주얼 패턴"
        subtitle={SUBTITLE}
        emptyMessage="선택 기간에 수집된 라이브 소재가 없습니다."
      />
      {showUpdateButton && (
        <div className="rounded-2xl border border-border bg-white p-3">
          <p className="text-xs text-muted">미분석 {unanalyzedCount}개</p>
          <div className="mt-2 flex gap-2">
            <button
              type="button"
              onClick={runLoop}
              disabled={running}
              className="rounded-full bg-brand px-3 py-1.5 text-xs font-semibold text-white disabled:opacity-60"
            >
              {running ? "분석 중..." : "분석 업데이트"}
            </button>
            {running && (
              <button
                type="button"
                onClick={() => {
                  stopRef.current = true;
                }}
                className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-foreground"
              >
                중지
              </button>
            )}
          </div>
          {cumulative && (
            <p className="mt-2 text-xs text-muted">
              처리 {cumulative.processed}개(성공 {cumulative.succeeded} · 실패 {cumulative.failed})
            </p>
          )}
          {statusMessage && <p className="mt-1 text-xs text-muted">{statusMessage}</p>}
        </div>
      )}
    </section>
  );
}

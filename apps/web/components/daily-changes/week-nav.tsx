"use client";

import { useRef } from "react";
import { todayKst } from "@/lib/types";
import { shiftDate } from "@/components/daily-changes/date-nav";

// 한국 업무 기준 주차: 월요일 ~ 일요일. date-nav.tsx의 shiftDate()를 그대로 재사용한다.
export function mondayOf(dateStr: string): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  const day = date.getUTCDay(); // 0=일 ... 6=토
  const diffToMonday = day === 0 ? -6 : 1 - day;
  date.setUTCDate(date.getUTCDate() + diffToMonday);
  return date.toISOString().slice(0, 10);
}

export function weekRangeOf(dateStr: string): { start: string; end: string } {
  const start = mondayOf(dateStr);
  return { start, end: shiftDate(start, 6) };
}

function formatKorean(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${y}.${m}.${d}`;
}

/**
 * §5(2026-09 사용자 피드백) — 기간 선택 UI 단순화. 이전엔 "‹ 2026.09.14 ~ 2026.09.20 ›" pill과
 * "[시작일] ~ [종료일]" 버튼이 같은 기간을 두 번 보여줘 어색했다. 하나의 컨트롤로 합쳐 시작일/
 * 종료일 실제 날짜가 처음부터 보이고, 각 날짜를 누르면 바로 그 date picker가 열린다.
 *
 * 기존 기능은 모두 유지한다: ‹/›는 7일 단위 이동, 기본 월~일, start/end를 직접 바꾸면 커스텀
 * range도 가능, start<=end / end<=today / minDate 이전 선택 방지. weekRangeOf/mondayOf/shiftDate
 * 헬퍼를 그대로 재사용한다.
 */
export function WeekNav({
  start,
  end,
  onChange,
  minDate,
}: {
  start: string;
  end: string;
  onChange: (start: string, end: string) => void;
  minDate?: string | null;
}) {
  const today = todayKst();
  const startInputRef = useRef<HTMLInputElement>(null);
  const endInputRef = useRef<HTMLInputElement>(null);

  const goToPrevWeek = () => {
    const { start: s, end: e } = weekRangeOf(shiftDate(start, -7));
    onChange(s, e);
  };
  const goToNextWeek = () => {
    const { start: s, end: e } = weekRangeOf(shiftDate(start, 7));
    onChange(s, e);
  };
  const atMin = !!minDate && start <= minDate;
  const atMax = end >= today;

  const openPicker = (ref: React.RefObject<HTMLInputElement | null>) => {
    const input = ref.current;
    if (!input) return;
    if (typeof input.showPicker === "function") input.showPicker();
    else input.focus();
  };

  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-white p-1">
      <button
        type="button"
        onClick={goToPrevWeek}
        disabled={atMin}
        aria-label="이전 주"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
      >
        ‹
      </button>

      <button
        type="button"
        onClick={() => openPicker(startInputRef)}
        className="rounded-lg px-2 py-1 text-sm font-bold text-foreground hover:bg-slate-100"
      >
        {formatKorean(start)}
      </button>
      <input
        ref={startInputRef}
        type="date"
        value={start}
        min={minDate ?? undefined}
        max={end}
        onChange={(e) => e.target.value && onChange(e.target.value, end)}
        className="sr-only"
        aria-label="시작일 선택"
        tabIndex={-1}
      />

      <span className="text-sm text-muted">~</span>

      <button
        type="button"
        onClick={() => openPicker(endInputRef)}
        className="rounded-lg px-2 py-1 text-sm font-bold text-foreground hover:bg-slate-100"
      >
        {formatKorean(end)}
      </button>
      <input
        ref={endInputRef}
        type="date"
        value={end}
        min={start}
        max={today}
        onChange={(e) => e.target.value && onChange(start, e.target.value)}
        className="sr-only"
        aria-label="종료일 선택"
        tabIndex={-1}
      />

      <button
        type="button"
        onClick={goToNextWeek}
        disabled={atMax}
        aria-label="다음 주"
        className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
      >
        ›
      </button>
    </div>
  );
}

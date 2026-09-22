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
 * 기본 조회 단위는 "주간"(월~일). ‹ 이전 주 / 다음 주 › 로 이동하고, 네이티브 date input 2개로
 * 커스텀 범위(시작일/종료일)도 선택할 수 있다 — 향후 "기간 선택"을 넓히기 쉬운 구조.
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
    <div className="flex flex-wrap items-center gap-2">
      <div className="flex items-center gap-1 rounded-full border border-border bg-white p-1">
        <button
          type="button"
          onClick={goToPrevWeek}
          disabled={atMin}
          aria-label="이전 주"
          className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
        >
          ‹
        </button>
        <span className="px-1 text-sm font-bold text-foreground">
          {formatKorean(start)} ~ {formatKorean(end)}
        </span>
        <button
          type="button"
          onClick={goToNextWeek}
          disabled={atMax}
          aria-label="다음 주"
          className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
        >
          ›
        </button>
      </div>

      <div className="flex items-center gap-1 text-xs text-muted">
        <button
          type="button"
          onClick={() => openPicker(startInputRef)}
          className="rounded-full border border-border px-2.5 py-1 hover:border-brand hover:text-brand-dark"
        >
          시작일
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
        <span>~</span>
        <button
          type="button"
          onClick={() => openPicker(endInputRef)}
          className="rounded-full border border-border px-2.5 py-1 hover:border-brand hover:text-brand-dark"
        >
          종료일
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
      </div>
    </div>
  );
}

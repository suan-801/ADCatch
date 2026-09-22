"use client";

import { useRef } from "react";
import { todayKst } from "@/lib/types";

// 버그 수정: 기존엔 new Date(`${dateStr}T00:00:00`)로 "로컬 시간대" 기준 Date를 만들고
// toISOString()으로 "UTC" 기준 문자열을 뽑아썼다 — KST(UTC+9)에서는 이 둘이 어긋나서
// 하루씩(때로는 이틀씩) 밀렸다. 이제는 끝까지 UTC 기준(Date.UTC/setUTCDate)으로만 계산해
// 로컬 시간대와 무관하게 항상 정확히 deltaDays만큼만 이동한다.
// WeekNav(components/daily-changes/week-nav.tsx)가 그대로 재사용한다 — 새 날짜 연산 로직을
// 중복 작성하지 않는다.
export function shiftDate(dateStr: string, deltaDays: number): string {
  const [y, m, d] = dateStr.split("-").map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  date.setUTCDate(date.getUTCDate() + deltaDays);
  return date.toISOString().slice(0, 10);
}

function formatKorean(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${y}. ${m}. ${d}`;
}

// "‹ 날짜 › [Calendar]" — 커스텀 캘린더 위젯 대신 네이티브 date input을 쓴다.
// 버그 수정: 투명 input을 label 위에 겹쳐두고 "클릭하면 열리겠지" 기대하는 방식은
// Chrome에서 신뢰도 있게 열리지 않았다(빈 클릭으로 처리되는 경우가 있음). 대신 실제
// input은 시각적으로만 숨기고(sr-only), 날짜 텍스트 버튼의 onClick에서
// input.showPicker()를 명시적으로 호출해 항상 확실하게 네이티브 달력을 띄운다.
// 장식용 달력 이모지는 제거 — 버튼 자체가 실제로 달력을 여는 기능을 하므로 불필요하다.
export function DateNav({
  date,
  onChange,
  minDate,
}: {
  date: string;
  onChange: (date: string) => void;
  /** 추적 기능이 적용되기 이전 날짜 — 이 날짜보다 이전은 선택/이동할 수 없다. */
  minDate?: string | null;
}) {
  const today = todayKst();
  const atMin = !!minDate && date <= minDate;
  const inputRef = useRef<HTMLInputElement>(null);

  const openPicker = () => {
    const input = inputRef.current;
    if (!input) return;
    if (typeof input.showPicker === "function") {
      input.showPicker();
    } else {
      input.focus();
    }
  };

  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-white p-1">
      <button
        type="button"
        onClick={() => onChange(shiftDate(date, -1))}
        disabled={atMin}
        aria-label="이전 날짜"
        className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
      >
        ‹
      </button>

      <button
        type="button"
        onClick={openPicker}
        className="rounded-lg px-2 py-1 text-sm font-bold text-foreground hover:bg-slate-100"
      >
        {formatKorean(date)}
      </button>
      <input
        ref={inputRef}
        type="date"
        value={date}
        min={minDate ?? undefined}
        max={today}
        onChange={(e) => e.target.value && onChange(e.target.value)}
        className="sr-only"
        aria-label="날짜 선택"
        tabIndex={-1}
      />

      <button
        type="button"
        onClick={() => onChange(shiftDate(date, 1))}
        disabled={date >= today}
        aria-label="다음 날짜"
        className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground disabled:opacity-30"
      >
        ›
      </button>
    </div>
  );
}

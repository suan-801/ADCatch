"use client";

function shiftDate(dateStr: string, deltaDays: number): string {
  const d = new Date(`${dateStr}T00:00:00`);
  d.setDate(d.getDate() + deltaDays);
  return d.toISOString().slice(0, 10);
}

function formatKorean(dateStr: string): string {
  const [y, m, d] = dateStr.split("-");
  return `${y}. ${m}. ${d}`;
}

// 브리핑 §30: "‹ 날짜 › [Calendar]" — 커스텀 캘린더 위젯 대신 네이티브 date input을 얇게 감싸
// 동일한 기능(이전/다음/직접 선택)을 제공한다.
export function DateNav({ date, onChange }: { date: string; onChange: (date: string) => void }) {
  const today = new Date().toISOString().slice(0, 10);

  return (
    <div className="flex items-center gap-1 rounded-full border border-border bg-white p-1">
      <button
        type="button"
        onClick={() => onChange(shiftDate(date, -1))}
        aria-label="이전 날짜"
        className="flex h-8 w-8 items-center justify-center rounded-full text-muted hover:bg-slate-100 hover:text-foreground"
      >
        ‹
      </button>

      <label className="relative flex items-center px-2 text-sm font-bold text-foreground">
        {formatKorean(date)}
        <input
          type="date"
          value={date}
          max={today}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0"
          aria-label="날짜 선택"
        />
      </label>

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

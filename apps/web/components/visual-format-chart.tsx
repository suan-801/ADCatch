import type { VisualType } from "@/lib/types";

// 카테고리 4개 고정 순서 + dataviz 스킬 검증된 카테고리 팔레트 slot 1~4 (라이트 모드).
// node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light → ALL CHECKS PASS
// (Contrast WARN → 관련 relief rule에 따라 막대 옆에 라벨을 항상 노출한다)
const ORDER: { key: VisualType; label: string; color: string }[] = [
  { key: "PERSON", label: "인물", color: "#2a78d6" },
  { key: "PRODUCT", label: "제품", color: "#eb6834" },
  { key: "TEXT_HEAVY", label: "텍스트 중심", color: "#1baf7a" },
  { key: "GRAPHIC", label: "그래픽", color: "#eda100" },
];

export function VisualFormatChart({ ratio }: { ratio: Partial<Record<VisualType, number>> }) {
  const total = ORDER.reduce((sum, { key }) => sum + (ratio[key] ?? 0), 0);

  return (
    <div className="rounded border border-border bg-white p-4">
      <p className="text-xs font-medium text-muted">비주얼 포맷 비율</p>
      <div className="mt-3 space-y-2">
        {ORDER.map(({ key, label, color }) => {
          const count = ratio[key] ?? 0;
          const pct = total > 0 ? Math.round((count / total) * 100) : 0;
          return (
            <div key={key} className="flex items-center gap-3">
              <span className="w-24 shrink-0 text-xs text-foreground">{label}</span>
              <div className="h-2 flex-1 rounded bg-slate-100">
                <div
                  className="h-2 rounded"
                  style={{ width: `${pct}%`, backgroundColor: color }}
                />
              </div>
              <span className="w-14 shrink-0 text-right text-xs tabular-nums text-muted">
                {count}건 ({pct}%)
              </span>
            </div>
          );
        })}
        {total === 0 && <p className="text-xs text-muted">아직 태깅된 소재가 없습니다.</p>}
      </div>
    </div>
  );
}

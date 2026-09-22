import type { VisualType } from "@/lib/types";

// 카테고리 4개 고정 순서 + dataviz 스킬 검증된 카테고리 팔레트 slot 1~4 (라이트 모드).
// node scripts/validate_palette.js "#2a78d6,#eb6834,#1baf7a,#eda100" --mode light → ALL CHECKS PASS
const ORDER: { key: VisualType; label: string; color: string }[] = [
  { key: "PERSON", label: "인물", color: "#2a78d6" },
  { key: "PRODUCT", label: "제품", color: "#eb6834" },
  { key: "TEXT_HEAVY", label: "텍스트 중심", color: "#1baf7a" },
  { key: "GRAPHIC", label: "그래픽", color: "#eda100" },
];

// 브리핑 §26/§34: 작은 progress bar 대시보드가 아니라, 가장 많은 패턴을 먼저 크게 강조하는
// editorial 구조. title을 받아 현재 대시보드("비주얼 패턴")와 Daily Changes("오늘의 패턴")에서
// 그대로 재사용한다(Gemini 재호출 없이 기존 visual_type 카운트만 aggregate).
//
// 2026-09: ratio에 "UNANALYZED" 키가 있으면(§3 — alive 기준 집계는 visual_type 없는 광고를 조용히
// 빼지 않는다) 4개 카테고리 아래에 "미분석"으로 별도 표시한다. 퍼센트 분모는 UNANALYZED를 포함한
// 전체이므로, "태깅 완료 광고만 보면 100%"처럼 왜곡되지 않는다. changes/page.tsx의 기존 event 기준
// ratio(UNANALYZED 키 없음)는 이 로직에 영향받지 않고 기존과 동일하게 렌더링된다(하위 호환).
export function VisualFormatChart({
  ratio,
  title = "비주얼 패턴",
  subtitle,
  emptyMessage = "아직 태깅된 소재가 없습니다.",
}: {
  ratio: Record<string, number>;
  title?: string;
  subtitle?: string;
  emptyMessage?: string;
}) {
  const analyzedTotal = ORDER.reduce((sum, { key }) => sum + (ratio[key] ?? 0), 0);
  const unanalyzed = ratio.UNANALYZED ?? 0;
  const total = analyzedTotal + unanalyzed;
  const pct = (value: number) => (total > 0 ? Math.round((value / total) * 100) : 0);

  if (total === 0) {
    return (
      <div className="rounded-2xl border border-border bg-white p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
        {subtitle && <p className="mt-0.5 text-[11px] text-muted">{subtitle}</p>}
        <p className="mt-3 text-xs text-muted">{emptyMessage}</p>
      </div>
    );
  }

  if (analyzedTotal === 0) {
    // alive 소재는 있지만 전부 아직 Gemini 분석 전 — "태깅된 소재가 없다"는 표현과는 다른 상태다.
    return (
      <div className="rounded-2xl border border-border bg-white p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
        {subtitle && <p className="mt-0.5 text-[11px] text-muted">{subtitle}</p>}
        <p className="mt-3 text-xs text-muted">선택 기간 라이브 소재가 아직 비주얼 분석되지 않았습니다.</p>
      </div>
    );
  }

  const sorted = [...ORDER].sort((a, b) => (ratio[b.key] ?? 0) - (ratio[a.key] ?? 0));
  const [top, ...rest] = sorted;

  return (
    <div className="rounded-2xl border border-border bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {subtitle && <p className="mt-0.5 text-[11px] text-muted">{subtitle}</p>}

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-sm font-bold text-foreground">{top.label}</span>
        <span className="text-3xl font-extrabold tabular-nums" style={{ color: top.color }}>
          {pct(ratio[top.key] ?? 0)}%
        </span>
      </div>

      <div className="mt-3 space-y-1.5 border-t border-border pt-3">
        {rest.map(({ key, label, color }) => (
          <div key={key} className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: color }} />
              {label}
            </span>
            <span className="tabular-nums text-foreground">{pct(ratio[key] ?? 0)}%</span>
          </div>
        ))}
        {unanalyzed > 0 && (
          <div className="flex items-center justify-between text-xs">
            <span className="flex items-center gap-1.5 text-muted">
              <span className="h-1.5 w-1.5 rounded-full bg-slate-300" />
              미분석
            </span>
            <span className="tabular-nums text-foreground">{pct(unanalyzed)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}

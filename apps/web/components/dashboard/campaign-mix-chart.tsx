import type { CampaignTag } from "@/lib/types";

// visual-format-chart.tsx와 동일한 editorial 스타일(가장 큰 카테고리를 크게 강조 + 나머지는
// 작은 리스트)을 재사용한다. 캠페인 태그는 프로젝트마다 개수가 다르므로(고정 4종인 비주얼
// 패턴과 다름) 태그 목록 순서를 기준으로 팔레트를 순환 배정한다.
const PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#7c5cff", "#0ea5a4"];
const NEEDS_REVIEW_COLOR = "#94a3b8"; // muted — 검토 필요
const UNCLASSIFIED_COLOR = "#cbd5e1"; // 더 옅은 muted — 미분류(PENDING/FAILED/태그 없음)

// 2026-09: §5 — 비주얼 패턴과 동일한 분모(선택 기간 alive ads unique 기준)를 쓴다는 것을 subtitle로
// 명시한다. 절대 하나는 event 기준, 다른 하나는 다른 기준으로 갈라지지 않는다.
const SUBTITLE = "선택 기간 라이브 소재 기준 · 중복 소재 제외";

export function CampaignMixChart({
  mix,
  campaignTags,
  title = "캠페인 패턴",
}: {
  /** campaign_tag_id(string) 또는 "NEEDS_REVIEW"/"UNCLASSIFIED"를 키로 하는 카운트. */
  mix: Record<string, number>;
  campaignTags: CampaignTag[];
  title?: string;
}) {
  const nameOf = (key: string) => {
    if (key === "NEEDS_REVIEW") return "검토 필요";
    if (key === "UNCLASSIFIED") return "미분류";
    return campaignTags.find((t) => t.id === key)?.name ?? "알 수 없음";
  };
  const colorOf = (key: string, index: number) => {
    if (key === "NEEDS_REVIEW") return NEEDS_REVIEW_COLOR;
    if (key === "UNCLASSIFIED") return UNCLASSIFIED_COLOR;
    return PALETTE[index % PALETTE.length];
  };

  const entries = Object.entries(mix).filter(([, count]) => count > 0);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  const sorted = [...entries].sort((a, b) => b[1] - a[1]);

  if (total === 0) {
    return (
      <div className="rounded-2xl border border-border bg-white p-5">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
        <p className="mt-1 text-[11px] text-muted">{SUBTITLE}</p>
        <p className="mt-3 text-xs text-muted">선택 기간에 수집된 라이브 소재가 없습니다.</p>
      </div>
    );
  }

  const [[topKey, topCount], ...rest] = sorted;
  const pct = (count: number) => Math.round((count / total) * 100);

  return (
    <div className="rounded-2xl border border-border bg-white p-5">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      <p className="mt-1 text-[11px] text-muted">{SUBTITLE}</p>

      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-sm font-bold text-foreground">{nameOf(topKey)}</span>
        <span className="text-3xl font-extrabold tabular-nums" style={{ color: colorOf(topKey, 0) }}>
          {pct(topCount)}%
        </span>
      </div>

      {rest.length > 0 && (
        <div className="mt-3 space-y-1.5 border-t border-border pt-3">
          {rest.map(([key, count], i) => (
            <div key={key} className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-muted">
                <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: colorOf(key, i + 1) }} />
                {nameOf(key)}
              </span>
              <span className="tabular-nums text-foreground">{pct(count)}%</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

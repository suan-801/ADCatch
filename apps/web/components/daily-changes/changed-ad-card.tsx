import type { ChangedAd } from "@/lib/types";
import { FORMAT_LABEL, VISUAL_LABEL, runningDays } from "@/lib/types";

const EVENT_BADGE: Record<ChangedAd["event_type"], { label: string; className: string }> = {
  STARTED: { label: "NEW", className: "bg-blue-50 text-status-new border border-status-new/30" },
  REACTIVATED: { label: "REACTIVATED", className: "bg-green-50 text-status-active border border-status-active/30" },
  STOPPED: { label: "종료", className: "bg-slate-100 text-status-inactive border border-status-inactive/30" },
  // 백엔드가 baseline 이벤트는 켠/끈 목록에서 걸러주므로 실제로는 렌더링되지 않지만,
  // 타입 완전성을 위해 배지 스타일을 정의해둔다.
  BASELINE_DISCOVERED: { label: "기존 집행", className: "bg-slate-100 text-muted border border-border" },
};

function formatDate(iso: string): string {
  return iso.slice(0, 10).replaceAll("-", ".");
}

// 브리핑 §32/§33: 기존 Ad Card(ad-gallery.tsx)와 동일한 이미지 우선 카드 구조를 공유하되,
// 상태 배지 대신 "이 날짜에 무슨 일이 있었는지"를 나타내는 이벤트 배지를 보여준다.
//
// §4(2026-09 사용자 피드백) — 클릭 시 더 이상 메인 갤러리로 페이지 이동(Link)하지 않는다. 대신
// 같은 위치에서 compact ↔ expanded를 토글한다: router.push/Link/window.location/URL query 변경을
// 전혀 쓰지 않으므로 페이지 새로고침·스크롤 이동이 없다.
export function ChangedAdCard({
  ad,
  expanded,
  onToggle,
}: {
  ad: ChangedAd;
  expanded: boolean;
  onToggle: () => void;
}) {
  const badge = EVENT_BADGE[ad.event_type];
  // P1-01: 이 이벤트 카드는 "그 날 그 순간"의 숫자를 보여줘야 한다 — ad의 현재 값으로 라이브
  // 계산하면 이후 REACTIVATED 등으로 last_seen_at이 앞으로 밀릴 때 과거 카드의 숫자까지 바뀐다.
  // survival_days_at_event가 있으면(신규 이벤트) 그 값을 그대로 쓰고, 없으면(구 이벤트) 폴백한다.
  const running =
    ad.survival_days_at_event != null
      ? { days: ad.survival_days_at_event, label: ad.source_started_at ? ("집행" as const) : ("추적" as const) }
      : runningDays(ad);
  const metaLibraryUrl = `https://www.facebook.com/ads/library/?id=${ad.ad_archive_id}`;

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onToggle();
    }
  };

  if (!expanded) {
    return (
      <div
        role="button"
        tabIndex={0}
        aria-expanded={false}
        onClick={onToggle}
        onKeyDown={handleKeyDown}
        className="flex cursor-pointer items-center gap-3 rounded-2xl border border-border bg-white p-3 text-left transition-shadow hover:shadow-md"
      >
        <div className="flex h-16 w-16 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-slate-50">
          {ad.image_url ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={ad.image_url} alt={ad.copy_text ?? "ad creative"} className="h-full w-full object-cover" />
          ) : (
            <span className="text-[9px] text-muted">{ad.format ?? "-"}</span>
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold ${badge.className}`}>
              {badge.label}
            </span>
            <span className="truncate text-xs font-medium text-muted">{ad.competitor_name}</span>
          </div>
          {ad.copy_text && <p className="line-clamp-2 text-xs text-foreground">{ad.copy_text}</p>}
          {ad.event_date && <p className="text-[10px] text-muted">{formatDate(ad.event_date)}</p>}
        </div>
      </div>
    );
  }

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={true}
      onKeyDown={handleKeyDown}
      className="overflow-hidden rounded-2xl border border-brand/40 bg-white shadow-md"
    >
      <div
        className="relative flex aspect-[4/5] cursor-pointer items-center justify-center bg-slate-50"
        onClick={onToggle}
      >
        {ad.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={ad.image_url} alt={ad.copy_text ?? "ad creative"} className="h-full w-full object-contain" />
        ) : (
          <span className="text-xs text-muted">{ad.format ?? "미디어 없음"}</span>
        )}
        <div className="absolute right-2 top-2 rounded-xl bg-foreground/80 px-2.5 py-1.5 text-right text-white backdrop-blur-sm">
          <p className="text-lg font-extrabold leading-none tabular-nums">{running.days}</p>
          <p className="text-[9px] font-semibold uppercase tracking-wide text-white/70">{running.label}</p>
        </div>
      </div>

      <div className="space-y-3 p-4">
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${badge.className}`}>
              {badge.label}
            </span>
            <span className="text-xs font-medium text-muted">{ad.competitor_name}</span>
          </div>
          <button
            type="button"
            onClick={onToggle}
            aria-label="접기"
            className="rounded-full p-1 text-muted hover:bg-slate-100 hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
          {ad.event_date && (
            <div>
              <dt className="text-muted">이벤트 날짜</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{formatDate(ad.event_date)}</dd>
            </div>
          )}
          <div>
            <dt className="text-muted">포맷</dt>
            <dd className="mt-0.5 font-semibold text-foreground">{ad.format ? FORMAT_LABEL[ad.format] : "-"}</dd>
          </div>
          <div>
            <dt className="text-muted">비주얼</dt>
            <dd className="mt-0.5 font-semibold text-foreground">{ad.visual_type ? VISUAL_LABEL[ad.visual_type] : "-"}</dd>
          </div>
          <div>
            <dt className="text-muted">{running.label} 일수</dt>
            <dd className="mt-0.5 font-semibold text-foreground">{running.days}일째</dd>
          </div>
        </dl>

        {ad.copy_text && (
          <div>
            <p className="text-xs font-semibold text-muted">광고 카피</p>
            <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">{ad.copy_text}</p>
          </div>
        )}
        {ad.cta_text && (
          <div>
            <p className="text-xs font-semibold text-muted">CTA</p>
            <p className="mt-1 text-sm text-foreground">{ad.cta_text}</p>
          </div>
        )}

        <a
          href={metaLibraryUrl}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="block w-full rounded-full border border-border px-4 py-2 text-center text-xs font-semibold text-foreground hover:border-brand hover:text-brand-dark"
        >
          Meta에서 보기
        </a>
      </div>
    </div>
  );
}

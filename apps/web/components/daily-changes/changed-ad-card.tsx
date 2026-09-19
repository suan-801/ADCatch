import { useParams } from "next/navigation";
import Link from "next/link";
import type { ChangedAd } from "@/lib/types";
import { runningDays } from "@/lib/types";

const EVENT_BADGE: Record<ChangedAd["event_type"], { label: string; className: string }> = {
  STARTED: { label: "NEW", className: "bg-blue-50 text-status-new border border-status-new/30" },
  REACTIVATED: { label: "REACTIVATED", className: "bg-green-50 text-status-active border border-status-active/30" },
  STOPPED: { label: "종료", className: "bg-slate-100 text-status-inactive border border-status-inactive/30" },
  // 백엔드가 baseline 이벤트는 켠/끈 목록에서 걸러주므로 실제로는 렌더링되지 않지만,
  // 타입 완전성을 위해 배지 스타일을 정의해둔다.
  BASELINE_DISCOVERED: { label: "기존 집행", className: "bg-slate-100 text-muted border border-border" },
};

// 브리핑 §32/§33: 기존 Ad Card(ad-gallery.tsx)와 동일한 이미지 우선 카드 구조를 공유하되,
// 상태 배지 대신 "이 날짜에 무슨 일이 있었는지"를 나타내는 이벤트 배지를 보여준다.
// §36: 클릭하면 별도 Detail 화면을 새로 만들지 않고, 기존 "현재 현황" 갤러리로 이동해
// 해당 경쟁사 소재를 이어서 볼 수 있게 한다.
export function ChangedAdCard({ ad }: { ad: ChangedAd }) {
  const { projectId } = useParams<{ projectId: string }>();
  const badge = EVENT_BADGE[ad.event_type];
  // P1-01: 이 이벤트 카드는 "그 날 그 순간"의 숫자를 보여줘야 한다 — ad의 현재 값으로 라이브
  // 계산하면 이후 REACTIVATED 등으로 last_seen_at이 앞으로 밀릴 때 과거 카드의 숫자까지 바뀐다.
  // survival_days_at_event가 있으면(신규 이벤트) 그 값을 그대로 쓰고, 없으면(구 이벤트) 폴백한다.
  const running =
    ad.survival_days_at_event != null
      ? { days: ad.survival_days_at_event, label: ad.source_started_at ? ("집행" as const) : ("추적" as const) }
      : runningDays(ad);

  return (
    <Link
      href={`/dashboard/${projectId}?competitor=${ad.competitor_id}`}
      className="group block overflow-hidden rounded-2xl border border-border bg-white transition-shadow hover:shadow-md"
    >
      <div className="relative flex aspect-[4/5] items-center justify-center bg-slate-50">
        {ad.image_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={ad.image_url}
            alt={ad.copy_text ?? "ad creative"}
            className="h-full w-full object-contain transition-transform group-hover:scale-[1.02]"
          />
        ) : (
          <span className="text-xs text-muted">{ad.format ?? "미디어 없음"}</span>
        )}
        <div className="absolute right-2 top-2 rounded-xl bg-foreground/80 px-2.5 py-1.5 text-right text-white backdrop-blur-sm">
          <p className="text-lg font-extrabold leading-none tabular-nums">{running.days}</p>
          <p className="text-[9px] font-semibold uppercase tracking-wide text-white/70">{running.label}</p>
        </div>
      </div>
      <div className="space-y-2 p-4">
        <div className="flex items-center justify-between gap-2">
          <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${badge.className}`}>
            {badge.label}
          </span>
          <span className="truncate text-xs font-medium text-muted">{ad.competitor_name}</span>
        </div>
        {ad.copy_text && <p className="line-clamp-2 text-sm text-foreground">{ad.copy_text}</p>}
      </div>
    </Link>
  );
}

import { useParams } from "next/navigation";
import Link from "next/link";
import type { ChangedAd } from "@/lib/types";
import { survivalDays } from "@/lib/types";

const EVENT_BADGE: Record<ChangedAd["event_type"], { label: string; className: string }> = {
  STARTED: { label: "NEW", className: "bg-blue-50 text-status-new border border-status-new/30" },
  REACTIVATED: { label: "REACTIVATED", className: "bg-green-50 text-status-active border border-status-active/30" },
  STOPPED: { label: "종료", className: "bg-slate-100 text-status-inactive border border-status-inactive/30" },
};

// 브리핑 §32/§33: 기존 Ad Card(ad-gallery.tsx)와 동일한 이미지 우선 카드 구조를 공유하되,
// 상태 배지 대신 "이 날짜에 무슨 일이 있었는지"를 나타내는 이벤트 배지를 보여준다.
// §36: 클릭하면 별도 Detail 화면을 새로 만들지 않고, 기존 "현재 현황" 갤러리로 이동해
// 해당 경쟁사 소재를 이어서 볼 수 있게 한다.
export function ChangedAdCard({ ad }: { ad: ChangedAd }) {
  const { projectId } = useParams<{ projectId: string }>();
  const badge = EVENT_BADGE[ad.event_type];

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
            className="h-full w-full object-cover transition-transform group-hover:scale-[1.02]"
          />
        ) : (
          <span className="text-xs text-muted">{ad.format ?? "미디어 없음"}</span>
        )}
        <div className="absolute right-2 top-2 rounded-xl bg-foreground/80 px-2.5 py-1.5 text-right text-white backdrop-blur-sm">
          <p className="text-lg font-extrabold leading-none tabular-nums">{survivalDays(ad)}</p>
          <p className="text-[9px] font-semibold uppercase tracking-wide text-white/70">days</p>
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

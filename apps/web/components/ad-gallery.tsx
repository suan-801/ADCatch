import type { Ad } from "@/lib/types";
import { survivalDays } from "@/lib/types";
import { StatusBadge } from "./status-badge";

export function AdGallery({ ads }: { ads: Ad[] }) {
  const sorted = [...ads].sort((a, b) => survivalDays(b) - survivalDays(a));

  if (sorted.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted">
        아직 수집된 소재가 없습니다. 경쟁사를 등록하고 수집을 실행해보세요.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {sorted.map((ad) => (
        <div
          key={ad.id}
          className="group overflow-hidden rounded-2xl border border-border bg-white transition-shadow hover:shadow-md"
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
            {/* 브리핑 §25: 생존일수는 작은 메타데이터가 아니라 강한 시각적 배지로 표현 */}
            <div className="absolute right-2 top-2 rounded-xl bg-foreground/80 px-2.5 py-1.5 text-right text-white backdrop-blur-sm">
              <p className="text-lg font-extrabold leading-none tabular-nums">{survivalDays(ad)}</p>
              <p className="text-[9px] font-semibold uppercase tracking-wide text-white/70">days</p>
            </div>
          </div>
          <div className="space-y-2 p-4">
            <StatusBadge status={ad.status} />
            {ad.copy_text && <p className="line-clamp-2 text-sm text-foreground">{ad.copy_text}</p>}
            {ad.cta_text && <p className="text-xs text-muted">CTA: {ad.cta_text}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

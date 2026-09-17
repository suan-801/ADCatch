import type { Ad } from "@/lib/types";
import { survivalDays } from "@/lib/types";
import { StatusBadge } from "./status-badge";

export function AdGallery({ ads }: { ads: Ad[] }) {
  const sorted = [...ads].sort((a, b) => survivalDays(b) - survivalDays(a));

  if (sorted.length === 0) {
    return (
      <div className="rounded border border-dashed border-border p-8 text-center text-sm text-muted">
        아직 수집된 소재가 없습니다. 경쟁사를 등록하고 수집을 실행해보세요.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {sorted.map((ad) => (
        <div key={ad.id} className="overflow-hidden rounded border border-border bg-white">
          <div className="flex aspect-square items-center justify-center bg-slate-100">
            {ad.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={ad.image_url} alt={ad.copy_text ?? "ad creative"} className="h-full w-full object-cover" />
            ) : (
              <span className="text-xs text-muted">{ad.format ?? "미디어 없음"}</span>
            )}
          </div>
          <div className="space-y-1.5 p-3">
            <div className="flex items-center justify-between">
              <StatusBadge status={ad.status} />
              <span className="text-xs tabular-nums text-muted">{survivalDays(ad)}일째</span>
            </div>
            {ad.copy_text && <p className="line-clamp-2 text-xs text-foreground">{ad.copy_text}</p>}
            {ad.cta_text && <p className="text-xs text-muted">CTA: {ad.cta_text}</p>}
          </div>
        </div>
      ))}
    </div>
  );
}

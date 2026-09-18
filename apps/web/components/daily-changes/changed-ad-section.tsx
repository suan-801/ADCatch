import type { ChangedAd } from "@/lib/types";
import { ChangedAdCard } from "./changed-ad-card";

export function ChangedAdSection({ title, ads }: { title: string; ads: ChangedAd[] }) {
  if (ads.length === 0) return null;

  return (
    <section>
      <h2 className="mb-4 text-lg font-bold text-foreground">
        {title} <span className="ml-1 text-sm font-medium text-muted">{ads.length}</span>
      </h2>
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
        {ads.map((ad) => (
          <ChangedAdCard key={ad.id} ad={ad} />
        ))}
      </div>
    </section>
  );
}

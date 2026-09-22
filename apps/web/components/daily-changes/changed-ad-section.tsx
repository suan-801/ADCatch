"use client";

import { useState } from "react";
import type { ChangedAd } from "@/lib/types";
import { ChangedAdCard } from "./changed-ad-card";

// 같은 광고가 기간 안에서 여러 이벤트를 가질 수 있으므로(예: 월 STARTED, 금 REACTIVATED) ad.id만으로는
// 카드를 유일하게 식별할 수 없다 — event_type/event_date까지 합쳐 키로 쓴다.
function changedAdKey(ad: ChangedAd): string {
  return `${ad.id}:${ad.event_type}:${ad.event_date ?? ad.first_seen_at}`;
}

// §4 — 카드 클릭 시 페이지 이동(router.push/Link) 대신 같은 위치에서 inline expand한다. 한 번에
// 하나만 펼치는 방식을 쓴다(여러 개가 동시에 펼쳐지면 화면이 어수선해진다) — 다른 카드를 클릭하면
// 기존 확장 카드는 접히고 새 카드가 펼쳐진다.
export function ChangedAdSection({ title, ads }: { title: string; ads: ChangedAd[] }) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);

  if (ads.length === 0) return null;

  return (
    <section>
      <h2 className="mb-4 text-lg font-bold text-foreground">
        {title} <span className="ml-1 text-sm font-medium text-muted">{ads.length}</span>
      </h2>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {ads.map((ad) => {
          const key = changedAdKey(ad);
          return (
            <ChangedAdCard
              key={key}
              ad={ad}
              expanded={expandedKey === key}
              onToggle={() => setExpandedKey((prev) => (prev === key ? null : key))}
            />
          );
        })}
      </div>
    </section>
  );
}

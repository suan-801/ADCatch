"use client";

import { useState } from "react";
import type { Competitor } from "@/lib/types";

export function CompetitorPanel({
  competitors,
  selectedId,
  onSelect,
  onCreate,
  onCollect,
  collecting,
}: {
  competitors: Competitor[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: (payload: { name: string; ad_library_url: string; is_own_brand: boolean }) => Promise<void>;
  onCollect: (id: string) => Promise<void>;
  collecting: boolean;
}) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [isOwnBrand, setIsOwnBrand] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim() || !url.trim()) return;
    setSubmitting(true);
    try {
      await onCreate({ name: name.trim(), ad_library_url: url.trim(), is_own_brand: isOwnBrand });
      setName("");
      setUrl("");
      setIsOwnBrand(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="rounded border border-border bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">경쟁사 / 자사 브랜드</p>

      <div className="mt-3 flex flex-wrap gap-2">
        {competitors.map((c) => (
          <button
            key={c.id}
            onClick={() => onSelect(c.id)}
            className={`rounded-full border px-3 py-1 text-xs ${
              c.id === selectedId ? "border-foreground bg-foreground text-white" : "border-border text-muted"
            }`}
          >
            {c.name} {c.is_own_brand && "(자사)"}
          </button>
        ))}
      </div>

      {selectedId && (
        <button
          onClick={() => onCollect(selectedId)}
          disabled={collecting}
          className="mt-3 rounded bg-status-active px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
        >
          {collecting ? "수집 중..." : "지금 수집 실행"}
        </button>
      )}

      <div className="mt-4 space-y-2 border-t border-border pt-3">
        <p className="text-xs text-muted">Meta Ad Library URL로 새로 등록</p>
        <input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="브랜드명"
          className="w-full rounded border border-border px-2 py-1 text-xs"
        />
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.facebook.com/ads/library/?...&view_all_page_id=..."
          className="w-full rounded border border-border px-2 py-1 text-xs"
        />
        <label className="flex items-center gap-1.5 text-xs text-muted">
          <input type="checkbox" checked={isOwnBrand} onChange={(e) => setIsOwnBrand(e.target.checked)} />
          이 브랜드는 자사입니다 (대시보드 집계에서 제외)
        </label>
        <button
          onClick={handleSubmit}
          disabled={submitting}
          className="rounded bg-foreground px-3 py-1.5 text-xs text-white disabled:opacity-50"
        >
          등록
        </button>
      </div>
    </div>
  );
}

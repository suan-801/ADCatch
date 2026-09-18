"use client";

import { useState } from "react";
import type { Competitor } from "@/lib/types";
import { Modal } from "@/components/ui/modal";

// 브리핑 §27: 상시 노출 등록 폼을 "+ 경쟁사 추가" → Modal로 축소. validation/API/등록 로직은
// 기존 그대로 재사용하고, 노출 위치만 Modal 안으로 옮긴다.
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
  const [modalOpen, setModalOpen] = useState(false);
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
      setModalOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-muted">Competitors</span>

      {competitors.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
            c.id === selectedId
              ? "border-brand bg-brand text-white"
              : "border-border text-muted hover:border-brand/40 hover:text-foreground"
          }`}
        >
          {c.name} {c.is_own_brand && "(자사)"}
        </button>
      ))}

      <button
        onClick={() => setModalOpen(true)}
        className="rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-semibold text-muted hover:border-brand hover:text-brand-dark"
      >
        + 경쟁사 추가
      </button>

      {selectedId && (
        <button
          onClick={() => onCollect(selectedId)}
          disabled={collecting}
          className="ml-auto rounded-full bg-status-active px-4 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {collecting ? "수집 중..." : "지금 수집 실행"}
        </button>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="경쟁사 등록">
        <div className="space-y-2">
          <p className="text-xs text-muted">Meta Ad Library URL로 새로 등록</p>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="브랜드명"
            autoFocus
            className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-brand focus:outline-none"
          />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://www.facebook.com/ads/library/?...&view_all_page_id=..."
            className="w-full rounded-lg border border-border px-3 py-2 text-xs focus:border-brand focus:outline-none"
          />
          <label className="flex items-center gap-1.5 text-xs text-muted">
            <input type="checkbox" checked={isOwnBrand} onChange={(e) => setIsOwnBrand(e.target.checked)} />
            이 브랜드는 자사입니다 (대시보드 집계에서 제외)
          </label>
          <button
            onClick={handleSubmit}
            disabled={submitting || !name.trim() || !url.trim()}
            className="w-full rounded-full bg-foreground px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "등록 중..." : "등록"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

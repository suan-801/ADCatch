"use client";

import { useState } from "react";
import type { Competitor } from "@/lib/types";
import { Modal } from "@/components/ui/modal";
import { isValidMetaAdLibraryUrl, META_AD_LIBRARY_URL_ERROR } from "@/lib/validation";
import { useAuth } from "@/lib/auth-context";

// 브리핑 §27: 상시 노출 등록 폼을 "+ 브랜드 추가" → Modal로 축소. validation/API/등록 로직은
// 기존 그대로 재사용하고, 노출 위치만 Modal 안으로 옮긴다.
// P0-18~22 Brand Model Simplification: 자사/경쟁사 구분(체크박스)을 제거하고, Project 안의
// 모든 등록 대상을 동일한 "브랜드"로 취급한다.
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
  onSelect: (id: string | null) => void;
  onCreate: (payload: { name: string; ad_library_url: string }) => Promise<void>;
  onCollect: (id: string) => Promise<void>;
  collecting: boolean;
}) {
  const { isAdmin } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [urlError, setUrlError] = useState(false);

  const handleSubmit = async () => {
    if (!name.trim() || !url.trim()) return;
    if (!isValidMetaAdLibraryUrl(url.trim())) {
      setUrlError(true);
      return;
    }
    setUrlError(false);
    setSubmitting(true);
    try {
      await onCreate({ name: name.trim(), ad_library_url: url.trim() });
      setName("");
      setUrl("");
      setModalOpen(false);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="mr-1 text-xs font-semibold uppercase tracking-wide text-muted">추적 브랜드</span>

      {competitors.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id === selectedId ? null : c.id)}
          className={`rounded-full border px-3.5 py-1.5 text-xs font-medium transition-colors ${
            c.id === selectedId
              ? "border-brand bg-brand text-white"
              : "border-border text-muted hover:border-brand/40 hover:text-foreground"
          }`}
        >
          {c.name}
        </button>
      ))}

      {isAdmin && (
        <button
          onClick={() => setModalOpen(true)}
          className="rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-semibold text-muted hover:border-brand hover:text-brand-dark"
        >
          + 브랜드 추가
        </button>
      )}

      {isAdmin && selectedId && (
        <button
          onClick={() => onCollect(selectedId)}
          disabled={collecting}
          className="ml-auto rounded-full bg-status-active px-4 py-1.5 text-xs font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {collecting ? "수집 중..." : "지금 수집 실행"}
        </button>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="브랜드 등록">
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
            onChange={(e) => {
              setUrl(e.target.value);
              if (urlError) setUrlError(false);
            }}
            placeholder="https://www.facebook.com/ads/library/?...&view_all_page_id=..."
            className={`w-full rounded-lg border px-3 py-2 text-xs focus:outline-none ${
              urlError ? "border-status-inactive focus:border-status-inactive" : "border-border focus:border-brand"
            }`}
          />
          {urlError ? (
            <p className="text-[11px] font-medium text-status-inactive">{META_AD_LIBRARY_URL_ERROR}</p>
          ) : (
            <p className="text-[11px] text-muted">
              Meta Ad Library에서 브랜드 페이지를 연 뒤 브라우저 주소를 붙여넣어주세요.
            </p>
          )}
          <button
            onClick={handleSubmit}
            disabled={submitting || !name.trim() || !url.trim()}
            className="w-full rounded-full bg-foreground px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
          >
            {submitting ? "추가 중..." : "브랜드 추가"}
          </button>
        </div>
      </Modal>
    </div>
  );
}

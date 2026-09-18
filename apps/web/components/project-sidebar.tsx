"use client";

import { useState } from "react";
import Link from "next/link";
import type { Project } from "@/lib/types";
import { Modal } from "@/components/ui/modal";

// PRD 3.1 사이드바 프로젝트 전환 + 브리핑 §28: 상시 노출 입력폼 대신 "+ NEW PROJECT" → Modal로 축소.
// mobileOpen/onMobileClose는 §41 반응형(Sidebar → Drawer) 대응.
export function ProjectSidebar({
  projects,
  selectedId,
  onSelect,
  onCreate,
  mobileOpen = false,
  onMobileClose,
}: {
  projects: Project[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}) {
  const [modalOpen, setModalOpen] = useState(false);
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await onCreate(newName.trim());
      setNewName("");
      setModalOpen(false);
    } finally {
      setCreating(false);
    }
  };

  const body = (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/logo.png" alt="ADCatcher" className="h-6 w-auto" />
      <Link href="/" className="mt-4 flex items-center gap-2 text-xs font-medium text-muted hover:text-brand-dark">
        <span aria-hidden>←</span> 홈으로
      </Link>

      <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Projects</p>
      <nav className="mt-2 flex flex-col gap-1">
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => {
              onSelect(p.id);
              onMobileClose?.();
            }}
            className={`flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
              p.id === selectedId
                ? "bg-brand-cream font-semibold text-brand-dark"
                : "text-muted hover:bg-slate-50 hover:text-foreground"
            }`}
          >
            <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${p.id === selectedId ? "bg-brand" : "bg-transparent"}`} />
            {p.name}
            {p.status === "PAUSED" && <span className="ml-auto text-[10px] text-status-inactive">일시정지</span>}
          </button>
        ))}
        {projects.length === 0 && <p className="px-3 text-xs text-muted">아직 프로젝트가 없습니다.</p>}
      </nav>

      <button
        onClick={() => setModalOpen(true)}
        className="mt-4 rounded-lg border border-dashed border-border px-3 py-2 text-left text-xs font-semibold text-muted hover:border-brand hover:text-brand-dark"
      >
        + NEW PROJECT
      </button>
    </>
  );

  return (
    <>
      <aside className="hidden w-64 shrink-0 flex-col gap-1 border-r border-border bg-white p-5 lg:flex">{body}</aside>

      {mobileOpen && (
        <div className="fixed inset-0 z-40 flex lg:hidden">
          <div className="absolute inset-0 bg-foreground/40" onClick={onMobileClose} />
          <aside className="relative flex w-72 max-w-[85vw] flex-col gap-1 bg-white p-5 shadow-xl motion-safe:animate-fade-in-up">
            {body}
          </aside>
        </div>
      )}

      <Modal open={modalOpen} onClose={() => setModalOpen(false)} title="새 프로젝트">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="프로젝트명 (예: NIKE)"
          autoFocus
          className="w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-brand focus:outline-none"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button
          onClick={handleCreate}
          disabled={creating || !newName.trim()}
          className="mt-3 w-full rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {creating ? "만드는 중..." : "만들기"}
        </button>
      </Modal>
    </>
  );
}

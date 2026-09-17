"use client";

import { useState } from "react";
import type { Project } from "@/lib/types";

// PRD.MD 3.1 — 사이드바 드롭다운으로 프로젝트(워크스페이스)를 전환.
export function ProjectSidebar({
  projects,
  selectedId,
  onSelect,
  onCreate,
}: {
  projects: Project[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  onCreate: (name: string) => Promise<void>;
}) {
  const [newName, setNewName] = useState("");
  const [creating, setCreating] = useState(false);

  const handleCreate = async () => {
    if (!newName.trim()) return;
    setCreating(true);
    try {
      await onCreate(newName.trim());
      setNewName("");
    } finally {
      setCreating(false);
    }
  };

  return (
    <aside className="flex w-60 shrink-0 flex-col gap-3 border-r border-border bg-white p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted">프로젝트</p>
      <nav className="flex flex-col gap-1">
        {projects.map((p) => (
          <button
            key={p.id}
            onClick={() => onSelect(p.id)}
            className={`rounded px-2 py-1.5 text-left text-sm ${
              p.id === selectedId ? "bg-slate-100 font-medium text-foreground" : "text-muted hover:bg-slate-50"
            }`}
          >
            {p.name}
            {p.status === "PAUSED" && <span className="ml-2 text-[10px] text-status-inactive">(일시정지)</span>}
          </button>
        ))}
        {projects.length === 0 && <p className="px-2 text-xs text-muted">아직 프로젝트가 없습니다.</p>}
      </nav>

      <div className="mt-2 flex gap-1 border-t border-border pt-3">
        <input
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          placeholder="새 프로젝트명"
          className="min-w-0 flex-1 rounded border border-border px-2 py-1 text-xs"
          onKeyDown={(e) => e.key === "Enter" && handleCreate()}
        />
        <button
          onClick={handleCreate}
          disabled={creating}
          className="rounded bg-foreground px-2 py-1 text-xs text-white disabled:opacity-50"
        >
          추가
        </button>
      </div>
    </aside>
  );
}

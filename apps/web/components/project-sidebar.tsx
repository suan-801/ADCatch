"use client";

import { useState } from "react";
import Link from "next/link";
import type { Project } from "@/lib/types";
import { ProjectCreateWizard } from "@/components/project-create-wizard";
import { useAuth } from "@/lib/auth-context";

// PRD 3.1 사이드바 프로젝트 전환. mobileOpen/onMobileClose는 §41 반응형(Sidebar → Drawer) 대응.
// Part E-02: "+ NEW PROJECT"는 Landing과 동일한 ProjectCreateWizard(Project→Brand→첫 수집)를 연다 —
// 이름만 받는 간단한 폼을 더 이상 별도로 갖지 않는다.
export function ProjectSidebar({
  projects,
  selectedId,
  onSelect,
  onProjectCreated,
  onRequestDelete,
  mobileOpen = false,
  onMobileClose,
}: {
  projects: Project[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  /** 프로젝트 row가 생성된 직후 호출 — 사이드바 프로젝트 목록을 새로고침하기 위함. */
  onProjectCreated: () => void;
  /** 사이드바 각 프로젝트 row의 "⋯" → 삭제 — 실제 확인 다이얼로그는 부모(레이아웃)가 갖고 있다. */
  onRequestDelete: (project: Project) => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}) {
  const { isAdmin } = useAuth();
  const [wizardOpen, setWizardOpen] = useState(false);
  const [menuOpenFor, setMenuOpenFor] = useState<string | null>(null);

  const body = (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/brand/logo.png" alt="ADCatcher" className="h-auto w-[150px] max-w-full object-contain" />
      <Link href="/" className="mt-4 flex items-center gap-2 text-xs font-medium text-muted hover:text-brand-dark">
        <span aria-hidden>←</span> 홈으로
      </Link>

      <p className="mt-5 text-xs font-semibold uppercase tracking-wide text-muted">Projects</p>
      <nav className="mt-2 flex flex-col gap-1">
        {projects.map((p) => (
          <div
            key={p.id}
            className={`group relative flex items-center rounded-lg pr-1 transition-colors ${
              p.id === selectedId ? "bg-brand-cream" : "hover:bg-slate-50"
            }`}
          >
            <button
              onClick={() => {
                onSelect(p.id);
                onMobileClose?.();
              }}
              className={`flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left text-sm ${
                p.id === selectedId ? "font-semibold text-brand-dark" : "text-muted hover:text-foreground"
              }`}
            >
              <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${p.id === selectedId ? "bg-brand" : "bg-transparent"}`} />
              <span className="truncate">{p.name}</span>
              {p.status === "PAUSED" && <span className="ml-auto shrink-0 text-[10px] text-status-inactive">일시정지</span>}
            </button>

            {isAdmin && (
              <button
                type="button"
                onClick={() => setMenuOpenFor((v) => (v === p.id ? null : p.id))}
                aria-label={`${p.name} 옵션`}
                className="shrink-0 rounded-full px-1.5 py-1 text-muted opacity-0 hover:bg-slate-100 hover:text-foreground group-hover:opacity-100"
              >
                ⋯
              </button>
            )}

            {isAdmin && menuOpenFor === p.id && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setMenuOpenFor(null)} />
                <div className="absolute right-0 top-full z-20 mt-1 w-36 rounded-xl border border-border bg-white p-1 shadow-lg">
                  <button
                    type="button"
                    onClick={() => {
                      setMenuOpenFor(null);
                      onRequestDelete(p);
                    }}
                    className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-red-600 hover:bg-red-50"
                  >
                    프로젝트 삭제
                  </button>
                </div>
              </>
            )}
          </div>
        ))}
        {projects.length === 0 && <p className="px-3 text-xs text-muted">아직 프로젝트가 없습니다.</p>}
      </nav>

      {isAdmin && (
        <button
          onClick={() => setWizardOpen(true)}
          className="mt-4 rounded-lg border border-dashed border-border px-3 py-2 text-left text-xs font-semibold text-muted hover:border-brand hover:text-brand-dark"
        >
          + NEW PROJECT
        </button>
      )}
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

      {isAdmin && (
        <ProjectCreateWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={onProjectCreated} />
      )}
    </>
  );
}

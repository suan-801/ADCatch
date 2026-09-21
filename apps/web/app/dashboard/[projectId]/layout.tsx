"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useParams, useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Project } from "@/lib/types";
import { ProjectSidebar } from "@/components/project-sidebar";
import { CollectionFreshnessBadge } from "@/components/collection-freshness";
import { AutoCatchToggle } from "@/components/auto-catch-toggle";
import { ProjectContext } from "@/lib/project-context";
import { Modal } from "@/components/ui/modal";
import { AdminModeControl } from "@/components/admin-mode-control";
import { useAuth } from "@/lib/auth-context";

// 브리핑 §20/§21: Project 내부를 "현재 현황" / "날짜별 변화" 두 관점으로 나누는 공용 셸.
// 사이드바 + 프로젝트 헤더 + 서브내비를 여기서 한 번만 렌더링하고, 두 페이지는 콘텐츠만 채운다.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const pathname = usePathname();
  const { isAdmin } = useAuth();

  const [projects, setProjects] = useState<Project[]>([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  // 헤더의 "⋯"(현재 프로젝트)와 사이드바 각 row의 "⋯"(임의의 프로젝트) 둘 다 이 하나의
  // 다이얼로그를 공유한다 — 삭제 대상이 "현재 보고 있는 프로젝트"로 고정돼 있지 않다.
  const [deleteTarget, setDeleteTarget] = useState<Project | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {});
  }, []);

  const currentProject = projects.find((p) => p.id === projectId);
  const isChanges = pathname?.endsWith("/changes") ?? false;

  // Part E: 실제 생성/이동은 ProjectCreateWizard(Sidebar 내부)가 전담한다 — 여기서는
  // 사이드바 프로젝트 목록만 최신 상태로 새로고침한다.
  const refreshProjects = () => {
    api.listProjects().then(setProjects).catch(() => {});
  };

  const handleToggleAutoCollect = async (enabled: boolean) => {
    const updated = await api.updateProject(projectId, { auto_collect_enabled: enabled });
    setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
  };

  // Part H-06: 삭제된 프로젝트 route에 머무르지 않는다 — 남은 프로젝트가 있으면 그중 하나로,
  // 없으면 Landing Project Select로 이동한다. 단, 사이드바에서 "현재 보고 있지 않은" 다른
  // 프로젝트를 지운 경우엔 지금 보던 화면에 그대로 머무른다(굳이 이동시키지 않는다).
  const handleDeleteProject = async () => {
    if (!deleteTarget) return;
    const targetId = deleteTarget.id;
    setDeleting(true);
    try {
      await api.deleteProject(targetId);
      const remaining = projects.filter((p) => p.id !== targetId);
      setProjects(remaining);
      setDeleteTarget(null);
      if (targetId === projectId) {
        router.push(remaining.length > 0 ? `/dashboard/${remaining[0].id}` : "/");
      }
    } catch (e) {
      alert(`프로젝트 삭제에 실패했어요: ${e}`);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <ProjectContext.Provider value={{ project: currentProject ?? null, updateAutoCollect: handleToggleAutoCollect }}>
    <div className="flex min-h-screen bg-background">
      <ProjectSidebar
        projects={projects}
        selectedId={projectId}
        onSelect={(id) => {
          router.push(isChanges ? `/dashboard/${id}/changes` : `/dashboard/${id}`);
          setMobileNavOpen(false);
        }}
        onProjectCreated={refreshProjects}
        onRequestDelete={setDeleteTarget}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => setMobileNavOpen(false)}
      />

      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-center gap-4 border-b border-border bg-white px-6 py-5 sm:px-8">
          <button
            type="button"
            onClick={() => setMobileNavOpen(true)}
            className="rounded-lg border border-border p-2 text-muted lg:hidden"
            aria-label="메뉴 열기"
          >
            ☰
          </button>

          <div className="min-w-0">
            <h1 className="truncate text-xl font-extrabold text-foreground">{currentProject?.name ?? " "}</h1>
            <p className="text-xs text-muted">브랜드 광고 현황</p>
            {projectId && (
              <div className="mt-1.5">
                <CollectionFreshnessBadge projectId={projectId} />
              </div>
            )}
          </div>

          <div className="ml-auto flex items-center gap-3">
            <AdminModeControl />

            {currentProject && isAdmin && (
              <AutoCatchToggle project={currentProject} onToggle={handleToggleAutoCollect} />
            )}

            {/* Part H-05: Project Header의 secondary menu에 삭제 액션을 둔다. Viewer는 삭제 기능 자체가
                없으므로 메뉴를 아예 숨긴다(빈 메뉴 노출 방지). */}
            {isAdmin && (
              <div className="relative">
                <button
                  type="button"
                  onClick={() => setMenuOpen((v) => !v)}
                  aria-label="프로젝트 옵션"
                  className="rounded-full border border-border p-2 text-muted hover:bg-slate-50 hover:text-foreground"
                >
                  ⋯
                </button>
                {menuOpen && (
                  <>
                    <div className="fixed inset-0 z-10" onClick={() => setMenuOpen(false)} />
                    <div className="absolute right-0 top-full z-20 mt-2 w-40 rounded-xl border border-border bg-white p-1 shadow-lg">
                      <button
                        type="button"
                        onClick={() => {
                          setMenuOpen(false);
                          if (currentProject) setDeleteTarget(currentProject);
                        }}
                        className="w-full rounded-lg px-3 py-2 text-left text-sm font-medium text-red-600 hover:bg-red-50"
                      >
                        프로젝트 삭제
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            <nav className="flex gap-1 rounded-full bg-slate-100 p-1 text-xs font-semibold">
            <Link
              href={`/dashboard/${projectId}`}
              className={`rounded-full px-4 py-1.5 transition-colors ${
                !isChanges ? "bg-white text-brand-dark shadow-sm" : "text-muted hover:text-foreground"
              }`}
            >
              현재 현황
            </Link>
            <Link
              href={`/dashboard/${projectId}/changes`}
              className={`rounded-full px-4 py-1.5 transition-colors ${
                isChanges ? "bg-white text-brand-dark shadow-sm" : "text-muted hover:text-foreground"
              }`}
            >
              날짜별 변화
            </Link>
            </nav>
          </div>
        </header>

        <main className="p-6 sm:p-8">{children}</main>
      </div>

      <Modal open={!!deleteTarget} onClose={() => !deleting && setDeleteTarget(null)}>
        <h3 className="text-base font-bold text-foreground">
          &apos;{deleteTarget?.name ?? ""}&apos; 프로젝트를 삭제할까요?
        </h3>
        <p className="mt-2 text-sm text-muted">
          등록된 브랜드와 수집 기록도 함께 삭제됩니다.
          <br />이 작업은 되돌릴 수 없습니다.
        </p>
        <div className="mt-5 flex items-center gap-2">
          <button
            type="button"
            onClick={() => setDeleteTarget(null)}
            disabled={deleting}
            className="flex-1 rounded-full px-4 py-2.5 text-sm font-medium text-muted hover:text-foreground disabled:opacity-60"
          >
            취소
          </button>
          <button
            type="button"
            onClick={handleDeleteProject}
            disabled={deleting}
            className="flex-1 rounded-full bg-red-600 px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {deleting ? "삭제 중..." : "프로젝트 삭제"}
          </button>
        </div>
      </Modal>
    </div>
    </ProjectContext.Provider>
  );
}

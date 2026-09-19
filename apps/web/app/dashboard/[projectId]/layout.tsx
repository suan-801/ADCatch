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

// 브리핑 §20/§21: Project 내부를 "현재 현황" / "날짜별 변화" 두 관점으로 나누는 공용 셸.
// 사이드바 + 프로젝트 헤더 + 서브내비를 여기서 한 번만 렌더링하고, 두 페이지는 콘텐츠만 채운다.
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { projectId } = useParams<{ projectId: string }>();
  const router = useRouter();
  const pathname = usePathname();

  const [projects, setProjects] = useState<Project[]>([]);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  useEffect(() => {
    api.listProjects().then(setProjects).catch(() => {});
  }, []);

  const currentProject = projects.find((p) => p.id === projectId);
  const isChanges = pathname?.endsWith("/changes") ?? false;

  const handleCreateProject = async (name: string) => {
    const project = await api.createProject(name);
    setProjects((prev) => [...prev, project]);
    router.push(`/dashboard/${project.id}`);
  };

  const handleToggleAutoCollect = async (enabled: boolean) => {
    const updated = await api.updateProject(projectId, { auto_collect_enabled: enabled });
    setProjects((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
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
        onCreate={handleCreateProject}
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
            {currentProject && <AutoCatchToggle project={currentProject} onToggle={handleToggleAutoCollect} />}

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
    </div>
    </ProjectContext.Provider>
  );
}

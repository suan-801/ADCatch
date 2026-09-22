"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";
import type { ProjectSummary } from "@/lib/types";
import { ProjectCreateWizard } from "@/components/project-create-wizard";
import { useAuth } from "@/lib/auth-context";

interface ProjectCardData {
  project: ProjectSummary;
  competitorCount: number;
  activeAdCount: number;
}

// §13-2 성능 최적화: 프로젝트 카드의 경쟁사/활성광고 수치는 이전엔 /projects + N×
// (/projects/{id}/competitors + /projects/{id}/dashboard)를 조합해 만들었다(2N+1회 호출).
// 지금은 GET /projects/summary 1회로 동일한 값을 받는다(하드코딩 금지 — 브리핑 4장, 값의 의미는
// 기존과 동일). 기존 listProjects/listCompetitors/getDashboard는 다른 화면에서 계속 쓰이므로
// 삭제하지 않는다.
export function ProjectSelectSection() {
  const { isAdmin } = useAuth();
  const [cards, setCards] = useState<ProjectCardData[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [wizardOpen, setWizardOpen] = useState(false);

  const loadCards = () => {
    api
      .listProjectsSummary()
      .then((summaries) => {
        setCards(
          summaries.map((project) => ({
            project,
            competitorCount: project.competitor_count,
            activeAdCount: project.active_ad_count,
          })),
        );
      })
      .catch((e) => setError(String(e)));
  };

  useEffect(() => {
    loadCards();
  }, []);

  return (
    <section id="project-select" className="bg-white px-6 py-24 sm:py-32">
      <div className="mx-auto max-w-4xl">
        <div className="flex flex-col items-center text-center">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/mascot/catcher-hero.webp" alt="캐쳐" className="w-24 sm:w-32" />
          <h2 className="mt-4 text-2xl font-extrabold text-foreground sm:text-4xl">
            오늘은 어떤 광고를
            <br className="sm:hidden" /> CATCH할까요?
          </h2>
        </div>

        {error && (
          <div className="mt-8 rounded-xl border border-status-inactive/30 bg-slate-50 p-4 text-center text-xs text-status-inactive">
            API 연동 오류: {error}. 백엔드(apps/api)가 실행 중인지 확인하세요.
          </div>
        )}

        <div className="mt-12 grid grid-cols-1 gap-5 sm:grid-cols-2">
          {cards?.map(({ project, competitorCount, activeAdCount }) => (
            <Link
              key={project.id}
              href={`/dashboard/${project.id}`}
              className="group rounded-2xl border border-border bg-white p-6 transition-all hover:-translate-y-0.5 hover:border-brand hover:shadow-lg"
            >
              <p className="text-lg font-extrabold text-foreground group-hover:text-brand-dark">{project.name}</p>
              <div className="mt-3 flex gap-4 text-xs text-muted">
                <span>브랜드 {competitorCount}</span>
                <span>활성 광고 {activeAdCount}</span>
              </div>
            </Link>
          ))}

          {cards && cards.length === 0 && (
            <p className="col-span-full text-center text-sm text-muted">
              아직 프로젝트가 없습니다. 아래에서 새로 만들어보세요.
            </p>
          )}

          {!cards && !error && <p className="col-span-full text-center text-sm text-muted">불러오는 중...</p>}
        </div>

        {isAdmin && (
          <div className="mx-auto mt-10 flex max-w-sm justify-center">
            <button
              onClick={() => setWizardOpen(true)}
              className="rounded-full bg-brand px-6 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90"
            >
              새 프로젝트
            </button>
          </div>
        )}
      </div>

      {isAdmin && (
        <ProjectCreateWizard open={wizardOpen} onClose={() => setWizardOpen(false)} onCreated={loadCards} />
      )}
    </section>
  );
}

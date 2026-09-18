"use client";

import { createContext, useContext } from "react";
import type { Project } from "./types";

// layout.tsx가 프로젝트 목록/현재 프로젝트를 소유하고, 페이지(page.tsx)와 헤더의 자동 추적
// 토글이 같은 값을 공유하도록 한다. 이게 없으면 Baseline CTA에서 opt-in해도 헤더 토글이
// 별도 fetch 상태를 갖고 있어 즉시 반영되지 않는 불일치가 생긴다.
interface ProjectContextValue {
  project: Project | null;
  updateAutoCollect: (enabled: boolean) => Promise<void>;
}

export const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProjectContext(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProjectContext must be used within a dashboard layout");
  return ctx;
}

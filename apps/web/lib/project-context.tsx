"use client";

import { createContext, useContext } from "react";
import type { CampaignTag, Competitor, Project } from "./types";

// layout.tsx가 프로젝트 목록/현재 프로젝트를 소유하고, 페이지(page.tsx)와 헤더의 자동 추적
// 토글이 같은 값을 공유하도록 한다. 이게 없으면 Baseline CTA에서 opt-in해도 헤더 토글이
// 별도 fetch 상태를 갖고 있어 즉시 반영되지 않는 불일치가 생긴다.
//
// §13-5 성능 최적화: competitors/campaignTags도 여기서 프로젝트당 1회만 fetch해 공유한다 —
// 대시보드/날짜별 변화/캠페인 태그 관리 탭을 오갈 때마다 각자 다시 fetch하지 않기 위함(additive —
// 기존 소비자는 project/updateAutoCollect만 써도 그대로 동작한다).
interface ProjectContextValue {
  project: Project | null;
  updateAutoCollect: (enabled: boolean) => Promise<void>;
  competitors: Competitor[];
  refreshCompetitors: () => Promise<void>;
  campaignTags: CampaignTag[];
  refreshCampaignTags: () => Promise<void>;
}

export const ProjectContext = createContext<ProjectContextValue | null>(null);

export function useProjectContext(): ProjectContextValue {
  const ctx = useContext(ProjectContext);
  if (!ctx) throw new Error("useProjectContext must be used within a dashboard layout");
  return ctx;
}

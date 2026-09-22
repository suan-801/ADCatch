import type { Ad, AdFormat, AdStatus, CampaignTag, VisualType } from "@/lib/types";

// Part B — Gallery Filters. Brand 필터(기존 CompetitorFilter)는 그대로 유지하고, 이 컴포넌트는
// Status/Format/Visual/캠페인 태그/카피 검색만 추가로 담당한다. "70% 업무 툴" 톤을 유지하기 위해
// select dropdown 위주로 구성하고 pill을 남발하지 않는다.

export type StatusFilterValue = "ALL" | AdStatus;
export type FormatFilterValue = "ALL" | AdFormat;
export type VisualFilterValue = "ALL" | VisualType | "UNANALYZED";
// tag id 문자열 | "ALL" | "NEEDS_REVIEW"(검토 필요 — NEEDS_REVIEW 상태 또는 아직 태그가 없는 소재).
export type CampaignTagFilterValue = "ALL" | "NEEDS_REVIEW" | string;

export interface GalleryFilterState {
  status: StatusFilterValue;
  format: FormatFilterValue;
  visual: VisualFilterValue;
  campaignTagId: CampaignTagFilterValue;
  search: string;
}

export const DEFAULT_GALLERY_FILTERS: GalleryFilterState = {
  status: "ALL",
  format: "ALL",
  visual: "ALL",
  campaignTagId: "ALL",
  search: "",
};

export function isGalleryFilterActive(filters: GalleryFilterState): boolean {
  return (
    filters.status !== "ALL" ||
    filters.format !== "ALL" ||
    filters.visual !== "ALL" ||
    filters.campaignTagId !== "ALL" ||
    filters.search.trim() !== ""
  );
}

export function applyGalleryFilters<T extends Ad>(ads: T[], filters: GalleryFilterState): T[] {
  const q = filters.search.trim().toLowerCase();
  return ads.filter((ad) => {
    if (filters.status !== "ALL" && ad.status !== filters.status) return false;
    if (filters.format !== "ALL" && ad.format !== filters.format) return false;
    if (filters.visual === "UNANALYZED") {
      if (ad.visual_type !== null) return false;
    } else if (filters.visual !== "ALL" && ad.visual_type !== filters.visual) {
      return false;
    }
    if (filters.campaignTagId === "NEEDS_REVIEW") {
      if (ad.campaign_tag_id !== null) return false;
    } else if (filters.campaignTagId !== "ALL" && ad.campaign_tag_id !== filters.campaignTagId) {
      return false;
    }
    if (q) {
      const haystack = `${ad.copy_text ?? ""} ${ad.cta_text ?? ""}`.toLowerCase();
      if (!haystack.includes(q)) return false;
    }
    return true;
  });
}

const STATUS_LABEL: Record<StatusFilterValue, string> = {
  ALL: "전체",
  NEW: "신규",
  ACTIVE: "집행 중",
  INACTIVE: "종료",
};

const FORMAT_LABEL: Record<FormatFilterValue, string> = {
  ALL: "전체",
  IMAGE: "이미지",
  VIDEO: "영상",
  CAROUSEL: "캐러셀",
};

const VISUAL_LABEL: Record<VisualFilterValue, string> = {
  ALL: "전체",
  PERSON: "인물",
  PRODUCT: "제품",
  TEXT_HEAVY: "텍스트 중심",
  GRAPHIC: "그래픽",
  UNANALYZED: "미분석",
};

const selectClass =
  "rounded-lg border border-border bg-white px-2.5 py-1.5 text-xs font-medium text-foreground focus:border-brand focus:outline-none";

export function GalleryFilters({
  value,
  onChange,
  campaignTags = [],
}: {
  value: GalleryFilterState;
  onChange: (next: GalleryFilterState) => void;
  /** 캠페인 태그 필터 드롭다운 옵션 — 없으면(프로젝트에 태그가 없으면) 필터 자체를 숨긴다. */
  campaignTags?: CampaignTag[];
}) {
  const activeCampaignTags = campaignTags.filter((t) => t.is_active);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={value.status}
        onChange={(e) => onChange({ ...value, status: e.target.value as StatusFilterValue })}
        className={selectClass}
        aria-label="상태 필터"
      >
        {(Object.keys(STATUS_LABEL) as StatusFilterValue[]).map((v) => (
          <option key={v} value={v}>
            {STATUS_LABEL[v]}
          </option>
        ))}
      </select>

      <select
        value={value.format}
        onChange={(e) => onChange({ ...value, format: e.target.value as FormatFilterValue })}
        className={selectClass}
        aria-label="포맷 필터"
      >
        {(Object.keys(FORMAT_LABEL) as FormatFilterValue[]).map((v) => (
          <option key={v} value={v}>
            {FORMAT_LABEL[v]}
          </option>
        ))}
      </select>

      <select
        value={value.visual}
        onChange={(e) => onChange({ ...value, visual: e.target.value as VisualFilterValue })}
        className={selectClass}
        aria-label="비주얼 필터"
      >
        {(Object.keys(VISUAL_LABEL) as VisualFilterValue[]).map((v) => (
          <option key={v} value={v}>
            {VISUAL_LABEL[v]}
          </option>
        ))}
      </select>

      {activeCampaignTags.length > 0 && (
        <select
          value={value.campaignTagId}
          onChange={(e) => onChange({ ...value, campaignTagId: e.target.value })}
          className={selectClass}
          aria-label="캠페인 태그 필터"
        >
          <option value="ALL">캠페인 태그: 전체</option>
          {activeCampaignTags.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
          <option value="NEEDS_REVIEW">검토 필요</option>
        </select>
      )}

      <input
        value={value.search}
        onChange={(e) => onChange({ ...value, search: e.target.value })}
        placeholder="광고 카피 검색"
        className="min-w-[160px] flex-1 rounded-lg border border-border px-3 py-1.5 text-xs focus:border-brand focus:outline-none"
      />
    </div>
  );
}

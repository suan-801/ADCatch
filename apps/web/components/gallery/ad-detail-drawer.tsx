"use client";

import { useEffect, useState } from "react";
import type { Ad, AdHistoryEvent, CampaignTag } from "@/lib/types";
import { FORMAT_LABEL, VISUAL_LABEL, runningDays, survivalDays } from "@/lib/types";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

// Part C — Ad Detail Drawer. 새 route를 만들지 않고 Gallery Card 클릭 시 우측(모바일: 하단
// bottom sheet)에서 여는 오버레이 패널로 구현한다.

type DrawerAd = Ad & { competitor_name?: string };

const EVENT_LABEL: Record<AdHistoryEvent["event_type"], string> = {
  STARTED: "NEW",
  REACTIVATED: "REACTIVATED",
  STOPPED: "종료",
  BASELINE_DISCOVERED: "기존 집행",
};

function formatDate(iso: string): string {
  return iso.slice(0, 10).replaceAll("-", ".");
}

function CampaignTagSection({
  ad,
  campaignTags,
  onAdUpdated,
}: {
  ad: DrawerAd;
  campaignTags: CampaignTag[];
  onAdUpdated?: (ad: DrawerAd) => void;
}) {
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const activeTags = campaignTags.filter((t) => t.is_active);
  const currentTag = campaignTags.find((t) => t.id === ad.campaign_tag_id);

  const isNeedsReview = ad.campaign_classification_status === "NEEDS_REVIEW";
  const isUnclassified = ad.campaign_classification_status === "PENDING" || ad.campaign_classification_status === "FAILED";

  const handleChange = async (tagId: string) => {
    if (!tagId) return;
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateAdCampaignTag(ad.id, tagId);
      onAdUpdated?.({ ...ad, ...updated });
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  if (activeTags.length === 0) return null;

  return (
    <div>
      <p className="text-xs font-semibold text-muted">캠페인 태그</p>
      <div className="mt-1.5 flex flex-wrap items-center gap-2">
        {currentTag ? (
          <span className="rounded-full border border-border bg-slate-50 px-2.5 py-1 text-xs font-semibold text-foreground">
            {currentTag.name}
            <span className="ml-1 font-normal text-muted">
              {ad.campaign_tag_assignment_source === "USER"
                ? "· 사용자 지정"
                : ad.campaign_tag_confidence != null
                  ? `· AI 분류 ${Math.round(ad.campaign_tag_confidence * 100)}%`
                  : "· AI 분류"}
            </span>
          </span>
        ) : isNeedsReview ? (
          <span className="rounded-full border border-brand/40 bg-brand-cream px-2.5 py-1 text-xs font-semibold text-brand-dark">
            검토 필요
            {ad.campaign_tag_confidence != null && ` (확신도 ${Math.round(ad.campaign_tag_confidence * 100)}%)`}
          </span>
        ) : (
          <span className="rounded-full border border-border px-2.5 py-1 text-xs font-medium text-muted">
            {isUnclassified ? "분류 대기 중" : "미분류"}
          </span>
        )}
        <select
          value={currentTag?.id ?? ""}
          disabled={saving}
          onChange={(e) => handleChange(e.target.value)}
          className="rounded-full border border-border px-2 py-1 text-xs text-foreground disabled:opacity-50"
        >
          <option value="">태그 변경...</option>
          {activeTags.map((t) => (
            <option key={t.id} value={t.id}>
              {t.name}
            </option>
          ))}
        </select>
      </div>
      {ad.campaign_tag_reason && (
        <p className="mt-1.5 text-xs text-muted">근거: {ad.campaign_tag_reason}</p>
      )}
      {error && <p className="mt-1.5 text-xs text-status-inactive">태그 변경 실패: {error}</p>}
    </div>
  );
}

// IMAGE/VIDEO 2분류(2026-09-23 재설계) — 대표 썸네일 1장을 보여주고, VIDEO는 ▶ 배지만 덧붙인다.
// ffmpeg keyframe 추출/CAROUSEL 카드 grid는 제거했다(운영 복잡도 대비 가치가 낮다고 판단 —
// docs/DATA_SEMANTICS.md §10). 영상 원본을 보고 싶으면 하단 "Meta에서 보기" 버튼을 쓴다.
function MediaDetail({ ad }: { ad: DrawerAd }) {
  return (
    <div className="relative flex aspect-[4/5] items-center justify-center overflow-hidden rounded-xl bg-slate-50">
      {ad.image_url ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={ad.image_url}
          alt={ad.copy_text ?? "ad creative"}
          className="h-full w-full object-contain"
        />
      ) : (
        <span className="text-xs text-muted">미디어 없음</span>
      )}
      {ad.format === "VIDEO" && (
        <span className="absolute bottom-2 left-2 flex h-8 w-8 items-center justify-center rounded-full bg-foreground/70 text-sm text-white">
          ▶
        </span>
      )}
    </div>
  );
}

export function AdDetailDrawer({
  ad,
  onClose,
  campaignTags = [],
  onAdUpdated,
}: {
  ad: DrawerAd | null;
  onClose: () => void;
  campaignTags?: CampaignTag[];
  // 사용자가 Drawer 안에서 캠페인 태그를 바꾸면, Drawer를 닫았을 때 갤러리 카드에도 즉시 반영되도록
  // 갱신된 ad를 부모(대시보드 page.tsx)로 전달한다 — 전체 목록 refetch 없이 로컬 state만 갱신한다.
  onAdUpdated?: (ad: DrawerAd) => void;
}) {
  const [history, setHistory] = useState<AdHistoryEvent[] | null>(null);

  useEffect(() => {
    if (!ad) return;
    setHistory(null);
    api
      .getAdHistory(ad.id)
      .then((res) => setHistory(res.events))
      .catch(() => setHistory([]));
  }, [ad]);

  useEffect(() => {
    if (!ad) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [ad, onClose]);

  // Drawer가 열려 있는 동안 배경 스크롤을 완전히 잠근다 — 어두워진 배경 위에서 wheel/touch
  // 스크롤이 뒤쪽 페이지로 새어나가지 않게 한다. 닫히면(ad === null, 컴포넌트가 언마운트되는
  // 시점) cleanup이 항상 실행돼 기존 overflow/스크롤 위치가 그대로 복원된다.
  useEffect(() => {
    if (!ad) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [ad]);

  if (!ad) return null;

  const running = runningDays(ad);
  const survival = survivalDays(ad);
  // C-04: ad_archive_id로 Meta Ad Library의 공식 상세 페이지 URL을 구성한다 — 별도로 저장된
  // 직접 링크가 없으므로, 가짜 링크를 만드는 대신 Meta의 실제 공개 URL 패턴만 사용한다.
  const metaLibraryUrl = `https://www.facebook.com/ads/library/?id=${ad.ad_archive_id}`;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end bg-foreground/40 sm:items-stretch" onClick={onClose}>
      <div
        className="motion-safe:animate-fade-in-up flex max-h-[85vh] w-full flex-col overflow-y-auto overscroll-contain rounded-t-2xl bg-white shadow-xl sm:h-full sm:max-h-none sm:w-full sm:max-w-md sm:rounded-none sm:rounded-l-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <h3 className="text-sm font-bold text-foreground">광고 상세</h3>
          <button
            type="button"
            onClick={onClose}
            aria-label="닫기"
            className="rounded-full p-1.5 text-muted hover:bg-slate-100 hover:text-foreground"
          >
            ✕
          </button>
        </div>

        <div className="space-y-5 p-5">
          <MediaDetail ad={ad} />

          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={ad.status} />
            {ad.competitor_name && <span className="text-xs font-medium text-muted">{ad.competitor_name}</span>}
            {ad.format === "VIDEO" && (
              <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-muted">▶ 영상</span>
            )}
          </div>

          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
            <div>
              <dt className="text-muted">포맷</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{ad.format ? FORMAT_LABEL[ad.format] : "-"}</dd>
            </div>
            <div>
              <dt className="text-muted">비주얼</dt>
              <dd className="mt-0.5 font-semibold text-foreground">
                {ad.analysis_status === "PENDING"
                  ? "비주얼 분석 대기"
                  : ad.analysis_status === "FAILED"
                    ? "비주얼 분석 실패"
                    : ad.visual_type
                      ? VISUAL_LABEL[ad.visual_type]
                      : "-"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">{running.label} 일수</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{running.days}일째</dd>
            </div>
            <div>
              <dt className="text-muted">추적 일수(전체)</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{survival}일</dd>
            </div>
            <div>
              <dt className="text-muted">Meta 집행 시작일</dt>
              <dd className="mt-0.5 font-semibold text-foreground">
                {ad.source_started_at ? formatDate(ad.source_started_at) : "확인되지 않음"}
              </dd>
            </div>
            <div>
              <dt className="text-muted">ADCatcher 최초 발견</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{formatDate(ad.first_seen_at)}</dd>
            </div>
            <div>
              <dt className="text-muted">마지막 발견</dt>
              <dd className="mt-0.5 font-semibold text-foreground">{formatDate(ad.last_seen_at)}</dd>
            </div>
          </dl>

          <CampaignTagSection ad={ad} campaignTags={campaignTags} onAdUpdated={onAdUpdated} />

          {ad.copy_text && (
            <div>
              <p className="text-xs font-semibold text-muted">광고 카피</p>
              <p className="mt-1 whitespace-pre-wrap text-sm text-foreground">{ad.copy_text}</p>
            </div>
          )}

          {ad.cta_text && (
            <div>
              <p className="text-xs font-semibold text-muted">CTA</p>
              <p className="mt-1 text-sm text-foreground">{ad.cta_text}</p>
            </div>
          )}

          <div>
            <p className="text-xs font-semibold text-muted">변화 이력</p>
            {history === null ? (
              <p className="mt-2 text-xs text-muted">불러오는 중...</p>
            ) : history.length === 0 ? (
              <p className="mt-2 text-xs text-muted">기록된 변화 이력이 없어요.</p>
            ) : (
              <ul className="mt-2 space-y-1.5">
                {history.map((event, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs">
                    <span className="font-medium text-muted">{formatDate(event.event_date)}</span>
                    <span className="font-semibold text-foreground">{EVENT_LABEL[event.event_type]}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <a
            href={metaLibraryUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="block w-full rounded-full border border-border px-4 py-2.5 text-center text-sm font-semibold text-foreground hover:border-brand hover:text-brand-dark"
          >
            Meta에서 보기
          </a>
        </div>
      </div>
    </div>
  );
}

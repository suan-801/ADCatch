"use client";

import { useEffect, useState } from "react";
import type { Ad, AdHistoryEvent } from "@/lib/types";
import { runningDays, survivalDays } from "@/lib/types";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/status-badge";

// Part C — Ad Detail Drawer. 새 route를 만들지 않고 Gallery Card 클릭 시 우측(모바일: 하단
// bottom sheet)에서 여는 오버레이 패널로 구현한다.

type DrawerAd = Ad & { competitor_name?: string };

const FORMAT_LABEL: Record<string, string> = { IMAGE: "이미지", VIDEO: "영상", CAROUSEL: "캐러셀" };
const VISUAL_LABEL: Record<string, string> = {
  PERSON: "인물",
  PRODUCT: "제품",
  TEXT_HEAVY: "텍스트 중심",
  GRAPHIC: "그래픽",
};
const EVENT_LABEL: Record<AdHistoryEvent["event_type"], string> = {
  STARTED: "NEW",
  REACTIVATED: "REACTIVATED",
  STOPPED: "종료",
  BASELINE_DISCOVERED: "기존 집행",
};

function formatDate(iso: string): string {
  return iso.slice(0, 10).replaceAll("-", ".");
}

export function AdDetailDrawer({ ad, onClose }: { ad: DrawerAd | null; onClose: () => void }) {
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

  if (!ad) return null;

  const running = runningDays(ad);
  const survival = survivalDays(ad);
  // C-04: ad_archive_id로 Meta Ad Library의 공식 상세 페이지 URL을 구성한다 — 별도로 저장된
  // 직접 링크가 없으므로, 가짜 링크를 만드는 대신 Meta의 실제 공개 URL 패턴만 사용한다.
  const metaLibraryUrl = `https://www.facebook.com/ads/library/?id=${ad.ad_archive_id}`;

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-end bg-foreground/40 sm:items-stretch" onClick={onClose}>
      <div
        className="motion-safe:animate-fade-in-up flex max-h-[85vh] w-full flex-col overflow-y-auto rounded-t-2xl bg-white shadow-xl sm:h-full sm:max-h-none sm:w-full sm:max-w-md sm:rounded-none sm:rounded-l-2xl"
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
          <div className="flex aspect-[4/5] items-center justify-center rounded-xl bg-slate-50">
            {ad.image_url ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                src={ad.image_url}
                alt={ad.copy_text ?? "ad creative"}
                className="h-full w-full rounded-xl object-contain"
              />
            ) : (
              <span className="text-xs text-muted">미디어 없음</span>
            )}
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={ad.status} />
            {ad.competitor_name && <span className="text-xs font-medium text-muted">{ad.competitor_name}</span>}
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

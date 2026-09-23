import type { Ad, CampaignTag } from "@/lib/types";
import { runningDays, survivalDays } from "@/lib/types";
import { StatusBadge } from "@/components/status-badge";

type GalleryAd = Ad & { competitor_name?: string };

function CampaignTagBadge({ ad, campaignTags }: { ad: GalleryAd; campaignTags: CampaignTag[] }) {
  const tag = campaignTags.find((t) => t.id === ad.campaign_tag_id);
  if (tag) {
    return (
      <span className="truncate rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-muted">
        {tag.name}
        {ad.campaign_tag_assignment_source === "AI" ? " · AI 분류" : ""}
      </span>
    );
  }
  if (ad.campaign_classification_status === "NEEDS_REVIEW") {
    return (
      <span className="truncate rounded-full bg-brand-cream px-2 py-0.5 text-[10px] font-semibold text-brand-dark">
        검토 필요
      </span>
    );
  }
  return null;
}

export function AdGallery({
  ads,
  totalCount,
  onCardClick,
  campaignTags = [],
}: {
  /** 필터 적용 후 렌더링할 소재 목록. */
  ads: GalleryAd[];
  /** 필터 적용 전(브랜드 필터까지만 반영된) 전체 개수 — B-08: "데이터 없음"과 "필터 결과 없음"을
   * 구분하기 위해 필요하다. */
  totalCount: number;
  onCardClick: (ad: GalleryAd) => void;
  /** 카드에 캠페인 태그 배지를 표시하기 위한 프로젝트의 태그 목록(선택 — 없으면 배지 생략). */
  campaignTags?: CampaignTag[];
}) {
  const sorted = [...ads].sort((a, b) => survivalDays(b) - survivalDays(a));

  if (totalCount === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted">
        아직 수집된 소재가 없습니다. 브랜드를 등록하고 수집을 실행해보세요.
      </div>
    );
  }

  if (sorted.length === 0) {
    return (
      <div className="rounded-2xl border border-dashed border-border p-12 text-center text-sm text-muted">
        조건에 맞는 광고가 없어요.
        <br />
        필터를 변경해보세요.
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 xl:grid-cols-3">
      {sorted.map((ad) => {
        const running = runningDays(ad);
        return (
          <div
            key={ad.id}
            role="button"
            tabIndex={0}
            onClick={() => onCardClick(ad)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onCardClick(ad);
              }
            }}
            className="group cursor-pointer overflow-hidden rounded-2xl border border-border bg-white text-left transition-shadow hover:shadow-md"
          >
            <div className="relative flex aspect-[4/5] items-center justify-center bg-slate-50">
              {ad.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={ad.image_url}
                  alt={ad.copy_text ?? "ad creative"}
                  className="h-full w-full object-contain transition-transform group-hover:scale-[1.02]"
                />
              ) : (
                <span className="text-xs text-muted">{ad.format ?? "미디어 없음"}</span>
              )}
              {/* 브리핑 §25: 생존일수는 작은 메타데이터가 아니라 강한 시각적 배지로 표현.
                  P0-06 의미는 그대로 유지하되("집행"=실제 Meta 집행 시작일 기준,
                  "추적"=ADCatcher가 처음 발견한 시점 기준) "2집행"처럼 붙어 읽히던 표기를
                  "집행 2일째" 형태 + 툴팁으로 풀어써 한눈에 뜻이 들어오게 한다. */}
              <div
                className="absolute right-2 top-2 rounded-xl bg-foreground/80 px-2.5 py-1.5 text-right text-white backdrop-blur-sm"
                title={
                  running.label === "집행"
                    ? `이 광고가 Meta에서 실제로 집행된 지 ${running.days}일째예요.`
                    : `ADCatcher가 이 광고를 처음 발견한 지 ${running.days}일째예요. (실제 집행 시작일은 확인되지 않았어요)`
                }
              >
                <p className="text-lg font-extrabold leading-none tabular-nums">{running.days}일째</p>
                <p className="text-[9px] font-semibold uppercase tracking-wide text-white/70">{running.label} 중</p>
              </div>
              {ad.analysis_status === "PENDING" && (
                <span className="absolute left-2 top-2 rounded-full bg-white/90 px-2 py-1 text-[9px] font-semibold text-muted">
                  비주얼 분석 대기
                </span>
              )}
              {/* IMAGE/VIDEO 2분류(2026-09-23) — 대표 썸네일 1장만 보여주고, VIDEO는 ▶ 배지만 붙인다. */}
              {ad.format === "VIDEO" && (
                <span className="absolute bottom-2 left-2 flex h-6 w-6 items-center justify-center rounded-full bg-foreground/80 text-xs text-white">
                  ▶
                </span>
              )}
            </div>
            <div className="space-y-2 p-4">
              <div className="flex items-center justify-between gap-2">
                <StatusBadge status={ad.status} />
                {ad.competitor_name && (
                  <span className="truncate text-xs font-medium text-muted">{ad.competitor_name}</span>
                )}
              </div>
              <CampaignTagBadge ad={ad} campaignTags={campaignTags} />
              {ad.copy_text && <p className="line-clamp-2 text-sm text-foreground">{ad.copy_text}</p>}
              {ad.cta_text && <p className="text-xs text-muted">CTA: {ad.cta_text}</p>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

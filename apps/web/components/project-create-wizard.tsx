"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { SyncResult } from "@/lib/types";
import { isValidMetaAdLibraryUrl, META_AD_LIBRARY_URL_ERROR } from "@/lib/validation";

// Part E — New Project Onboarding: "Project 생성 → 빈 Dashboard → 하단에서 Brand 추가" 대신
// Project(Step1) → Brand(Step2) → Initial Collection(Step3~4)의 짧은 온보딩으로 만든다.
// Landing의 새 프로젝트 생성과 Sidebar의 "+ NEW PROJECT"가 이 컴포넌트 하나를 공유한다(E-02) —
// 두 위치가 서로 다른 로직을 갖지 않는다.
//
// E-05/E-08: 이 컴포넌트는 새 API 계약을 만들지 않는다 — 기존 createProject / createCompetitor /
// collectNow(=/competitors/{id}/ads/collect)를 그대로 순차/제한 병렬로 호출한다. Baseline 판정은
// 전적으로 app.services.ad_sync.synchronize_ad_status(SyncResult.is_baseline/snapshot_complete)에
// 위임하며, 프론트는 그 결과를 표시만 한다 — 새 Brand의 첫 수집을 "오늘 신규 N개"로 직접 계산하지 않는다.

type Step = "project" | "brand" | "collecting" | "done";

interface BrandRow {
  key: string;
  name: string;
  url: string;
}

type BrandOutcome =
  | { status: "pending" }
  | { status: "collecting"; competitorId: string }
  | { status: "success"; adCount: number; competitorId: string }
  | { status: "partial"; competitorId: string }
  // competitorId가 없으면 브랜드(경쟁사) row 생성 자체가 실패한 경우 — 재시도 버튼을 숨긴다.
  | { status: "failed"; error: string; competitorId?: string };

let rowKeySeq = 0;
const nextRowKey = () => `row-${++rowKeySeq}`;

// G-06과 동일한 원칙: 첫 수집(Apify + enrichment)이 브랜드당 수십 초~분 단위로 걸릴 수 있으므로,
// 무제한 Promise.all이 아니라 제한 동시성(기본 2)으로 순회한다.
async function runWithConcurrency<T>(items: T[], limit: number, worker: (item: T) => Promise<void>) {
  let cursor = 0;
  async function runNext(): Promise<void> {
    const i = cursor++;
    if (i >= items.length) return;
    await worker(items[i]);
    return runNext();
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, runNext));
}

export function ProjectCreateWizard({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  /** 프로젝트 row가 생성된 직후(브랜드/수집 완료 전) 호출 — 호출부가 프로젝트 목록을 갱신할 때 사용. */
  onCreated?: () => void;
}) {
  const router = useRouter();

  const [step, setStep] = useState<Step>("project");
  const [projectName, setProjectName] = useState("");
  const [brands, setBrands] = useState<BrandRow[]>([{ key: nextRowKey(), name: "", url: "" }]);
  const [error, setError] = useState<string | null>(null);

  const [projectId, setProjectId] = useState<string | null>(null);
  const [alreadyAutoCollect, setAlreadyAutoCollect] = useState(false);
  const [outcomes, setOutcomes] = useState<Record<string, BrandOutcome>>({});
  const [optInState, setOptInState] = useState<"idle" | "submitting" | "failed">("idle");

  const reset = () => {
    setStep("project");
    setProjectName("");
    setBrands([{ key: nextRowKey(), name: "", url: "" }]);
    setError(null);
    setProjectId(null);
    setOutcomes({});
    setOptInState("idle");
  };

  const handleClose = () => {
    if (step === "collecting") return; // 수집 중에는 닫기로 흐름을 끊지 않는다.
    reset();
    onClose();
  };

  const updateBrand = (key: string, patch: Partial<BrandRow>) =>
    setBrands((prev) => prev.map((b) => (b.key === key ? { ...b, ...patch } : b)));

  const addBrandRow = () => setBrands((prev) => [...prev, { key: nextRowKey(), name: "", url: "" }]);
  const removeBrandRow = (key: string) =>
    setBrands((prev) => (prev.length <= 1 ? prev : prev.filter((b) => b.key !== key)));

  const filledBrands = brands.filter((b) => b.name.trim() && b.url.trim());
  // E-01: URL이 채워져 있지만 Meta Ad Library 형식이 아닌 row가 하나라도 있으면 진행을 막는다.
  const hasInvalidUrl = filledBrands.some((b) => !isValidMetaAdLibraryUrl(b.url.trim()));
  const validBrands = hasInvalidUrl ? [] : filledBrands;

  const runCollectionFor = async (competitorId: string, rowKey: string) => {
    setOutcomes((prev) => ({ ...prev, [rowKey]: { status: "collecting", competitorId } }));
    try {
      const result: SyncResult = await api.collectNow(competitorId);
      if (result.is_baseline && result.snapshot_complete) {
        setOutcomes((prev) => ({
          ...prev,
          [rowKey]: { status: "success", adCount: result.new_ads, competitorId },
        }));
      } else {
        // PARTIAL(max_ads 상한) 또는 이미 baseline이 있던 경우 — 완전한 성공으로 취급하지 않는다(E-09).
        setOutcomes((prev) => ({ ...prev, [rowKey]: { status: "partial", competitorId } }));
      }
    } catch (e) {
      setOutcomes((prev) => ({ ...prev, [rowKey]: { status: "failed", error: String(e), competitorId } }));
    }
  };

  const handleCreateAndCollect = async () => {
    if (validBrands.length === 0) return;
    setError(null);
    setStep("collecting");

    try {
      const project = await api.createProject(projectName.trim());
      setProjectId(project.id);
      setAlreadyAutoCollect(project.auto_collect_enabled);
      onCreated?.();

      const initial: Record<string, BrandOutcome> = {};
      const rowToCompetitor: { row: BrandRow; competitorId: string }[] = [];

      // 1) 브랜드(경쟁사) row 생성은 순차로 — Apify를 부르지 않는 가벼운 API 호출.
      for (const row of validBrands) {
        initial[row.key] = { status: "pending" };
        setOutcomes({ ...initial });
        try {
          const competitor = await api.createCompetitor(project.id, {
            name: row.name.trim(),
            ad_library_url: row.url.trim(),
          });
          rowToCompetitor.push({ row, competitorId: competitor.id });
        } catch (e) {
          initial[row.key] = { status: "failed", error: String(e) };
          setOutcomes({ ...initial });
        }
      }

      // 2) 첫 Collection(Apify+enrichment)만 bounded concurrency(2)로 실행.
      await runWithConcurrency(rowToCompetitor, 2, ({ row, competitorId }) =>
        runCollectionFor(competitorId, row.key),
      );

      setStep("done");
    } catch (e) {
      setError(String(e));
      setStep("brand");
    }
  };

  const retryBrand = (row: BrandRow) => {
    const outcome = outcomes[row.key];
    if (outcome && "competitorId" in outcome && outcome.competitorId) {
      runCollectionFor(outcome.competitorId, row.key);
    }
  };

  // D-01: updateProject 실패 시 finally에서 무조건 navigate하던 버그를 수정 — 성공했을 때만
  // Dashboard로 이동한다. 실패하면 이 completion step에 그대로 남아 에러 메시지와 재시도 버튼을 보여준다.
  const handleOptIn = async () => {
    if (!projectId) return;
    setOptInState("submitting");
    try {
      await api.updateProject(projectId, { auto_collect_enabled: true });
      finishAndNavigate();
    } catch {
      setOptInState("failed");
    }
  };

  const finishAndNavigate = () => {
    const id = projectId;
    reset();
    onClose();
    if (id) router.push(`/dashboard/${id}`);
  };

  if (!open) return null;

  const successOutcomes = Object.values(outcomes).filter(
    (o): o is Extract<BrandOutcome, { status: "success" }> => o.status === "success",
  );
  const totalAds = successOutcomes.reduce((sum, o) => sum + o.adCount, 0);
  const successBrandCount = successOutcomes.length;
  const allSettled =
    validBrands.length > 0 &&
    validBrands.every((row) => {
      const o = outcomes[row.key];
      return o && (o.status === "success" || o.status === "partial" || o.status === "failed");
    });

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 p-4 motion-safe:animate-fade-in-up"
      onClick={handleClose}
    >
      <div
        className="w-full max-w-lg rounded-2xl bg-white p-6 shadow-xl sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        {step !== "collecting" && (
          <button
            type="button"
            onClick={handleClose}
            aria-label="닫기"
            className="float-right rounded-full p-1 text-muted hover:bg-slate-100 hover:text-foreground"
          >
            ✕
          </button>
        )}

        {step === "project" && (
          <div>
            <h3 className="text-lg font-bold text-foreground">새 프로젝트</h3>
            <p className="mt-1 text-xs text-muted">프로젝트 1개 = 추적할 브랜드 묶음 1세트예요.</p>
            <input
              value={projectName}
              onChange={(e) => setProjectName(e.target.value)}
              placeholder="프로젝트명을 입력해주세요"
              autoFocus
              className="mt-5 w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:border-brand focus:outline-none"
              onKeyDown={(e) => e.key === "Enter" && projectName.trim() && setStep("brand")}
            />
            <button
              type="button"
              onClick={() => setStep("brand")}
              disabled={!projectName.trim()}
              className="mt-5 w-full rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
            >
              다음
            </button>
          </div>
        )}

        {step === "brand" && (
          <div>
            <h3 className="text-lg font-bold text-foreground">추적할 브랜드를 등록해주세요</h3>
            <p className="mt-1 text-xs text-muted">Meta Ad Library URL로 등록하면 첫 수집을 바로 시작해요.</p>

            <div className="mt-5 space-y-3">
              {brands.map((row) => (
                <div key={row.key} className="rounded-xl border border-border p-3">
                  <div className="flex items-center gap-2">
                    <input
                      value={row.name}
                      onChange={(e) => updateBrand(row.key, { name: e.target.value })}
                      placeholder="브랜드명을 입력해주세요"
                      className="min-w-0 flex-1 rounded-lg border border-border px-3 py-2 text-sm focus:border-brand focus:outline-none"
                    />
                    {brands.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeBrandRow(row.key)}
                        aria-label="브랜드 삭제"
                        className="shrink-0 rounded-full p-1.5 text-muted hover:bg-slate-100 hover:text-status-inactive"
                      >
                        ✕
                      </button>
                    )}
                  </div>
                  <input
                    value={row.url}
                    onChange={(e) => updateBrand(row.key, { url: e.target.value })}
                    placeholder="Meta Ad Library URL을 입력해주세요"
                    className={`mt-2 w-full rounded-lg border px-3 py-2 text-xs focus:outline-none ${
                      row.url.trim() && !isValidMetaAdLibraryUrl(row.url.trim())
                        ? "border-status-inactive focus:border-status-inactive"
                        : "border-border focus:border-brand"
                    }`}
                  />
                  {row.url.trim() && !isValidMetaAdLibraryUrl(row.url.trim()) ? (
                    <p className="mt-1 text-[11px] font-medium text-status-inactive">{META_AD_LIBRARY_URL_ERROR}</p>
                  ) : (
                    <p className="mt-1 text-[11px] text-muted">
                      Meta Ad Library에서 브랜드 페이지를 연 뒤 브라우저 주소를 붙여넣어주세요.
                    </p>
                  )}
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={addBrandRow}
              className="mt-3 rounded-full border border-dashed border-border px-3.5 py-1.5 text-xs font-semibold text-muted hover:border-brand hover:text-brand-dark"
            >
              + 브랜드 추가
            </button>

            {error && <p className="mt-3 text-xs text-status-inactive">{error}</p>}

            <div className="mt-6 flex items-center gap-2">
              <button
                type="button"
                onClick={() => setStep("project")}
                className="rounded-full px-4 py-2.5 text-sm font-medium text-muted hover:text-foreground"
              >
                이전
              </button>
              <button
                type="button"
                onClick={handleCreateAndCollect}
                disabled={validBrands.length === 0}
                className="flex-1 rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
              >
                프로젝트 만들고 첫 수집 시작
              </button>
            </div>
          </div>
        )}

        {step === "collecting" && (
          <CollectingPanel brands={validBrands} outcomes={outcomes} onRetry={retryBrand} allSettled={allSettled} />
        )}

        {step === "done" && (
          <div className="text-center">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/mascot/catcher-hero.webp" alt="캐쳐" className="mx-auto w-20" />
            {successBrandCount > 0 ? (
              <p className="mt-4 text-lg font-bold text-foreground">
                {successBrandCount}개 브랜드에서
                <br />
                {totalAds}개의 광고를 기준으로 저장했어요!
              </p>
            ) : (
              <p className="mt-4 text-lg font-bold text-foreground">첫 수집이 아직 완료되지 않았어요</p>
            )}

            {alreadyAutoCollect ? (
              <p className="mt-4 text-sm text-muted">이 프로젝트는 이미 매일 자동으로 변화를 CATCH하고 있어요.</p>
            ) : (
              <>
                <p className="mt-5 text-base font-bold text-foreground">앞으로 매일 변화를 CATCH하시겠어요?</p>
                <p className="mt-1 text-xs text-muted">매일 자동으로 새로운 광고와 종료된 광고를 확인해드려요.</p>
                {optInState === "failed" && (
                  <p className="mt-3 text-xs font-medium text-status-inactive">
                    자동 추적을 설정하지 못했어요.
                    <br />
                    잠시 후 다시 시도해주세요.
                  </p>
                )}
                <div className="mt-5 flex flex-col items-center gap-2 sm:flex-row sm:justify-center">
                  <button
                    type="button"
                    onClick={handleOptIn}
                    disabled={optInState === "submitting"}
                    className="w-full rounded-full bg-brand px-6 py-3 text-sm font-bold text-white transition-opacity hover:opacity-90 disabled:opacity-60 sm:w-auto"
                  >
                    {optInState === "submitting"
                      ? "설정 중..."
                      : optInState === "failed"
                        ? "다시 설정하기"
                        : "매일 변화 CATCH하기"}
                  </button>
                  <button
                    type="button"
                    onClick={finishAndNavigate}
                    disabled={optInState === "submitting"}
                    className="rounded-full px-4 py-2 text-sm font-medium text-muted hover:text-foreground disabled:opacity-60"
                  >
                    나중에
                  </button>
                </div>
              </>
            )}

            {alreadyAutoCollect && (
              <button
                type="button"
                onClick={finishAndNavigate}
                className="mt-6 w-full rounded-full bg-brand px-6 py-3 text-sm font-bold text-white transition-opacity hover:opacity-90"
              >
                대시보드 보기
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function CollectingPanel({
  brands,
  outcomes,
  onRetry,
  allSettled,
}: {
  brands: BrandRow[];
  outcomes: Record<string, BrandOutcome>;
  onRetry: (row: BrandRow) => void;
  allSettled: boolean;
}) {
  return (
    <div>
      <h3 className="text-lg font-bold text-foreground">광고를 CATCH하고 있어요</h3>
      <p className="mt-1 text-xs text-muted">
        브랜드마다 Meta 광고 확인 → 저장 → 비주얼 분석 순서로 진행돼요. 화면을 벗어나지 않아도 괜찮아요.
      </p>

      <div className="mt-5 space-y-2">
        {brands.map((row) => {
          const o = outcomes[row.key] ?? { status: "pending" as const };
          return (
            <div
              key={row.key}
              className="flex items-center justify-between gap-3 rounded-xl border border-border px-4 py-3"
            >
              <span className="truncate text-sm font-semibold text-foreground">{row.name}</span>
              {o.status === "pending" && <span className="shrink-0 text-xs text-muted">대기 중...</span>}
              {o.status === "collecting" && (
                <span className="shrink-0 text-xs font-medium text-brand-dark">광고 수집 중...</span>
              )}
              {o.status === "success" && (
                <span className="shrink-0 text-xs font-semibold text-status-active">✓ {o.adCount}개</span>
              )}
              {o.status === "partial" && (
                <span className="shrink-0 text-xs font-medium text-muted">
                  ✓ 수집됨 (전체 확인은 다음 수집부터)
                </span>
              )}
              {o.status === "failed" && (
                <div className="flex shrink-0 items-center gap-2">
                  <span className="text-xs text-status-inactive">
                    ⚠ {o.competitorId ? "수집 실패" : "브랜드 등록 실패"}
                  </span>
                  {o.competitorId && (
                    <button
                      type="button"
                      onClick={() => onRetry(row)}
                      className="rounded-full border border-border px-2.5 py-1 text-[11px] font-semibold text-foreground hover:border-brand hover:text-brand-dark"
                    >
                      다시 시도
                    </button>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {!allSettled && (
        <p className="mt-4 text-center text-[11px] text-muted">브랜드가 많을수록 시간이 더 걸릴 수 있어요.</p>
      )}
    </div>
  );
}

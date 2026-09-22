"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type {
  CampaignTag,
  CampaignTagClassificationStatusSummary,
  CampaignTagProcessPendingResult,
  CampaignTagReclassifyResult,
} from "@/lib/types";
import { useProjectContext } from "@/lib/project-context";
import { useAuth } from "@/lib/auth-context";

// §10 — 캠페인 태그 관리. 최초 생성자만 정의를 아는 구조를 금지한다: 이름/정의를 항상 목록에서
// 확인할 수 있고, 누구나(Viewer 포함) 조회할 수 있다. 생성/수정/삭제/재분류만 Admin 전용.

type EditingState = { id: string | null; name: string; definition: string };

const EMPTY_FORM: EditingState = { id: null, name: "", definition: "" };
const STATUS_POLL_INTERVAL_MS = 5000;

export default function CampaignTagsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { isAdmin } = useAuth();
  const { campaignTags, refreshCampaignTags } = useProjectContext();

  const [includeInactive, setIncludeInactive] = useState(false);
  const [form, setForm] = useState<EditingState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // §2 — "현재 프로젝트 소재 분류 상태" 스냅샷. 굿네이버스 사례처럼 태그가 없던 시절 생성된
  // 기존 광고가 이미 PENDING인 경우에도, 이 카드는 항상 그 수를 명확히 보여준다(버튼을 눌러야만
  // 보이는 게 아니라 페이지 진입 즉시 보인다).
  const [status, setStatus] = useState<CampaignTagClassificationStatusSummary | null>(null);
  const [reclassifyResult, setReclassifyResult] = useState<CampaignTagReclassifyResult | null>(null);
  const [reclassifying, setReclassifying] = useState(false);
  const [includeUserAssigned, setIncludeUserAssigned] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [processResult, setProcessResult] = useState<CampaignTagProcessPendingResult | null>(null);
  const [statusError, setStatusError] = useState<string | null>(null);

  const visibleTags = includeInactive ? campaignTags : campaignTags.filter((t: CampaignTag) => t.is_active);
  const hasActiveTags = campaignTags.some((t: CampaignTag) => t.is_active);

  const refreshStatus = useCallback(() => {
    if (!projectId) return;
    api
      .getCampaignTagClassificationStatus(projectId)
      .then(setStatus)
      .catch((e) => setStatusError(String(e)));
  }, [projectId]);

  useEffect(() => {
    refreshStatus();
  }, [refreshStatus]);

  // 페이지를 열어둔 동안에만 짧게 polling한다(대기 중인 소재가 있을 때만) — Daily Scheduler가
  // 백그라운드에서 처리한 결과도 반영되도록. 브라우저가 작업 큐를 소유하는 구조는 아니다 — 페이지를
  // 떠나면 polling도 멈추지만, 실제 분류(Gemini 호출)는 서버의 Daily Scheduler가 계속 담당한다.
  useEffect(() => {
    if (!status || status.pending === 0) return;
    const timer = setInterval(refreshStatus, STATUS_POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [status, refreshStatus]);

  const openCreateForm = () => {
    setForm({ ...EMPTY_FORM });
    setError(null);
  };
  const openEditForm = (tag: CampaignTag) => {
    setForm({ id: tag.id, name: tag.name, definition: tag.definition });
    setError(null);
  };

  const handleSave = async () => {
    if (!form) return;
    if (!form.name.trim() || !form.definition.trim()) {
      setError("태그명과 정의를 모두 입력하세요.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      if (form.id) {
        await api.updateCampaignTag(form.id, { name: form.name, definition: form.definition });
      } else {
        await api.createCampaignTag(projectId, { name: form.name, definition: form.definition });
      }
      setForm(null);
      await refreshCampaignTags();
      refreshStatus();
    } catch (e) {
      setError(String(e));
    } finally {
      setSaving(false);
    }
  };

  const handleDeactivate = async (tag: CampaignTag) => {
    if (!confirm(`'${tag.name}' 태그를 비활성화할까요? 기존 소재의 태그 표시는 유지됩니다.`)) return;
    await api.deleteCampaignTag(tag.id);
    await refreshCampaignTags();
    refreshStatus();
  };

  const handleReflectExisting = async () => {
    setReclassifying(true);
    setStatusError(null);
    try {
      const result = await api.reclassifyCampaignTags(projectId, includeUserAssigned);
      setReclassifyResult(result);
      setProcessResult(null);
      refreshStatus();
    } catch (e) {
      setStatusError(String(e));
    } finally {
      setReclassifying(false);
    }
  };

  const handleProcessNow = async () => {
    setProcessing(true);
    setStatusError(null);
    try {
      const result = await api.processPendingCampaignTags(projectId);
      setProcessResult(result);
      refreshStatus();
    } catch (e) {
      setStatusError(String(e));
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-foreground">캠페인 태그 관리</h2>
          <p className="mt-1 text-xs text-muted">
            프로젝트마다 캠페인 분류 기준을 직접 정의합니다. Gemini가 신규 소재를 이 기준으로 자동
            분류하고, 확신이 낮으면 &quot;검토 필요&quot;로 남깁니다.
          </p>
          {/* §1 — Viewer/Admin 모두에게 항상 노출. Viewer는 수정 버튼이 아예 안 보이므로, 왜
              없는지(권한이 아니라 문의 대상임을) 알려주는 안내다. alert 톤이 아니라 muted 캡션. */}
          <p className="mt-1 text-xs text-muted">※ 태그 추가/수정/삭제는 관리자에게 문의 부탁드립니다.</p>
        </div>
        {isAdmin && (
          <button
            type="button"
            onClick={openCreateForm}
            className="whitespace-nowrap rounded-full bg-brand px-4 py-2 text-xs font-semibold text-white hover:opacity-90"
          >
            + 태그 추가
          </button>
        )}
      </div>

      {/* §2 — "기존 광고 반영" 상태 카드. 버튼을 눌러야만 보이는 배너가 아니라 항상 노출되어,
          굿네이버스 사례처럼 이미 PENDING인 기존 광고도 그 수가 명확히 보이게 한다. */}
      <div className="rounded-2xl border border-border bg-white p-4">
        <h3 className="text-sm font-bold text-foreground">기존 광고 재분류</h3>
        {status ? (
          <p className="mt-1 text-xs text-muted">
            현재 분류 상태 — 대기 {status.pending} · 완료 {status.success} · 검토 필요{" "}
            {status.needs_review} · 실패 {status.failed}
          </p>
        ) : (
          <p className="mt-1 text-xs text-muted">불러오는 중...</p>
        )}

        {reclassifyResult && (
          <p className="mt-2 text-xs text-brand-dark">
            총 대상 {reclassifyResult.total_target_count}개(리셋 {reclassifyResult.reset_count} · 이미
            대기 중 {reclassifyResult.already_pending_count}) — 아래 &quot;지금 재분류 실행&quot;을
            누르거나, Daily Scheduler가 순차적으로 처리해요.
          </p>
        )}
        {processing && (
          <p className="mt-2 text-xs text-brand-dark">
            Gemini가 최대 {"10"}개 소재를 분류하고 있어요...
          </p>
        )}
        {processResult && !processing && (
          <p className="mt-2 text-xs text-muted">
            이번 실행: {processResult.processed}개 처리(성공 {processResult.succeeded} · 검토 필요{" "}
            {processResult.needs_review} · 대기 {processResult.still_pending} · 실패{" "}
            {processResult.failed}) · 남은 대기 {processResult.pending_remaining}개
            {processResult.quota_stopped && " · Gemini 할당량 초과로 일시 중단됐어요."}
          </p>
        )}
        {statusError && <p className="mt-2 text-xs text-status-inactive">{statusError}</p>}

        {isAdmin && hasActiveTags && (
          <div className="mt-3 space-y-2">
            <label className="flex items-center gap-1.5 text-xs text-muted">
              <input
                type="checkbox"
                checked={includeUserAssigned}
                onChange={(e) => setIncludeUserAssigned(e.target.checked)}
              />
              사용자가 직접 지정한 소재도 재분류 대상에 포함
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={handleReflectExisting}
                disabled={reclassifying}
                className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground hover:border-brand hover:text-brand-dark disabled:opacity-60"
              >
                {reclassifying ? "처리 중..." : "기존 광고 반영"}
              </button>
              <button
                type="button"
                onClick={handleProcessNow}
                disabled={processing || !status || status.pending === 0}
                className="rounded-full bg-brand px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
              >
                {processing ? "분류 중..." : "지금 재분류 실행"}
              </button>
            </div>
          </div>
        )}
        {!hasActiveTags && (
          <p className="mt-2 text-xs text-muted">활성 태그를 먼저 추가하면 자동 분류가 시작돼요.</p>
        )}
      </div>

      {form && (
        <div className="space-y-3 rounded-2xl border border-border bg-white p-4">
          <div>
            <label className="text-xs font-semibold text-muted">태그명</label>
            <input
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              placeholder="예: 굿즈"
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-brand focus:outline-none"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-muted">정의</label>
            <textarea
              value={form.definition}
              onChange={(e) => setForm({ ...form, definition: e.target.value })}
              placeholder="예: 팔찌, 다이어리, 키링 등 상품 구매를 유도하는 광고"
              rows={3}
              className="mt-1 w-full rounded-lg border border-border px-3 py-2 text-sm focus:border-brand focus:outline-none"
            />
          </div>
          {error && <p className="text-xs text-status-inactive">{error}</p>}
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-full bg-brand px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
            >
              {saving ? "저장 중..." : "저장"}
            </button>
            <button
              type="button"
              onClick={() => setForm(null)}
              className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-foreground"
            >
              취소
            </button>
          </div>
          <p className="text-xs text-muted">
            저장 후에는 위 &quot;기존 광고 재분류&quot; 카드에서 &quot;기존 광고 반영&quot;을 눌러
            새 기준을 적용하세요.
          </p>
        </div>
      )}

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-foreground">태그 목록 ({visibleTags.length})</h3>
        <label className="flex items-center gap-1.5 text-xs text-muted">
          <input type="checkbox" checked={includeInactive} onChange={(e) => setIncludeInactive(e.target.checked)} />
          비활성 태그 포함 보기
        </label>
      </div>

      {visibleTags.length === 0 ? (
        <p className="rounded-2xl border border-dashed border-border p-10 text-center text-sm text-muted">
          아직 캠페인 태그가 없어요. 태그를 추가하면 Gemini가 신규 소재를 자동으로 분류해요.
        </p>
      ) : (
        <ul className="space-y-2">
          {visibleTags.map((tag: CampaignTag) => (
            <li key={tag.id} className="rounded-xl border border-border bg-white p-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="flex items-center gap-2 text-sm font-bold text-foreground">
                    {tag.name}
                    {!tag.is_active && (
                      <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] font-semibold text-muted">
                        비활성
                      </span>
                    )}
                  </p>
                  <p className="mt-1 text-xs text-muted">{tag.definition}</p>
                </div>
                {isAdmin && (
                  <div className="flex shrink-0 gap-1.5">
                    <button
                      type="button"
                      onClick={() => openEditForm(tag)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-foreground hover:border-brand hover:text-brand-dark"
                    >
                      수정
                    </button>
                    {tag.is_active && (
                      <button
                        type="button"
                        onClick={() => handleDeactivate(tag)}
                        className="rounded-full border border-border px-3 py-1.5 text-xs font-semibold text-status-inactive hover:border-status-inactive"
                      >
                        비활성화
                      </button>
                    )}
                  </div>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

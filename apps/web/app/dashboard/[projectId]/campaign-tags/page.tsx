"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { api } from "@/lib/api";
import type { CampaignTag } from "@/lib/types";
import { useProjectContext } from "@/lib/project-context";
import { useAuth } from "@/lib/auth-context";

// §10 — 캠페인 태그 관리. 최초 생성자만 정의를 아는 구조를 금지한다: 이름/정의를 항상 목록에서
// 확인할 수 있고, 누구나(Viewer 포함) 조회할 수 있다. 생성/수정/삭제/재분류만 Admin 전용.

type EditingState = { id: string | null; name: string; definition: string };

const EMPTY_FORM: EditingState = { id: null, name: "", definition: "" };

export default function CampaignTagsPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const { isAdmin } = useAuth();
  const { campaignTags, refreshCampaignTags } = useProjectContext();

  const [includeInactive, setIncludeInactive] = useState(false);
  const [form, setForm] = useState<EditingState | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 정의가 바뀌거나 새 태그가 생겼을 때 "다시 분류할까요?" 배너를 보여준다.
  const [showReclassifyBanner, setShowReclassifyBanner] = useState(false);
  const [includeUserAssigned, setIncludeUserAssigned] = useState(false);
  const [reclassifying, setReclassifying] = useState(false);
  const [reclassifyResult, setReclassifyResult] = useState<number | null>(null);

  const visibleTags = includeInactive ? campaignTags : campaignTags.filter((t: CampaignTag) => t.is_active);

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
      setShowReclassifyBanner(true);
      setReclassifyResult(null);
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
  };

  const handleReclassifyAll = async () => {
    setReclassifying(true);
    try {
      const result = await api.reclassifyCampaignTags(projectId, includeUserAssigned);
      setReclassifyResult(result.reset_count);
    } catch (e) {
      setError(String(e));
    } finally {
      setReclassifying(false);
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

      {showReclassifyBanner && (
        <div className="rounded-xl border border-brand/30 bg-brand-cream p-4 text-sm text-brand-dark">
          <p className="font-semibold">분류 기준이 변경되었습니다. 기존 광고도 새로운 기준으로 다시 분류할까요?</p>
          {reclassifyResult === null ? (
            <>
              {isAdmin && (
                <label className="mt-2 flex items-center gap-1.5 text-xs">
                  <input
                    type="checkbox"
                    checked={includeUserAssigned}
                    onChange={(e) => setIncludeUserAssigned(e.target.checked)}
                  />
                  사용자가 직접 지정한 소재도 재분류 대상에 포함
                </label>
              )}
              <div className="mt-3 flex gap-2">
                {isAdmin && (
                  <button
                    type="button"
                    onClick={handleReclassifyAll}
                    disabled={reclassifying}
                    className="rounded-full bg-brand px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
                  >
                    {reclassifying ? "처리 중..." : "전체 재분류"}
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => setShowReclassifyBanner(false)}
                  className="rounded-full border border-border bg-white px-4 py-2 text-xs font-semibold text-foreground"
                >
                  앞으로 수집되는 광고부터 적용
                </button>
              </div>
            </>
          ) : (
            <p className="mt-2 text-xs">
              {reclassifyResult}개 소재를 재분류 대상으로 표시했어요. 재분류 처리 중에는 다시 분류될
              때까지 임시로 미분류로 표시될 수 있어요.
            </p>
          )}
        </div>
      )}

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

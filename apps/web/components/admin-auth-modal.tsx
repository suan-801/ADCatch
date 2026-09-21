"use client";

import { useState } from "react";
import { Modal } from "@/components/ui/modal";
import { useAuth } from "@/lib/auth-context";

// Viewer/Admin 권한 §4: 사이트 최초 접속 상태는 Viewer — 이 Modal로 관리자 비밀번호를 입력해야
// Admin 기능(생성/삭제/수집 실행)이 열린다. 비밀번호 값은 이 컴포넌트의 로컬 state를 벗어나지
// 않는다 — 세션은 서버가 발급한 HttpOnly 쿠키로만 유지된다(useAuth().loginAdmin 참고).
export function AdminAuthModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { loginAdmin } = useAuth();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const handleClose = () => {
    if (submitting) return;
    setPassword("");
    setError(null);
    onClose();
  };

  const handleSubmit = async () => {
    if (!password.trim() || submitting) return;
    setSubmitting(true);
    const result = await loginAdmin(password);
    setSubmitting(false);
    setPassword("");
    if (result.ok) {
      setError(null);
      onClose();
    } else {
      setError(result.error);
    }
  };

  return (
    <Modal open={open} onClose={handleClose} title="관리자 모드">
      <div>
        <label className="text-xs font-semibold text-muted">관리자 비밀번호</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoFocus
          disabled={submitting}
          onKeyDown={(e) => e.key === "Enter" && handleSubmit()}
          className="mt-1.5 w-full rounded-lg border border-border px-3 py-2.5 text-sm focus:border-brand focus:outline-none disabled:opacity-60"
        />
        {error && <p className="mt-2 text-xs font-medium text-status-inactive">{error}</p>}

        <button
          type="button"
          onClick={handleSubmit}
          disabled={!password.trim() || submitting}
          className="mt-4 w-full rounded-full bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
        >
          {submitting ? "확인 중..." : "관리자 권한 활성화"}
        </button>

        <p className="mt-3 text-center text-[11px] text-muted/60">*생성 권한은 개발자에게 문의 부탁드립니다</p>
      </div>
    </Modal>
  );
}

"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { AdminAuthModal } from "@/components/admin-auth-modal";

// Viewer/Admin 권한 §5: Viewer는 자물쇠 아이콘으로 관리자 모드에 진입하고, Admin 인증 후에는
// 상태 배지 + "관리자 모드 종료"가 대신 보인다. `floating`이면 헤더가 없는 화면(랜딩)에서
// 화면 우상단에 떠 있는 작은 버튼으로 렌더링한다 — 기존 레이아웃 구조는 건드리지 않는다.
export function AdminModeControl({ floating = false }: { floating?: boolean }) {
  const { isAdmin, loading, logoutAdmin } = useAuth();
  const [modalOpen, setModalOpen] = useState(false);

  if (loading) return null;

  const wrapperClass = floating ? "fixed right-4 top-4 z-40" : "";

  if (isAdmin) {
    return (
      <div className={`flex items-center gap-2 ${wrapperClass}`}>
        <span className="flex items-center gap-1 rounded-full border border-border bg-white px-2.5 py-1 text-[11px] font-semibold text-status-active shadow-sm">
          🔓 Admin
        </span>
        <button
          type="button"
          onClick={logoutAdmin}
          className="rounded-full border border-border bg-white px-2.5 py-1 text-[11px] font-semibold text-muted shadow-sm hover:border-brand/40 hover:text-foreground"
        >
          관리자 모드 종료
        </button>
      </div>
    );
  }

  return (
    <div className={wrapperClass}>
      <button
        type="button"
        onClick={() => setModalOpen(true)}
        aria-label="관리자 모드"
        title="관리자 모드"
        className="flex h-8 w-8 items-center justify-center rounded-full border border-border bg-white text-sm text-muted shadow-sm hover:border-brand/40 hover:text-foreground"
      >
        🔒
      </button>
      <AdminAuthModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </div>
  );
}

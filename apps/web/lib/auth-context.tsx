"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";

// Viewer/Admin 권한: 사이트 기본 방문자는 Viewer(읽기 전용)이고, 관리자 비밀번호 인증에
// 성공한 브라우저만 Admin 기능(생성/삭제/수집 실행 등)을 쓸 수 있다. 세션은 서버가 발급한
// HttpOnly 쿠키로 유지되므로 여기서는 "지금 Admin인가"라는 boolean 상태만 들고 있으면 된다 —
// 비밀번호 자체는 React state 밖으로 절대 나가지 않는다(localStorage 등에 저장 금지).
interface AuthContextValue {
  isAdmin: boolean;
  loading: boolean;
  checkAuth: () => Promise<void>;
  loginAdmin: (password: string) => Promise<{ ok: true } | { ok: false; error: string }>;
  logoutAdmin: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  const checkAuth = useCallback(async () => {
    try {
      const status = await api.adminStatus();
      setIsAdmin(status.is_admin);
    } catch {
      setIsAdmin(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // 보호된 API가 401을 반환하면(세션 만료 등) lib/api.ts가 이 이벤트를 쏜다 —
  // Admin 상태를 즉시 내려서 관리 버튼들이 숨고 자물쇠 아이콘이 다시 보이게 한다.
  useEffect(() => {
    const onUnauthorized = () => setIsAdmin(false);
    window.addEventListener("adcatcher:admin-unauthorized", onUnauthorized);
    return () => window.removeEventListener("adcatcher:admin-unauthorized", onUnauthorized);
  }, []);

  const loginAdmin = useCallback(async (password: string) => {
    try {
      const result = await api.adminLogin(password);
      setIsAdmin(result.is_admin);
      return { ok: true as const };
    } catch (e) {
      const message =
        e instanceof ApiError && e.status === 429
          ? "로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요."
          : "비밀번호가 올바르지 않습니다.";
      return { ok: false as const, error: message };
    }
  }, []);

  const logoutAdmin = useCallback(async () => {
    try {
      await api.adminLogout();
    } finally {
      setIsAdmin(false);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ isAdmin, loading, checkAuth, loginAdmin, logoutAdmin }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

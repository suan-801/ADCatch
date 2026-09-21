import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth-context";

export const metadata: Metadata = {
  title: "ADCatcher — 매일 바뀌는 경쟁사 광고를 CATCH!",
  description: "경쟁사의 Meta Ad Library 라이브 소재를 매일 자동 수집해 신규/종료 감지, 생존 기간, 비주얼 패턴을 분석합니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen antialiased">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}

import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AdCatch — 경쟁사 메타 소재 트래커",
  description: "경쟁사의 Meta Ad Library 라이브 소재를 매일 자동 수집해 신규/종료 감지, 생존 기간, 비주얼 패턴을 분석합니다.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}

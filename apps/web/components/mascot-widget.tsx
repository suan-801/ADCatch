"use client";

import { useState } from "react";

// PRD.MD 5.2 픽셀 도트 비서 캐릭터("캐쳐") — 제품 화면에서는 우측 하단 상주, image-rendering: pixelated.
// 랜딩 Hero의 3D 렌더 캐쳐(catcher-hero.png)와는 의도적으로 다른 스타일: 브랜드 주인공(랜딩) vs
// 작은 UX 가이드(제품)라는 역할 차이를 시각적으로도 구분한다.
//
// 순수 표시 컴포넌트로 유지한다 — 어떤 메시지를 보여줄지는 호출부(현재 현황 페이지 / 날짜별
// 변화 페이지)가 각자의 맥락에 맞게 결정한다 (브리핑 §29: 두 화면의 멘트가 서로 달라야 함).
export function MascotWidget({ message, happy = false }: { message: string; happy?: boolean }) {
  const [open, setOpen] = useState(true);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {open && (
        <div className="max-w-[220px] rounded-xl border border-border bg-white p-3 text-xs text-foreground shadow-lg">
          {message}
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="캐쳐 비서 토글"
        className="h-16 w-16 rounded-full border border-border bg-white p-1.5 shadow-lg transition-transform hover:scale-105"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={happy ? "/mascot/Catcher_happy.png" : "/mascot/Catcher.png"}
          alt="캐쳐"
          className="pixelated h-full w-full object-contain"
        />
      </button>
    </div>
  );
}

"use client";

import { useEffect, useRef, useState } from "react";

// PRD.MD 5.2 픽셀 도트 비서 캐릭터("캐쳐") — 제품 화면에서는 우측 하단 상주, image-rendering: pixelated.
// 랜딩 Hero의 3D 렌더 캐쳐(catcher-hero.webp)와는 의도적으로 다른 스타일: 브랜드 주인공(랜딩) vs
// 작은 UX 가이드(제품)라는 역할 차이를 시각적으로도 구분한다.
//
// 순수 표시 컴포넌트로 유지한다 — 어떤 메시지를 보여줄지는 호출부(현재 현황 페이지 / 날짜별
// 변화 페이지)가 각자의 맥락에 맞게 결정한다 (브리핑 §29: 두 화면의 멘트가 서로 달라야 함).
//
// P1-03: 챗봇처럼 매번 자동으로 말풍선을 열지 않는다 — 기본은 닫힘. 호출부가 "의미 있는 순간"
// (온보딩, baseline 완료, 신규 변화 감지, 수집 완료/실패 등)에만 openSignal 값을 바꿔서 그 순간에만
// 말풍선이 열리도록 한다. openSignal이 없으면(undefined) 자동으로 열리지 않는다 — 사용자가 직접
// 토글한 열림/닫힘 상태를 그대로 존중한다.
export function MascotWidget({
  message,
  happy = false,
  openSignal,
}: {
  message: string;
  happy?: boolean;
  openSignal?: string | number;
}) {
  const [open, setOpen] = useState(false);
  const prevSignal = useRef<string | number | undefined>(undefined);

  useEffect(() => {
    if (openSignal !== undefined && openSignal !== prevSignal.current) {
      setOpen(true);
    }
    prevSignal.current = openSignal;
  }, [openSignal]);

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {open && (
        <div className="max-w-[240px] rounded-xl border border-border bg-white p-3 text-xs text-foreground shadow-lg">
          {message}
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="캐쳐 비서 토글"
        // I-02/I-03: 64x64 → 데스크톱 80~88px/모바일 64~72px로 키우고, 은은한 오렌지 링 +
        // 진한 그림자로 주목도를 올린다. openSignal이 바뀔 때만(=의미 있는 순간) key가 바뀌어
        // pop-in이 다시 재생된다 — 항상 움직이는 캐릭터로 만들지 않는다(I-03).
        className="h-[70px] w-[70px] shrink-0 rounded-full border border-border bg-white p-2 shadow-xl ring-4 ring-brand/15 transition-transform hover:scale-105 sm:h-[84px] sm:w-[84px]"
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          key={String(openSignal ?? "")}
          src={happy ? "/mascot/catcher-happy.png" : "/mascot/catcher.png"}
          alt="캐쳐"
          className="pixelated h-full w-full object-contain motion-safe:animate-pop-in"
        />
      </button>
    </div>
  );
}

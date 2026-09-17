"use client";

import { useState } from "react";

// PRD.MD 5.2 픽셀 도트 비서 캐릭터("캐쳐") — 우측 하단 상주, image-rendering: pixelated,
// 말풍선 툴팁으로 온보딩·수집 상태·당일 결과 요약 전달.
// 마스코트 이미지: apps/web/public/mascot/{Catcher,Catcher_happy}.png (원본 에셋 그대로 사용).
// 등장/말풍선 연출은 docs/mascot-style-reference.jpg 의 캐릭터 등장 방식만 참고 — 그 파일의
// 전체 UI 톤(오렌지 랜딩페이지)은 AdCatch 디자인과 무관하므로 따르지 않는다.
export function MascotWidget({ newCount }: { newCount: number }) {
  const [open, setOpen] = useState(true);
  const happy = newCount > 0;
  const message = happy
    ? `오늘 신규 소재 ${newCount}건을 발견했어요!`
    : "오늘은 새 소재가 없어요. 경쟁사를 더 등록해볼까요?";

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2">
      {open && (
        <div className="max-w-[220px] rounded border border-border bg-white p-3 text-xs text-foreground shadow-md">
          {message}
        </div>
      )}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="캐쳐 비서 토글"
        className="h-16 w-16 rounded-full border border-border bg-white p-1 shadow-md"
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

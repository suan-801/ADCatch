"use client";

import { useEffect, useRef, useState } from "react";

// "경쟁사 소재는 매일 다른 비주얼로 바뀌고, ADCatcher는 그 변화를 지켜본다"는 개념을
// 고전 명화를 ADCatcher Catcher로 재해석한 3장의 "전시 작품"으로 유머러스하게 표현한다.
// 실제 광고 이미지는 쓰지 않는다 — 세 작품 자체가 "오늘은 이 소재, 내일은 다른 소재"의 metaphor.
// 카피는 기존 그대로 — 이번 변경은 시각 구성(작품 갤러리)만 교체한다.
//
// 이전엔 시간 기반(9초 주기) 앰비언트 loop로 "NEW" 배지를 깜빡였는데, 스크롤 속도에 비해
// 너무 느려서 사용자가 알아차리기 힘들다는 피드백을 받았다. 그래서 배경에서 조용히 도는
// 애니메이션 대신, 섹션이 뷰포트에 들어오는 "그 순간" 세 작품이 가운데에서 확대되며
// 튀어나오는 1회성 reveal로 바꿨다 — 스크롤 타이밍과 항상 일치하므로 놓칠 수 없다.
type Artwork = { src: string; alt: string; caption: string };

const ARTWORKS: Artwork[] = [
  { src: "/landing/gallery/catcher-monalisa.webp", alt: "모나리자로 재해석된 캐쳐", caption: "MONA" },
  { src: "/landing/gallery/catcher-pearl.webp", alt: "진주 귀걸이를 한 소녀로 재해석된 캐쳐", caption: "PEARL" },
  { src: "/landing/gallery/catcher-vangogh.webp", alt: "반 고흐로 재해석된 캐쳐", caption: "VAN GOGH" },
];

function useRevealOnScroll() {
  const ref = useRef<HTMLDivElement>(null);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    // reduced-motion에서는 애니메이션 없이 바로 최종 상태로 보여준다.
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setRevealed(true);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setRevealed(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  return { ref, revealed };
}

// Frame 자체(테두리/그림자/badge/caption)는 desktop·mobile 어디서나 동일하다 — 바깥
// wrapper(positioning)만 호출부가 다르게 감싼다. revealed=false일 때는 중앙으로 수축된
// 채 투명하게 숨어있다가, true가 되는 순간 실제 크기/위치로 "튀어나온다".
function ArtworkFrame({
  artwork,
  revealed,
  delayMs,
  showBadge,
  priority,
}: {
  artwork: Artwork;
  revealed: boolean;
  delayMs: number;
  showBadge?: boolean;
  priority?: boolean;
}) {
  return (
    <div className="flex flex-col items-center">
      <div
        className="relative w-full overflow-visible rounded-3xl border-[1.5px] border-[#EADFCF] bg-white p-2.5 shadow-lg transition-[transform,opacity] duration-500 ease-[cubic-bezier(0.22,1.4,0.36,1)] sm:p-3"
        style={{
          transitionDelay: `${delayMs}ms`,
          transform: revealed ? "scale(1) translateY(0)" : "scale(0.25) translateY(12px)",
          opacity: revealed ? 1 : 0,
        }}
      >
        {showBadge && (
          <span
            className="absolute -right-1.5 -top-1.5 z-10 flex items-center gap-1 rounded-full bg-white px-2 py-0.5 text-[9px] font-extrabold text-brand-dark shadow-md transition-opacity duration-300"
            style={{ transitionDelay: `${delayMs + 400}ms`, opacity: revealed ? 1 : 0 }}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-brand" />
            NEW
          </span>
        )}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={artwork.src}
          alt={artwork.alt}
          loading={priority ? "eager" : "lazy"}
          className="aspect-square w-full rounded-2xl object-contain"
        />
      </div>
      <p
        className="mt-2 text-[10px] font-bold uppercase tracking-[0.2em] text-muted transition-opacity duration-300"
        style={{ transitionDelay: `${delayMs + 200}ms`, opacity: revealed ? 1 : 0 }}
      >
        {artwork.caption}
      </p>
    </div>
  );
}

export function WhatItDoesSection() {
  const [mona, pearl, vangogh] = ARTWORKS;
  const { ref, revealed } = useRevealOnScroll();

  return (
    <section className="bg-white px-6 py-24 sm:py-32">
      <div className="mx-auto flex max-w-4xl flex-col items-center text-center">
        <h2 className="text-3xl font-extrabold leading-tight text-foreground [word-break:keep-all] sm:text-5xl">
          경쟁사 광고는
          <br />
          오늘도 조용히 바뀌고 있어요
        </h2>
        <p className="mt-4 max-w-md text-sm text-muted sm:text-base">
          <span className="block">새로 투입되는 소재, 조용히 사라지는 소재.</span>
          <span className="block">ADCatcher가 매일 그 변화를 대신 지켜보고 캐치해드려요.</span>
        </p>

        <div ref={ref}>
          {/* Desktop: 비대칭 갤러리 구성 — 왼쪽 큰 모나리자 + 오른쪽에 진주/반고흐를 서로 다른
              높이로 쌓는다. flex 기반이라 캡션끼리 겹칠 걱정 없이 "약간의 variation"만 준다. */}
          <div className="mt-20 hidden w-full max-w-2xl items-center justify-center gap-10 sm:flex">
            <div className="w-[40%]">
              <ArtworkFrame artwork={mona} revealed={revealed} delayMs={0} showBadge priority />
            </div>
            <div className="flex w-[27%] flex-col gap-10 pt-14">
              <div className="self-end">
                <ArtworkFrame artwork={pearl} revealed={revealed} delayMs={120} />
              </div>
              <div className="w-[85%] self-start">
                <ArtworkFrame artwork={vangogh} revealed={revealed} delayMs={240} />
              </div>
            </div>
          </div>

          {/* Mobile: 메인 작품 → 보조 작품 2개 순서로 stack. */}
          <div className="mt-16 flex w-full flex-col items-center gap-8 sm:hidden">
            <div className="w-[86vw] max-w-xs">
              <ArtworkFrame artwork={mona} revealed={revealed} delayMs={0} showBadge priority />
            </div>
            <div className="flex w-full max-w-xs justify-center gap-5">
              <div className="w-[38vw] max-w-[160px]">
                <ArtworkFrame artwork={pearl} revealed={revealed} delayMs={120} />
              </div>
              <div className="w-[38vw] max-w-[160px]">
                <ArtworkFrame artwork={vangogh} revealed={revealed} delayMs={240} />
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

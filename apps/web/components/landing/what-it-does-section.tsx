// 실제 경쟁사 광고 이미지 대신, "광고가 계속 바뀐다"는 개념을 추상 그래픽으로 표현한다
// (Section 02 — 브리핑 4장: 실제 경쟁사 소재 이미지를 노출하지 않는다).
const TILES = [
  { color: "#FFD9C2", delay: "0s" },
  { color: "#FFB088", delay: "0.4s" },
  { color: "#1A1A1A", delay: "0.8s" },
  { color: "#FF8A42", delay: "0.2s" },
  { color: "#EEE7E0", delay: "1.1s" },
  { color: "#FF6B1A", delay: "0.6s" },
  { color: "#FFD9C2", delay: "1.4s" },
  { color: "#EA580C", delay: "1.0s" },
];

export function WhatItDoesSection() {
  return (
    <section className="bg-white px-6 py-24 sm:py-32">
      <div className="mx-auto flex max-w-3xl flex-col items-center text-center">
        <h2 className="text-3xl font-extrabold leading-tight text-foreground sm:text-5xl">
          경쟁사 광고는
          <br />
          오늘도 조용히 바뀌고 있어요
        </h2>
        <p className="mt-4 max-w-md text-sm text-muted sm:text-base">
          새로 투입되는 소재, 조용히 사라지는 소재. ADCather가 매일 그 변화를 대신 지켜보고 캐치해드려요.
        </p>

        <div className="relative mt-16 grid w-full max-w-lg grid-cols-4 gap-3 sm:gap-4">
          {TILES.map((tile, i) => (
            <div
              key={i}
              className="aspect-[3/4] animate-pulse-fade rounded-xl"
              style={{ backgroundColor: tile.color, animationDelay: tile.delay }}
            />
          ))}

          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src="/mascot/catcher-hero.png"
            alt="캐쳐가 광고를 캐치하는 모습"
            className="absolute -bottom-10 -right-8 w-28 rotate-6 drop-shadow-xl sm:w-36"
          />
        </div>
      </div>
    </section>
  );
}

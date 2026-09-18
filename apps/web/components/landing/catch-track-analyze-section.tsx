// 텍스트(tag/title/copy)는 기존 카피를 그대로 유지 — 이번 변경은 각 단계의 visual scene만 교체한다.
const STEPS = [
  {
    tag: "CATCH",
    title: "새로운 광고를 발견",
    copy: "경쟁사가 새로 집행한 소재를 매일 자동으로 찾아냅니다.",
    Graphic: CatchGraphic,
  },
  {
    tag: "TRACK",
    title: "얼마나 오래 살아남는지 확인",
    copy: "광고가 처음 발견된 날부터 사라질 때까지, 생존 기간을 계속 추적합니다.",
    Graphic: TrackGraphic,
  },
  {
    tag: "ANALYZE",
    title: "어떤 비주얼이 반복되는지 확인",
    copy: "인물·제품·텍스트·그래픽 — 오래 살아남는 소재의 비주얼 패턴을 분석합니다.",
    Graphic: AnalyzeGraphic,
  },
];

export function CatchTrackAnalyzeSection() {
  return (
    <section className="relative overflow-hidden bg-brand-cream px-6 py-24 sm:py-32">
      <div className="pointer-events-none absolute -left-32 top-10 h-80 w-80 rounded-full bg-brand/10 blur-3xl" />
      <div className="pointer-events-none absolute -right-24 bottom-10 h-96 w-96 rounded-full bg-brand/10 blur-3xl" />

      <div className="relative mx-auto flex max-w-5xl flex-col gap-24 sm:gap-32">
        {STEPS.map(({ tag, title, copy, Graphic }, i) => (
          <div
            key={tag}
            className={`flex flex-col items-center gap-10 sm:gap-16 ${i % 2 === 1 ? "sm:flex-row-reverse" : "sm:flex-row"}`}
          >
            <div className="text-center sm:flex-1 sm:text-left">
              <p className="text-xs font-extrabold tracking-[0.2em] text-brand-dark">{tag}</p>
              <h3 className="mt-3 text-3xl font-extrabold leading-tight text-foreground sm:text-5xl">{title}</h3>
              <p className="mt-4 max-w-sm text-sm text-muted sm:text-base sm:mx-0 mx-auto">{copy}</p>
            </div>
            <div className="w-full sm:flex-1">
              <Graphic />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

// ── CATCH: 떠다니는 추상 광고 카드 + NEW 배지 + 캐쳐가 캐치하는 순간 ──────────
function CatchGraphic() {
  return (
    <div className="relative mx-auto aspect-square w-full max-w-sm">
      <div className="absolute left-4 top-4 w-20 -rotate-[10deg] rounded-xl bg-[#1A1A1A] p-2 shadow-xl motion-safe:animate-float">
        <div className="h-24 w-full rounded-lg bg-white/10" />
      </div>

      <div
        className="absolute right-0 top-0 w-16 rotate-[8deg] rounded-xl bg-brand-light p-2 shadow-xl motion-safe:animate-float"
        style={{ animationDelay: "0.6s" }}
      >
        <div className="h-20 w-full rounded-lg bg-white/20" />
        <span className="absolute -right-2 -top-2 rounded-full bg-white px-2 py-0.5 text-[9px] font-extrabold text-brand-dark shadow-md">
          NEW
        </span>
      </div>

      <div
        className="absolute bottom-12 left-0 w-14 rotate-[6deg] rounded-xl bg-white p-2 shadow-xl motion-safe:animate-float"
        style={{ animationDelay: "1.1s" }}
      >
        <div className="h-16 w-full rounded-lg bg-slate-100" />
      </div>

      <span
        className="absolute right-12 top-20 h-2.5 w-2.5 rotate-45 bg-brand motion-safe:animate-pulse-fade"
        style={{ animationDelay: "0.3s" }}
      />
      <span
        className="absolute bottom-28 left-10 h-2 w-2 rotate-45 bg-brand-dark motion-safe:animate-pulse-fade"
        style={{ animationDelay: "1s" }}
      />

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/mascot/catcher-hero.png"
        alt="캐쳐가 새로운 광고를 캐치하는 모습"
        className="absolute bottom-0 left-1/2 w-48 -translate-x-1/2 -rotate-[4deg] drop-shadow-2xl sm:w-56"
      />
    </div>
  );
}

// ── TRACK: 광고 카드 + 생존일수 타임라인(글로시 트랙 + 진행 인디케이터) ──────
function TrackGraphic() {
  return (
    <div className="relative mx-auto flex w-full max-w-sm flex-col items-center">
      <div className="w-28 -rotate-3 rounded-2xl bg-foreground p-3 shadow-xl">
        <div className="flex items-center justify-between">
          <span className="h-2 w-2 rounded-full bg-status-active" />
          <span className="text-[9px] font-bold tracking-wide text-white/60">AD</span>
        </div>
        <div className="mt-2 h-20 w-full rounded-lg bg-white/10" />
      </div>

      <div className="mt-12 flex w-full items-center gap-3">
        <span className="shrink-0 text-xs font-bold text-muted">DAY 01</span>
        <div className="relative h-2.5 flex-1 rounded-full bg-white shadow-inner">
          <div
            className="relative h-full rounded-full bg-gradient-to-r from-brand-light to-brand motion-safe:animate-track-fill"
            style={{ width: "68%" }}
          >
            <span className="absolute right-0 top-1/2 h-4 w-4 -translate-y-1/2 translate-x-1/2 rounded-full bg-white shadow-[0_0_0_4px_rgba(255,107,26,0.22)]" />
          </div>
        </div>
        <span className="shrink-0 text-xs font-bold text-brand-dark">DAY 24</span>
      </div>
    </div>
  );
}

// ── ANALYZE: 중앙 광고 카드에서 비주얼 태그가 사방으로 분리되는 클러스터 ─────
const TAGS = [
  { label: "인물", color: "#2a78d6", area: "col-start-2 row-start-1", delay: "0s" },
  { label: "제품", color: "#eb6834", area: "col-start-3 row-start-2", delay: "0.4s" },
  { label: "텍스트", color: "#1baf7a", area: "col-start-2 row-start-3", delay: "0.8s" },
  { label: "그래픽", color: "#eda100", area: "col-start-1 row-start-2", delay: "1.2s" },
];

function AnalyzeGraphic() {
  return (
    <div className="relative mx-auto grid w-full max-w-sm grid-cols-3 grid-rows-3 items-center justify-items-center gap-3 sm:gap-4">
      {TAGS.map(({ label, color, area, delay }) => (
        <span
          key={label}
          className={`${area} motion-safe:animate-tag-pulse rounded-full px-3 py-1.5 text-[11px] font-bold text-white shadow-md`}
          style={{ backgroundColor: color, animationDelay: delay }}
        >
          {label}
        </span>
      ))}

      <div className="col-start-2 row-start-2 flex aspect-square w-20 items-center justify-center rounded-2xl bg-foreground shadow-xl sm:w-24">
        <span className="text-[10px] font-extrabold tracking-wide text-white">AD</span>
      </div>
    </div>
  );
}

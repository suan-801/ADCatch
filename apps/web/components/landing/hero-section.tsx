export function HeroSection() {
  return (
    <section className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-brand px-6 text-center">
      <div className="pointer-events-none absolute inset-0 opacity-[0.07]">
        <div className="absolute -left-24 -top-24 h-96 w-96 rounded-full bg-white blur-3xl" />
        <div className="absolute -bottom-24 -right-24 h-96 w-96 rounded-full bg-white blur-3xl" />
      </div>

      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src="/mascot/catcher-hero.png"
        alt="캐쳐"
        className="relative z-10 w-56 animate-float drop-shadow-2xl sm:w-72 md:w-80"
      />

      <h1 className="relative z-10 mt-4 text-4xl font-extrabold leading-[1.15] text-white sm:text-6xl md:text-7xl">
        매일 바뀌는
        <br />
        경쟁사 광고를
        <br />
        <span className="inline-block rounded-2xl bg-white px-4 py-1 text-brand-dark">CATCH!</span>
      </h1>

      <p className="relative z-10 mt-6 max-w-md text-sm text-white/90 sm:text-base">
        Meta Ad Library 라이브 소재를 매일 자동 수집해, 신규/종료 감지와 생존 기간을 한눈에 보여드려요.
      </p>

      <a
        href="#project-select"
        className="relative z-10 mt-8 rounded-full bg-white px-8 py-3.5 text-sm font-bold text-brand-dark shadow-lg transition-transform hover:scale-105"
      >
        시작하기
      </a>
    </section>
  );
}

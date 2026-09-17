# Layout Toolkit — 섹션 옵션 풀 + CSS 패턴 + 디자인 품질 룰

> ref/landing-page-builder/SKILL.md § Layout Toolkit · Reusable CSS Techniques · Design Quality Rules · What to Avoid 의 한국어판.
> SKILL Step 1.5 (시나리오 도출) 와 Step 3 (HTML 빌드) 에서 본 파일을 1순위 인용.

---

## 1. 섹션 옵션 풀 (페이지 타입별 골격에서 선택)

각 섹션은 옵션이 여러 개다. **콘텐츠에 맞는 1개만** 선택. 가장 복잡한 옵션이 아니라, 메시지에 가장 적합한 옵션을 고를 것.

### 1-1. Hero (필수, 1개)

| 옵션 | 언제 쓰나 | 핵심 CSS |
|---|---|---|
| **Full-bleed image hero** | 비주얼 캠페인·체험단 무드 강조 | `min-height: 100vh` + 배경 풀블리드 + 멀티 그라데이션 scrim + `align-items: flex-end` 좌하단 정렬 |
| **Split-screen hero** | 제품 런칭·이벤트 — 비주얼과 카피가 동일 가중치 | `grid-template-columns: 1fr 1fr` (이미지 50~60% / 텍스트 40~50%) |
| **Text-forward hero** | 공지·세일·브랜드 스토리 — 카피가 주인공 | 거대한 헤드라인 (`clamp(56px, 9vw, 120px)`) + 브랜드 컬러 배경 + 하단 이미지 스트립 |
| **Video/motion hero** | 브랜드·멤버십 LP | 정적 이미지 대신 CSS 애니메이션 (그라데이션 시프트·요소 floating) |

### 1-2. Value Props / 혜택 (선택)

| 옵션 | 언제 |
|---|---|
| **Overlapping cards** | 세일·이벤트 — 혜택이 주된 후킹. 카드가 hero 를 negative `margin-top` + `z-index: 3` 으로 덮음. 카드별 다른 그라데이션 top-border |
| **Icon-led columns** | 체험단 혜택·기능 리스트 — 사이드 컬럼에 SVG 아이콘/큰 숫자 |
| **Bento grid** | 혜택의 가중치가 불균등 (메인 혜택 1 + 보조 N). CSS Grid `grid-row`·`grid-column` 변화 |
| **Horizontal scroll strip** | 모바일 퍼스트·다수 혜택. `display: flex; overflow-x: auto; scroll-snap-type: x mandatory` |

### 1-3. Visual Showcase / 디테일 (선택)

| 옵션 | 언제 |
|---|---|
| **Magazine grid** | 다목적 쇼케이스. 비대칭 `1.15fr 0.85fr` + 1개 카드가 2행 span. 이미지 hover zoom |
| **Full-bleed interstitial** | 스토리텔링·딥다이브. 텍스트 섹션 사이에 풀블리드 이미지 |
| **Alternating left/right** | 단계별 내러티브·비포애프터. 섹션마다 이미지↔텍스트 좌우 교대 |
| **Stacked cards with peek** | 단계별 공개. `position: sticky` 로 스크롤 시 다음 카드가 슬쩍 |

### 1-4. Stats / Proof (선택)

| 옵션 | 언제 |
|---|---|
| **Dark strip** | 두 라이트 섹션 사이 break. 풀폭 브랜드 컬러 + 통계 그리드 + `::after` 디바이더 + 라디얼 그라데이션 |
| **Inline stat callouts** | 에디토리얼 톤. 본문 안에 큰 숫자를 pull-quote 처럼 floating |
| **Stat cards row** | 사회증거가 주요 섹션. value-prop 카드 스타일과 매칭 |

### 1-5. Testimonial (선택)

| 옵션 | 언제 |
|---|---|
| **Staggered cards** | 3개 후기·길이 다양. 카드별 `margin-top` 어긋남 + 거대 따옴표 데코 |
| **Featured quote** | 1개 후기가 압도적. 풀폭 blockquote + 양옆 작은 후기 |
| **Carousel** | 4개 이상·모바일 퍼스트. 가로 스크롤 + 네비 도트 |
| **Integrated with imagery** | 후기가 특정 제품·시나리오를 지칭. 이미지 위/옆 오버레이 |

### 1-6. How-it-works / 진행 방법 (체험단·이벤트 권장)

| 옵션 | 언제 |
|---|---|
| **Timeline** | 3~5단계 선형 프로세스. `::before` 그라데이션 연결선 + 번호 원 (각 도트 다른 브랜드 컬러) |
| **Numbered vertical stack** | 단계 콘텐츠가 풍부. 큰 번호 좌측 + 단계 콘텐츠 우측 + 넉넉한 화이트 스페이스 |
| **Icon grid** | 단순 4단계 이내. 2x2 또는 1x4 그리드 + 커스텀 SVG 아이콘 |

### 1-7. Final CTA (필수, 1개)

| 옵션 | 언제 |
|---|---|
| **Dark immersive** | 강력한 클로징·감정 풀. 브랜드 primary 배경 + 라디얼 그라데이션 레이어 + 유기적 SVG 데코 (지형선·식물 실루엣) ~4% opacity + padding 100-120px |
| **Image-backed** | 비주얼 캠페인. 두 번째 이미지 배경 + 그라데이션 scrim + 클로징 카피 |
| **Minimal** | 위 섹션이 이미 충분히 팔았을 때. 단일 헤드라인 + 1줄 카피 + CTA 버튼 |

> **신청·등록 CTA 처리**: `<a href="{사용자가 제공한 구글폼/Tally URL}" target="_blank" rel="noopener noreferrer">` 로만 마크업. `<form>` 마크업 ❌, JS 검증 ❌, action 빈칸 ❌.

---

## 2. Reusable CSS 패턴

### 2-1. Foundation

```css
:root {
  /* brand_brief.md § 4-1 6슬롯에서 동적 주입 */
  --bg-light:    #__;  /* BG-Light */
  --bg-deep:     #__;  /* BG-Deep */
  --brand-sig:   #__;  /* BRAND-Signature */
  --brand-sub:   #__;  /* BRAND-Sub */
  --text-primary:#__;  /* TEXT-Primary */
  --text-sub:    #__;  /* TEXT-Sub */

  --font-display: 'Noto Serif KR', serif;  /* brand_brief § 4-4 */
  --font-body:    'Pretendard', 'Noto Sans KR', sans-serif;

  --ease: cubic-bezier(0.16, 1, 0.3, 1);
  --radius: 14px;
}

/* Fluid typography — breakpoint 점프 대신 clamp() */
h1 { font-size: clamp(42px, 7vw, 80px); letter-spacing: -1.5px; }
h2 { font-size: clamp(28px, 4vw, 48px); letter-spacing: -1px; }
.label { font-size: 13px; letter-spacing: 2px; text-transform: uppercase; }
```

**Google Fonts import**: 본 OS 한국어 LP 디폴트 = `Pretendard` + `Noto Serif KR`. brand_brief § 4-4 에 다른 폰트 지정 있으면 우선.

### 2-2. 반응형 breakpoint

- `@media (max-width: 900px)` — 태블릿: 그리드를 단일 컬럼으로
- `@media (max-width: 600px)` — 모바일: CTA 세로 스택, 데코 요소 단순화
- 모바일 퍼스트, 터치 타겟 최소 44px

### 2-3. Motion & Interaction

- **Scroll reveal**: `.reveal { opacity: 0; transform: translateY(32px); transition: opacity .8s var(--ease), transform .8s var(--ease); }` → `IntersectionObserver` 로 `.is-visible` 추가
- **Card hover**: `transform: translateY(-6px)` + 확장된 shadow
- **Image hover zoom**: `overflow: hidden` 컨테이너 + 이미지 `transform: scale(1.04)` (transition 600ms)
- **Sticky nav**: 스크롤 시 `backdrop-filter: blur(12px)` + 배경 컬러 페이드 인

### 2-4. Depth & Texture

- **Gradient scrim**: `linear-gradient(180deg, rgba(0,0,0,0) 30%, rgba(0,0,0,0.55) 100%)` 이미지 위 오버레이 → 텍스트 가독성
- **Layered radial gradients**: 다크 섹션에 `radial-gradient` 2~3개 다른 위치 (flat ❌, 깊이감)
- **Section overlap**: `margin-top: -80px; z-index: 2; position: relative` 로 섹션이 위 섹션을 덮어 깊이 생성
- **Decorative `::before` / `::after`**: 그라데이션 보더, 액센트 라인, 그리드 디바이더

### 2-5. Typography & Layout

- **Letter-spacing**: 헤드라인 -1~-2px (타이트), 라벨 2~3px (와이드)
- **Weight mixing**: 한 섹션에 300 (서브) + 600 (라벨) + 700 (헤드) 섞기
- **Pill tags**: `border-radius: 100px` 라벨/배지
- **카드 라운드**: `border-radius: 12-16px` 통일
- **Gradient borders**: 카드별 `border-top` 또는 `border-left` 그라데이션 — 카드마다 다른 브랜드 컬러 조합

### 2-6. Image Integration

- `object-fit: cover` 항상 (고정 높이 컨테이너 안)
- 모바일에서 이미지는 cropped 또는 hidden gracefully
- 생성 이미지 톤 통일을 위해 미세한 `filter: saturate(0.95)` 또는 warm overlay

---

## 3. 이미지 슬롯 (NanoBanana 생성 가이드)

**히어로 16:9 (1장 필수)**
- 프롬프트 패턴: "Editorial K-beauty product photography of [구체 명사] on [배경 텍스처]. Soft diffused natural light, warm neutral tones. Shot in the style of Kinfolk magazine — calm, intimate, lived-in. Negative space at [상단/우측]. No text, no logos."
- aspect_ratio: `"16:9"`
- output_path: `08_landing/{토픽}/images/hero.png`

**콘텐츠 4:3 (1~3장 선택)**
- 프롬프트 패턴: "Close-up of [제품 사용 장면 / 라이프스타일 컷]. Shallow depth of field. Natural textures: ceramic, linen, aged wood. Warm late afternoon light. No people in direct focus, no branding visible."
- aspect_ratio: `"4:3"`
- output_path: `08_landing/{토픽}/images/content-{n}.png`

**제품·로고 등장 시**: `01_brand/products/`·`01_brand/logos/` 의 실재 PNG 를 reference image 로 첨부 (Method 1 conditioning). 재그리기 ❌, 위치·크기·라이팅 블렌드만 허용.

**Negative prompt 항상**: `"stock photography, oversaturated, neon colors, text overlays, logos, watermarks, posed people, generic, corporate, plastic surfaces"`

**Fallback** (NanoBanana 호출 불가 시): CSS 그라데이션 placeholder + `role="img" aria-label="..."` 추가 + 채팅에 "이미지 N장이 placeholder 입니다" 알림.

**수량 가이드**
- 단일 LP: 히어로 1 + 콘텐츠 1~2 = 2~3장
- 체험단: 히어로 1 + 콘텐츠 1 = 2장
- 이벤트: 히어로 1 + 콘텐츠 2~3 (혜택 비주얼) = 3~4장

---

## 4. 디자인 품질 룰 (절대 위반 ❌)

LP 가 "AI 가 만든 generic LP" 처럼 보이지 않으려면:

- ❌ 똑같은 3컬럼 카드 그리드가 페이지 전체 지배 패턴이 되는 것
- ❌ 센터 정렬 텍스트 + 그라데이션 오버레이 + 단일 CTA 의 "쿠키 커터" 히어로
- ❌ 모든 섹션이 흰색·회색 평면 배경에 변화 없음
- ❌ 데코 요소가 단순 원·사각형 (유기적 SVG 사용)
- ❌ 카드 스타일이 페이지 전체에 똑같이 반복
- ❌ 그림자만으로 깊이 표현 (그라데이션·overlap·텍스처 조합)
- ❌ Placeholder 처럼 보이는 이미지 영역 (단색 사각형)
- ❌ brand_brief § 4-1 슬롯 밖의 색 사용 (특히 § 4-2 사용 ❌ 컬러)

✅ **권장**:
- 비대칭 레이아웃, 겹치는 요소, off-grid 위치
- 풀블리드 ↔ contained 섹션 교대로 리듬 생성
- CSS Grid 활용 (flexbox row 만 ❌)
- 한 섹션 안에서도 카드 크기 변화
- 헤드라인은 거대하고 자신만만, 라벨은 정밀하고 작게 — 타입 스케일 대비 극단화
- pull-quote·stat callout 은 시각 센터피스 (단순 bold 처리 ❌)
- 섹션마다 distinct 한 시각 캐릭터

---

## 5. HTML 구조 표준

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{브랜드} — {토픽}</title>
  <meta name="description" content="..." />
  <!-- Open Graph (옵션) -->
  <meta property="og:title" content="..." />
  <meta property="og:image" content="images/hero.png" />
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=..." rel="stylesheet" />
  <style>
    /* :root + 섹션별 CSS — 단일 inline 스타일, 외부 CSS ❌ */
  </style>
</head>
<body>
  <nav class="nav"></nav>
  <section class="hero"></section>
  <section class="value-props reveal"></section>
  <section class="showcase reveal"></section>
  <section class="proof reveal"></section>
  <section class="how-it-works reveal"></section>  <!-- 체험단·이벤트만 -->
  <section class="cta-final reveal"></section>
  <footer class="footer"></footer>
  <script>
    /* IntersectionObserver scroll reveal + (옵션) 카운트다운 */
  </script>
</body>
</html>
```

**원칙**:
- 단일 HTML 파일. 외부 CSS·JS ❌
- 이미지 `<img src="images/{slot}.png" alt="...">` 상대 경로
- alt 텍스트 항상 (접근성)
- 신청 CTA `<a class="btn-primary" href="{외부 URL}" target="_blank" rel="noopener noreferrer">`

---

## 6. 스크롤 시네마틱 (선택, 사용자 명시 요청 시만)

> 사용자가 "세련된 LP / 스크롤에 따라 움직이는 / Apple 스타일 / 시네마틱 히어로" 키워드를 쓰면 본 § 6 패턴 적용. 디폴트는 § 1~5 의 정적 LP — 본 § 은 옵션 옵트인.

본 패턴은 **단일 HTML + 바닐라 JS** 로 100% 구현. Next.js / React / Vite / GSAP / Three.js 모두 ❌ — 1페이지 LP 에 빌드 스텝·번들러는 ROI 마이너스.

### 6-1. Hero Pattern 5: Sticky Video Scrub

스크롤 진행률 0~100% 가 `video.currentTime` 0~Ns 에 매핑. Apple Airpods Pro / Stripe 홈페이지 패턴.

```html
<section class="hero-pin">
  <div class="hero-sticky">
    <video class="hero-video"
           src="videos/hero-scrub.mp4"
           poster="images/hero-poster.jpg"
           muted playsinline preload="auto"
           aria-hidden="true"></video>
    <div class="hero-scrim"></div>
    <div class="hero-copy">
      <h1>{헤드라인}</h1>
      <p class="sub">{서브카피}</p>
      <a href="{외부 URL}" class="cta-primary">{CTA}</a>
    </div>
  </div>
</section>
```

```css
.hero-pin    { height: 200vh; position: relative; }
.hero-sticky { position: sticky; top: 0; height: 100vh; overflow: hidden; }
.hero-video  { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
.hero-scrim  { position: absolute; inset: 0;
               background: linear-gradient(90deg, var(--bg-light) 0%, transparent 55%);
               opacity: .85; }
.hero-copy   { position: relative; z-index: 2;
               display: flex; flex-direction: column; justify-content: center;
               height: 100%; padding: 0 8vw; max-width: 50%; }
```

```js
const pin = document.querySelector('.hero-pin');
const video = document.querySelector('.hero-video');
const isTouch = matchMedia('(hover: none)').matches;

if (isTouch) {
  // 모바일: scrub 포기, 표준 autoplay loop (currentTime seek 가 iOS Safari 에서 stutter)
  video.loop = true; video.autoplay = true;
  video.play().catch(()=>{});
} else {
  video.addEventListener('loadedmetadata', () => {
    let raf = null;
    const update = () => {
      const rect = pin.getBoundingClientRect();
      const total = pin.offsetHeight - innerHeight;
      const progress = Math.min(Math.max(-rect.top / total, 0), 1);
      video.currentTime = progress * video.duration;
    };
    addEventListener('scroll', () => {
      if (raf) return;
      raf = requestAnimationFrame(() => { update(); raf = null; });
    }, { passive: true });
    update();
  });
}
```

### 6-2. 영상 인코딩 룰 (ffmpeg)

Higgsfield/Kling 디폴트 H.264 GOP 는 ~30프레임 1키 → currentTime seek 시 같은 키프레임 안에서만 부드러움. 스크럽용으로 **모든 프레임을 키프레임으로** 재인코딩 필수:

```bash
ffmpeg -i hero-scrub-raw.mp4 \
  -vcodec libx264 -preset slow -crf 23 \
  -g 1 -keyint_min 1 -sc_threshold 0 \
  -movflags +faststart \
  -an \
  hero-scrub.mp4

# 포스터 (첫 프레임)
ffmpeg -i hero-scrub.mp4 -vframes 1 -q:v 2 hero-poster.jpg
```

- `-g 1`: 모든 프레임 키프레임 (시킹 부드러움)
- `-crf 23`: 품질 23 (시각 차이 미미, 크기 ~2.5MB @ 720p 5s)
- `-an`: 오디오 트랙 제거 (스크럽 LP 는 무음)
- `-movflags +faststart`: 메타데이터 앞쪽 → progressive 로드

### 6-3. 3D 패럴랙스 (나머지 섹션)

```css
:root { --scroll-y: 0; }
.parallax-card {
  perspective: 1500px;
  transform-style: preserve-3d;
  transition: transform .4s var(--ease);
}
.parallax-card:hover {
  transform: rotateY(6deg) rotateX(-3deg) translateZ(20px);  /* rotateY ≤ 10deg 캡 */
}
.reveal {
  opacity: 0; transform: translateY(40px) scale(.96);
  transition: opacity .8s var(--ease), transform .8s var(--ease);
}
.reveal.is-visible { opacity: 1; transform: translateY(0) scale(1); }
```

```js
// 마우스 위치 기반 spotlight (다크 CTA 섹션)
document.querySelector('.cta-final')?.addEventListener('mousemove', (e) => {
  const r = e.currentTarget.getBoundingClientRect();
  e.currentTarget.style.setProperty('--mx', `${(e.clientX - r.left) / r.width * 100}%`);
  e.currentTarget.style.setProperty('--my', `${(e.clientY - r.top) / r.height * 100}%`);
});
/* CSS: background: radial-gradient(circle at var(--mx) var(--my), var(--brand-sig), var(--bg-deep) 50%); */
```

### 6-4. (선택) Lenis 스무스 스크롤 1줄

```html
<script type="module">
  import Lenis from 'https://cdn.jsdelivr.net/npm/lenis@1.1.18/+esm';
  const lenis = new Lenis();
  (function raf(t){ lenis.raf(t); requestAnimationFrame(raf); })();
</script>
```

8KB 추가, 트랙패드/마우스 휠 inertia 강화. CSS 의존성 ❌ (JS 만).

### 6-5. 스크롤 시네마틱 회피 패턴 (banned-words.md § 7 와 동기)

- ❌ 수평 스크롤 캡처 — 사용자 방향 감 잃음
- ❌ 무한 스크롤 — LP 에 부적합
- ❌ 사운드 자동재생 — `<video>` 는 항상 `muted` + `playsinline`
- ❌ 스크롤 잠금 후 강제 애니메이션 (ESC 가능해야 함)
- ❌ sticky pin 트랙 > 300vh — 모바일에서 영상 1초가 페이지 1.5배 스크롤로 느껴짐
- ❌ 키프레임 재인코딩 없이 raw MP4 사용 — Safari·Chrome 에서 jerky
- ❌ `perspective` 1000px 미만 — 너무 가까워 왜곡, 1500~2000px 권장
- ❌ rotateY/rotateX > 10deg — 가독성 손실, 미세 틸트가 세련됨

### 6-6. 검수 체크리스트 (Step 4 추가 항목, 스크롤 시네마틱 사용 시)

- [ ] 영상이 `-g 1` 키프레임으로 재인코딩됨 (스크럽 부드러움)
- [ ] 모바일 폴백 분기 (`matchMedia('(hover: none)')`) 존재
- [ ] `<video>` 에 `muted playsinline preload="auto"` 모두 포함
- [ ] poster 이미지 지정 (LCP 빠르게)
- [ ] sticky pin `height: 200vh` 이내
- [ ] perspective ≥ 1500px, rotateY/rotateX ≤ 10deg
- [ ] 영상 1개 → 페이지 총 사이즈 ≤ 5MB

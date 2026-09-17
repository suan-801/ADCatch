---
name: 08-landing-page
description: 01_brand(자사) + (선택) 02_competitor + 03_customer 1페이지 분석을 인풋으로 받아, `references/` 7모듈(페이지 타입 3 + layout-toolkit·copy-rules·cta-library·banned-words)로 LP 카피·섹션 시나리오를 in-memory 도출 후 NanoBanana MCP(Gemini 기반)로 이미지 자동 생성 + `01_brand/products·logos/` 실재 자산 AS-IS 결합해 단일 HTML 파일을 `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v{N}.html` 로 빌드하는 스킬. 체험단 모집·이벤트·단일 상품 LP 3타입 지원. "신청하기" CTA 는 구글폼/Tally 등 외부 URL `<a>` 링크. 사용자가 "랜딩페이지 만들어줘", "체험단 페이지", "이벤트 페이지", "LP 제작", "/08-landing-page" 등으로 요청 시 호출. **사전 컨펌 게이트 ❌** — v1 출력 직후 페이지 시나리오·카피·이미지 슬롯을 채팅에 동봉해 사용자가 사후 검수·v2 반복. 데이터 분석 슬라이드·대시보드는 본 스킬 범위 ❌ (06번 스킬 예정).
---

# 08. 랜딩페이지 생성 (NanoBanana + HTML 단일 파일)

> 이 스킬의 목표는 **01~03 분석 + 사용자 토픽·페이지 타입 → 7모듈 도출 → NanoBanana 이미지 + 카피 → 단일 HTML 파일**.
> 광고 이미지(05a) · 카드뉴스(07) 와 차별점: **HTML 1장으로 마무리되는 콘텐츠**. 페이지 안에서 헤더 → 후킹 → 약속 → 증거 → CTA 까지 단일 스크롤 내러티브를 완성.

---

## 호출 시점

- "랜딩페이지 만들어줘"
- "체험단 페이지 / 체험단 모집 페이지"
- "이벤트 페이지 / 프로모션 페이지"
- "LP 만들어줘 / 단일 LP"
- "/08-landing-page"
- 01~03 분석이 채워지고 사용자가 단일 URL 산출물 요청

---

## Prerequisites

**필수**
- `.mcp.json` 에 `nanobanana` 서버 설정 — `mcp__nanobanana__gemini_generate_image` / `gemini_edit_image` 사용 가능
- `01_brand/brand_brief.md § 4-1` 컬러 6슬롯 채워짐 (비면 → "`/01-brand-from-url <URL>` 로 컬러부터 채워주세요" 안내 후 종료)
- **사용자 토픽** — "4주 챌린지 체험단", "1+1 이벤트", "광채 세럼 LP" 등 1줄
- **페이지 타입** — 체험단 / 이벤트 / 단일 중 1개 (미명시 시 단일 LP 디폴트)
- **신청 CTA URL** — 구글폼·Tally·자사몰 상품 페이지 등 외부 URL 1개 (없으면 `#` placeholder + 채팅 알림)
- (조건부) 제품·로고 등장 시: `01_brand/products/` 또는 `01_brand/logos/` 실재 PNG/JPG

**선택**
- `02_competitor/competitor_ads.md` (있으면 카피·헤드라인 시드)
- `03_customer/pain_points.md` (있으면 페인 → Hero 서브카피·USP 시드)
- `01_brand/products/ASSET_GUIDE.md` (있으면 자산 슬롯 매핑 1순위)

---

## 디폴트 설정 (사용자 override 가능)

| 항목 | 디폴트 | 다른 옵션 |
|---|---|---|
| 페이지 타입 | **단일 LP** | 체험단 모집 / 이벤트 |
| HTML 포맷 | **단일 파일 inline `<style>`** | 외부 CSS ❌ |
| 이미지 비율 | 히어로 16:9 + 콘텐츠 4:3 | 1:1 (정사각) |
| 폰트 | **Pretendard + Noto Serif KR** | brand_brief § 4-4 명시 폰트 |
| 디바이스 | **모바일 퍼스트 + 데스크탑 반응형** | 모바일 전용 / PC 전용 |
| 신청 CTA | **외부 URL `<a>` 링크 (구글폼·Tally 등)** | `<form>` 마크업 ❌ |

---

## Before You Start: Load Context

`01_brand/brand_brief.md` 1페이지에서 다음을 추출 — `01_brand/` 외부 ❌:

- **§ 한 줄 정의 / SKU·카테고리** — Hero 헤드라인 시드
- **§ USP 3개** — USP 카드·사회증거 정량 시드
- **§ 타겟·페인** — Hero 서브카피·페인 인용 시드
- **§ 톤 (Always / Never)** — 어휘·어미 룰
- **§ 4-1 컬러 6슬롯** — CSS `:root` 동적 주입 (ground truth)
- **§ 4-4 폰트** — Google Fonts import 결정

(선택) `03_customer/pain_points.md` § Top 5 페인 + Top 3 욕구
(선택) `02_competitor/competitor_ads.md` § 헤드라인 패턴 3개

---

## 핵심 원칙 (5줄, 절대 위반 ❌)

✅ **brand_brief § 4-1 컬러 6슬롯 ground truth** — AI 추정 HEX ❌. 슬롯 비면 호출 중단
✅ **제품·로고 reference AS-IS** — 등장 시 `01_brand/products·logos/` 실재 PNG. 재그리기 ❌. 위치·크기·라이팅 블렌드만 (05·07 동일 룰)
✅ **신청·구매 CTA = 외부 URL `<a>` 링크** — `<form>` 마크업 ❌, JS 검증 ❌, 결제 로직 ❌. URL 미수령 시 `#` placeholder + 채팅 알림
✅ **데이터 분석 슬라이드·대시보드 영역 ❌** — 본 스킬은 마케팅 LP 전용. 분석 리포트는 06번 스킬에서
✅ **결과물은 `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v{N}.html` + `images/`** — 덮어쓰기 ❌, v 증분

---

## Workflow (6 steps)

### Step 1: Gather Inputs + 페이지 타입 확정

**brand_brief.md § 4-1 컬러 6슬롯 점검** — `[확인 필요]` 잔존 시 호출 중단:
> "brand_brief.md § 4-1 컬러 팔레트 슬롯이 비어있습니다. `/01-brand-from-url <대표 상세페이지 URL>` 로 컬러를 먼저 채워주세요."

**페이지 타입 확정** — 사용자 메시지에서 키워드 매핑:
- "체험단 / 서포터즈 / 모집" → `references/page-types/tester-recruit.md`
- "이벤트 / 프로모션 / 세일 / 1+1 / 사전등록" → `references/page-types/event-promo.md`
- 그 외 (또는 미명시) → `references/page-types/single-lp.md` (디폴트)

미명시·모호 시 1줄 확인:
> "페이지 타입 한 줄로 알려주세요. ① 체험단 모집 / ② 이벤트·프로모션 / ③ 단일 상품 LP (미선택 시 ③)"

**토픽·CTA URL 수령** — 인풋 모호하면 사용자에게 묻기:
> "토픽 한 줄 + 신청 CTA URL 알려주세요. 예: '4주 챌린지 체험단 / https://forms.gle/...'"

**(선택) 02·03 로드** — 파일 존재 시 자동 로드, 부재 시 brand_brief 만으로 진행 (안내 ❌, 조용히 fallback).

---

### Step 1.5: Derive Page Scenario (in-memory)

> 모든 도출은 메모리 변수. 디스크 저장 ❌ (사용자 명시 요청 시만).

#### 1.5-1. 인풋 로드 (섹션 지정 Read)

| 파일 | 추출 섹션 |
|---|---|
| `01_brand/brand_brief.md` | § 한 줄 정의 + § USP + § 타겟·페인 + § 톤 + § 4-1 컬러 + § 4-4 폰트 + § Never |
| `03_customer/pain_points.md` | (있으면) Top 5 페인 + Top 3 욕구 |
| `02_competitor/competitor_ads.md` | (있으면) 헤드라인 패턴 3개 |

> ⚠️ **차별화 가드 (의무)**: 컬러·폰트·신뢰 섹션 톤·CTA 위치는 brand_brief 톤으로 통일. Hero 헤드라인·약속 라인·증거 수치는 자사 임상만 인용 (외부 사례 인용 ❌, 법적 리스크). 02 competitor 빈틈을 Hero·USP·신뢰 섹션에서 명확히 노출.

#### 1.5-2. 7모듈 로드 + 시나리오 도출

```
references/page-types/{tester-recruit|event-promo|single-lp}.md  → 페이지 골격 (섹션 시퀀스·카피 골격·이미지 슬롯)
references/layout-toolkit.md                                     → 섹션별 레이아웃 옵션 풀 + CSS 패턴 + 디자인 품질 룰
references/copy-rules.md                                         → 자수 캡·어미·구체 명사
references/cta-library.md                                        → CTA 카피·버튼 스타일
references/banned-words.md                                       → 금지어 자동 치환
```

**도출 순서**:

1. **페이지 골격 인용** — page-types/{선택}.md § 1 필수 섹션 골격 그대로 시퀀스 채택
2. **섹션별 레이아웃 옵션 선택** — layout-toolkit.md § 1 에서 섹션마다 1개 선택 (콘텐츠에 맞는 것, 가장 복잡한 것 ❌)
3. **카피 도출** — 섹션별 카피 골격 (page-types/{선택}.md § 2) + brand_brief § USP·페인·톤 → in-memory 카피 변수
4. **CTA 카피 선택** — cta-library.md § 1 페이지 타입별 풀에서 Hero·중간·Final 1개씩
5. **이미지 슬롯 계획** — page-types/{선택}.md § 3 + layout-toolkit.md § 3 → 히어로 16:9 1장 + 콘텐츠 4:3 1~2장 리스트업

---

### Step 2: Plan & Generate Images (NanoBanana 병렬 호출)

이미지 슬롯 리스트를 한 번에 병렬 호출 — `mcp__nanobanana__gemini_generate_image` 다중 tool call (단일 메시지에 묶기).

**호출 패턴**:
```
mcp__nanobanana__gemini_generate_image(
  prompt: "Editorial K-beauty product photography of {구체 명사}...
           Soft diffused natural light, warm neutral tones.
           Shot in the style of Kinfolk magazine — calm, intimate.
           Negative space at top-right. No text, no logos.",
  negative_prompt: "stock photography, oversaturated, neon colors,
                    text overlays, logos, watermarks, posed people,
                    generic, corporate, plastic surfaces",
  aspect_ratio: "16:9",  # 히어로 / 콘텐츠 "4:3"
  output_path: "08_landing/{YYYY-MM-DD}_{토픽-슬러그}/images/{slot}.png",
  reference_images: ["01_brand/products/{파일}.png"]  # 제품 등장 시
)
```

**원칙**:
- 제품·로고 등장 시 → `reference_images` 에 실재 PNG 첨부. 재그리기 ❌
- output_path 절대 누락 ❌ (메모리 룰: NanoBanana 저장 경로 항상 명시)
- 생성 후 짧게 Read 로 결과 확인 (파일 존재 + 비율 맞는지)

**Fallback** (NanoBanana 호출 실패 / 부적합 결과):
- CSS 그라데이션 placeholder 적용 + `role="img" aria-label="..."` 추가
- 채팅 보고에 "이미지 N장 placeholder 입니다" 명시 → 사용자 v2 에 재생성 요청

---

### Step 2.5: (선택) 스크롤 시네마틱 영상 생성

> **옵트인 트리거** — 사용자 메시지에 다음 키워드 1+ 포함 시만 진입: "세련된", "스크롤 영상", "스크롤에 따라 움직이는", "시네마틱 히어로", "Apple 스타일", "3D 홈페이지".
> 미해당 시 Step 3 직행 (디폴트는 정적 이미지 LP).

`layout-toolkit.md § 6 스크롤 시네마틱` 패턴 적용:

1. **Higgsfield CLI 영상 1샷 생성** (`/06-ad-video-higgsfield` 우회 호출)
   ```bash
   higgsfield generate create kling3_0 \
     --image ./images/hero.png \
     --prompt "Slow cinematic push-in toward the {제품 명사}. Subtle shimmer on {제형 디테일}. Left half of frame stays in soft focus for headline overlay. No subject movement, no hand entry, no text appearing." \
     --duration 5 --aspect_ratio 16:9 --mode std --sound off
   ```
   - 큐 길면 Seedance 2.0 `--mode fast` 폴백 (Kling 3.0 보다 보통 빠름)
   - 비동기로 큐잉 (`--json` 받아서 job ID 확보) → `higgsfield generate wait <id> --timeout 25m --interval 15s` 별도 폴링
   - 출력은 `videos/hero-scrub-raw.mp4` 또는 클라우드 URL → `curl -L -o` 로 받기

2. **ffmpeg 스크럽 최적화 재인코딩**
   ```bash
   ffmpeg -y -i hero-scrub-raw.mp4 \
     -vcodec libx264 -preset slow -crf 23 \
     -g 1 -keyint_min 1 -sc_threshold 0 \
     -movflags +faststart -an \
     videos/hero-scrub.mp4
   ffmpeg -y -i videos/hero-scrub.mp4 -vframes 1 -q:v 2 -update 1 images/hero-poster.jpg
   ```

3. **HTML 마크업** — Step 3 빌드 시 `layout-toolkit.md § 6-1` Hero Pattern 5 (Sticky Video Scrub) 마크업 인용. `.hero` 대신 `.hero-pin` + `.hero-sticky` + `<video>` 사용.

4. **JS 추가** — `layout-toolkit.md § 6-1` 의 scrub 로직 + § 6-3 의 3D parallax 인용. 모바일 폴백 (`matchMedia('(hover: none)')`) 필수.

5. **검수 추가** — `layout-toolkit.md § 6-6` 체크리스트 통과 (키프레임 재인코딩·모바일 폴백·sticky pin ≤ 200vh 등).

**Fallback** (Higgsfield 호출 실패·큐 25분 초과):
- 영상 생성 포기 → 디폴트 정적 Hero (Split-screen / Full-bleed)로 대체
- 채팅 보고에 "영상 생성 실패, 정적 이미지 LP 로 빌드 — 영상 재시도 시 v 증분 빌드" 명시

---

### Step 3: Build HTML

단일 파일 `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v{N}.html` 작성:

**파일명 결정** — 기존 v 검색:
```bash
ls 08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v*.html 2>/dev/null
```
없으면 v1, 있으면 max(v) + 1.

**HTML 구조** (layout-toolkit.md § 5 표준):

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{브랜드} — {토픽}</title>
  <meta name="description" content="{Hero 서브카피}" />
  <meta property="og:title" content="{Hero 헤드라인}" />
  <meta property="og:description" content="{Hero 서브카피}" />
  <meta property="og:image" content="images/hero.png" />
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
  <link href="https://fonts.googleapis.com/css2?family=Noto+Serif+KR:wght@400;500;700&family=Pretendard:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
  <style>
    /* :root 에 brand_brief § 4-1 6슬롯 주입 (모두 사용 필수) */
    :root {
      --bg-light:    #{brand_brief BG-Light HEX};
      --bg-deep:     #{brand_brief BG-Deep HEX};
      --brand-sig:   #{brand_brief BRAND-Signature HEX};
      --brand-sub:   #{brand_brief BRAND-Sub HEX};
      --text-primary:#{brand_brief TEXT-Primary HEX};
      --text-sub:    #{brand_brief TEXT-Sub HEX};
      --font-display:'Noto Serif KR', serif;
      --font-body:   'Pretendard', 'Noto Sans KR', sans-serif;
      --ease: cubic-bezier(0.16, 1, 0.3, 1);
      --radius: 14px;
    }
    /* layout-toolkit.md § 2 패턴 적용 */
    /* 섹션별 CSS */
  </style>
</head>
<body>
  <!-- 페이지 타입별 섹션 마크업 (page-types/{선택}.md § 1 골격) -->
  <section class="hero">...</section>
  <section class="value-props reveal">...</section>
  ...
  <section class="cta-final reveal">...</section>
  <script>
    /* IntersectionObserver scroll reveal */
    const io = new IntersectionObserver((entries) => {
      entries.forEach(e => { if (e.isIntersecting) e.target.classList.add('is-visible'); });
    }, { threshold: 0.15 });
    document.querySelectorAll('.reveal').forEach(el => io.observe(el));
    /* (옵션) D-day 카운트다운 — 사용자 명시 요청 시만 */
  </script>
</body>
</html>
```

**원칙**:
- 외부 CSS·JS ❌ (단일 HTML 파일)
- 이미지: `<img src="images/{slot}.png" alt="...">` 상대 경로
- 신청 CTA: `<a class="btn-primary" href="{사용자 제공 URL}" target="_blank" rel="noopener noreferrer">`
- URL 미수령 시: `<a href="#" data-cta-pending="true">` (Step 5 채팅에 알림)
- brand_brief § 4-1 6슬롯 6개 변수 모두 페이지 안에서 사용 (Step 4 검수)

---

### Step 4: Self-Validate

빌드 직후 자동 검수 (호출 직전 in-memory):

**카피 검수**
- [ ] `banned-words.md` 의 ❌ 단어 발견 → 자동 치환
- [ ] `copy-rules.md § 2` 자수 캡 위반 → in-memory 수정 (Hero ≤20자, CTA ≤10자 등)
- [ ] 페이지 전체 느낌표 ≤1개
- [ ] CTA 버튼이 혜택과 묶인 동사구 (제너릭 "클릭" ❌)
- [ ] brand_brief § 톤 Never 어휘 부재

**비주얼 검수**
- [ ] `:root` 의 6슬롯 모두 페이지 안에서 사용됨
- [ ] brand_brief § 4-2 사용 ❌ 컬러 부재
- [ ] 이미지 alt 텍스트 모두 채워짐
- [ ] 모바일 반응형 breakpoint (900px / 600px) 적용

**페이지 타입 검수**
- [ ] page-types/{선택}.md § 6 (또는 § 7) 의 체크리스트 모두 통과
- [ ] 필수 섹션 누락 ❌
- [ ] CTA 외부 URL 동일성 (페이지 안 모든 CTA 한 URL)

위반 1개라도 있으면 v1 출력 전 in-memory 수정. 수정 불가능한 항목 (예: URL 누락) 만 채팅 보고.

---

### Step 5: Report v1 (★ 사전 컨펌 게이트 ❌)

빌드 완료 직후 사용자에게 채팅으로 동봉:

```
✅ 08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v1.html 생성

📄 페이지 타입: {체험단 / 이벤트 / 단일}
🎨 컬러 슬롯: brand_brief § 4-1 6슬롯 모두 적용
🖼  이미지: NanoBanana N장 (히어로 16:9 + 콘텐츠 4:3 ×N)
🔗 신청 CTA: {사용자 제공 URL} (또는 ⚠️ placeholder `#`)

[섹션 시퀀스]
1. Hero — "{Hero 헤드라인}"
2. {섹션 2} — ...
...
N. Final CTA — "{CTA 카피}"

[검수 결과]
- 자수 캡: 통과
- banned-words: N개 자동 치환 ({치환 내역})
- 6슬롯 사용률: 6/6

어디 더 수정할까요?
- 카피 톤 / 섹션 순서 / 이미지 / CTA 카피 / 레이아웃 옵션 등
- 수정 요청 시 v2 신규 생성 (v1 덮어쓰기 ❌)
```

**사용자 피드백 → v2**:
- "Hero 카피 더 짧게" → v2 신규 생성 + Hero 만 수정 + 나머지 유지
- "혜택 카드 4개로" → v2 + Value Props 섹션만 확장
- "이미지 톤 더 따뜻하게" → NanoBanana 재호출 (Step 2) + v2

**v 증분 룰**: `index-v1.html` → `index-v2.html` → `index-v3.html` ... 덮어쓰기 ❌. 이미지도 슬롯 변경 시 `hero.png` → `hero-v2.png` (or 슬롯명 유지하고 폴더 분리: `images-v2/`).

---

## 파일명 규칙

- 메인 HTML: `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v{N}.html`
- 이미지: `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/images/{slot}.png`
  - 슬롯명: `hero`, `content-1`, `content-2`, ...
  - v2 이상에서 이미지 재생성 시: `images/hero-v2.png` 또는 `images-v2/hero.png` (사용자 선호 따라)
- 토픽 슬러그: 영소문자 + 하이픈 (예: "4주 챌린지 체험단" → `summer-tester`)

---

## CHANGELOG 동시 갱신 룰 (메모리)

작업 중 사용자가 룰성 피드백 ("앞으론 X 안 써", "Y 표현 금지", "Z 패턴 디폴트로") 을 주면:

1. 해당 references 파일 본문 갱신 (예: `banned-words.md` § 2 추가)
2. SKILL.md 체크리스트 갱신 (해당 시)
3. `CHANGELOG.md` 에 날짜·변경사항·영향범위·후속 4항 기록

"이번만" 표현은 갱신 ❌. 룰성 표현 ("앞으로", "디폴트로", "항상") 만 갱신.

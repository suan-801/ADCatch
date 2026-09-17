---
name: 07-carousel-nanobanana
description: 01_brand(자사) + 02_competitor(경쟁사) + 03_customer(고객) 1페이지 분석을 통합 인풋으로 받아, `references/` 5모듈(내러티브 아크·슬라이드 레이아웃·자수 캡·CTA 라이브러리·금지어) + `references/styles/STYLE-GUIDE.md` (사용자 reference 기반 5스타일 풀) 로 N장 슬라이드 시나리오를 in-memory 도출 후 NanoBanana MCP (Gemini 기반) 로 인스타그램 카드뉴스(.png 시퀀스) 를 생성해 `07_carousel/{YYYY-MM-DD}_{캠페인-슬러그}/` 에 저장하는 스킬. 사용자가 "카드뉴스 만들어줘", "캐러셀 제작", "인스타 슬라이드", "/07-carousel-nanobanana" 등으로 요청 시 호출. **사전 컨펌 게이트 ❌** — v1 출력 직후 N장 슬라이드 시나리오를 채팅에 동봉해 사용자가 사후 검수·v2 반복. 파워 유저가 `04_brief/confirmed_brief.md` 를 사전 작성한 경우만 인용 (분기 A). 디폴트는 분기 B (01/02/03 동적 로드).
---

# 07. 카드뉴스 (캐러셀) 생성 (NanoBanana → PNG 시퀀스)

> 이 스킬의 목표는 **01~03 분석 풀 디테일 + 사용자 토픽 → 5모듈 + STYLE-GUIDE 도출 → NanoBanana 슬라이드별 호출 → N장 PNG 시퀀스 + 시나리오 채팅 보고**.
> 광고 이미지(05a)와 차별점: 1장 후킹 → **N장 시퀀스 + 내러티브 아크 (Hook → 본문 → CTA)**. 시각 일관성 강제 (같은 배경·타이포·모티프 N장 통일).

## 호출 시점

- "카드뉴스 만들어줘"
- "캐러셀 제작해줘"
- "인스타 슬라이드 5장"
- "정보 카드 시리즈"
- "/07-carousel-nanobanana"
- 01~03 분석 3종이 채워지고 사용자가 SNS 오가닉 콘텐츠 요청

## Prerequisites

**필수**:
- `.mcp.json` 에 `nanobanana` 서버 설정 — `mcp__nanobanana__gemini_generate_image` / `gemini_edit_image` 사용 가능 여부 확인
- `01_brand/brand_brief.md` § 4-1 컬러 6슬롯 채워짐 (없으면 → "`/01-brand-from-url <URL>` 로 컬러를 먼저 채워주세요" 안내 후 종료)
- **사용자 토픽** — "4주 챌린지 시리즈", "성분 스토리텔링", "잡티 케어 3가지 팁" 등 1줄
- (조건부 필수) 제품·로고 등장 시: `01_brand/products/` 또는 `01_brand/logos/` 실재 PNG/JPG

**선택**:
- `02_competitor/competitor_ads.md` (있으면 빈틈·패턴 시드)
- `03_customer/pain_points.md` (있으면 페인 → 슬라이드 본문 시드)
- `references/styles/STYLE-GUIDE.md` + `references/styles/{01-05}/` 5스타일 슬롯 폴더별 5~7장 reference (있으면 스타일 매핑, 없으면 brand_brief 디폴트)
  - 자동 수집: `_scripts/fetch_style_refs.py` 가 `references/styles/reference-urls.md` 의 URL 들을 Apify IG 액터로 다운로드 → 슬롯 폴더에 저장 (사용 시 `APIFY_TOKEN` 필요)
- **`01_brand/products/ASSET_GUIDE.md`** — 있으면 § Step 1.5-3 자산 슬롯 매핑을 본 파일 표로 1순위 인용. 없으면 SKILL 디폴트 3행 표로 fallback
- **`04_brief/confirmed_brief.md`** — 있으면 § 인용 (분기 A). 없으면 분기 B 디폴트.

## 디폴트 설정 (사용자 override 가능)

| 항목 | 디폴트 | 다른 옵션 |
|---|---|---|
| 슬라이드 수 | **5장** | 3 / 7 / 10 (IG 카루셀 한도 10장) |
| 비율 | **4:5** (1080×1350) | 1:1 / 9:16 (Story) |
| 플랫폼 | **Instagram** | LinkedIn 1:1·4:5 / Facebook 1:1·16:9 / X 16:9 |
| 모드 | **캐러셀** | 단일 정적 이미지 |
| NanoBanana 모드 | **Method 1** (input image conditioning, 제품/로고 등장 시) 또는 **generate_image** (제품 미등장 일러스트 슬라이드) | Method 2 (배경만 + 사용자 합성) |

## Before You Start: Load Context

`01_brand/brand_brief.md` 1페이지에서 다음을 추출 — `01_brand/` 외부 ❌:

- **보이스** (§ 톤·banned words) — 슬라이드 텍스트의 어미·어휘
- **비주얼** (§ 4-1 컬러 6슬롯·§ 4-2 사용 ❌ 컬러·§ 4-4 폰트) — 배경·타이포 디폴트
- **제품·USP** — 본문 슬라이드 RTB 시드

## 핵심 원칙 (5줄, 절대 위반 ❌)

✅ **제품·로고 reference AS-IS** — 등장 시 `01_brand/products/`·`01_brand/logos/` 실재 PNG. 재그리기/리스타일 ❌. 위치·크기·라이팅 블렌드만 허용 (`05-ad-image-nanobanana` 와 동일 룰)
✅ **N장 시각 일관성 강제** — 같은 배경·타이포·모티프·로고 위치 N장 통일. `slide-templates.md § 시안 일관성` 5축 준수
✅ **슬라이드당 텍스트 캡** — Hook ≤8단어·≤15자 / 본문 ≤30자×2줄 / CTA ≤12자. `text-density-caps.md` 자동 검수
✅ **brand_brief § 4-1 6슬롯 ground truth** — AI 추정 HEX ❌. 슬롯 비면 호출 중단
✅ **CTA 슬라이드 = 직접 가격·% OFF ❌** — `carousel-cta-library.md` 6종 (저장·공유·댓글·프로필·DM·시리즈) 중 1개. 가격은 IG 캡션 본문에

> **분기**: 분기 A (confirmed_brief.md 존재) → § 인용 / 분기 B (디폴트) → Step 1.5 자동 도출. 시나리오는 in-memory 변수, 디스크 저장 ❌ (사용자 명시 요청 시만).

---

## Workflow (6 steps)

### Step 1: Gather Inputs (인풋 로드) + 분기 판정

먼저 `04_brief/confirmed_brief.md` 존재 여부 확인:

- **분기 A — `confirmed_brief.md` 존재**: § 2 카피 / § 3 무드 / § 4 제품 reference / § 6 포맷 그대로 인용. Step 1.5 스킵.
- **분기 B — 부재 (디폴트)**: Step 1.5 진입.

**brand_brief.md § 4-1 컬러 6슬롯 점검 (분기 무관 공통)** — `[확인 필요]` 잔존 시 호출 중단:
> "brand_brief.md § 4-1 컬러 팔레트 슬롯이 비어있습니다. `/01-brand-from-url <대표 상세페이지 URL>` 로 컬러를 먼저 채워주세요."

**사용자 토픽 확정** — 인풋이 모호하면 사용자에게 1줄 확인:
> "토픽 한 줄로 알려주세요. 예: '4주 챌린지 시리즈', '잡티 케어 3가지 팁', '성분 스토리'"

**슬라이드 수 / 비율 / 플랫폼 확정** — 사용자 명시 우선, 미명시 시 디폴트 (5장 / 4:5 / Instagram)

---

### Step 1.5: Derive Slide Scenario (★ 분기 B 만, in-memory 도출)

> ⚠️ 분기 A 면 본 단계 전체 스킵.

#### 1.5-1. 인풋 로드 (섹션 지정 Read)

| 파일 | 추출 섹션 |
|------|----------|
| `01_brand/brand_brief.md` | § 4-1 컬러 + § 4-4 폰트 + § USP 3개 + § 가격·번들·프로모션 + § Never 표현 |
| `03_customer/pain_points.md` | Top 5 페인 + Top 3 욕구 |
| `02_competitor/competitor_ads.md` | 자주 쓰는 헤드라인 패턴 3개 · 빈틈 3개 |
| `references/styles/STYLE-GUIDE.md` | (있을 때만) 5스타일 풀 — 사용자 토픽 매핑 |

> ⚠️ **차별화 가드 (의무)**: 시각 5축 일관성(BG·Photo·Illustration·Typography·PROP)·톤·레이아웃 격자는 슬라이드 전체에 통일. N장 슬라이드 중 1번(Hook) 슬라이드는 02 competitor 빈틈 또는 03 페인 기반으로 도출 — 경쟁사 후킹 카피 그대로 차용 ❌. 헤드라인 카피·앵글·내러티브 아크는 자사 USP 기반 변주.

#### 1.5-2. 5모듈 로드 + 시나리오 도출

```
references/carousel-narrative-arc.md   → 3개 골격 (정보형·스토리형·리스트형) + 슬라이드별 시나리오 룰
references/slide-templates.md          → 슬라이드 레이아웃 풀 (Hook 5종·본문 5종·CTA 5종) + 시각 일관성 5축
references/text-density-caps.md        → 자수 캡 (Hook ≤15자 / 본문 ≤30자×2 / CTA ≤12자)
references/carousel-cta-library.md     → CTA 6종 (저장·공유·댓글·프로필·DM·시리즈)
references/banned-words.md             → 자동 검수·치환 (한글 카피)
```

도출 순서:

1. **골격 선택** (`carousel-narrative-arc.md § 3` 매핑 표) — 사용자 토픽·페인·USP 조합 → 정보형/스토리형/리스트형 1개
2. **스타일 선택** (`STYLE-GUIDE.md § Quick Comparison 표` 1차 후보 → 본문 5스타일 풀 정독 2차 결정) — 있으면 사용자 토픽 매핑. 없으면 brand_brief 디폴트 + 트렌드 가이드
3. **★ Reference 시각 흡수** (1차 출처) — 선택한 스타일 슬롯 폴더 (`references/styles/{01-05}/`) 의 reference PNG **2~3장** 을 `Read` 로 시각 흡수. **5축 추출** (4축 → 5축, `PROP INVENTORY` 추가 — 2026-05-11):
   - **BG**: 배경 컬러·텍스처·라이팅·그라데이션
   - **Photo**: 제품/인물 비중·구도·풀블리드 vs 부분
   - **Illustration**: 일러스트·아이콘·소품·라벨 박스 유무
   - **Typography**: 한·영 믹스 비율·sans/serif·자간·줄바꿈 의도 + **텍스트 영역이 캔버스에서 차지하는 픽셀 비율**
   - **★ PROP INVENTORY** (신설) — reference 에 등장하는 **물리 오브젝트를 verbatim 으로 리스트업**. 예: "검정 메탈 바인더 클립 좌상단", "폴라로이드 카드 2장 스택, ~3° 회전, 두꺼운 흰 보더", "마스킹 테이프 한 조각", "종이 모서리 접힘". 추상 속성("editorial feel") ❌, **구체 명사** 만. 이 인벤토리는 Step 4 `[3] EFFECT` 에 그대로 인용 의무.

   ★ **Reference-Literal Mode** (신설 — 2026-05-11):
   - 마스트헤드·헤드라인이 reference 에 **없으면 만들지 말 것**. AI 가 "잡지스러우니 큰 마스트헤드 박자" 추정 ❌
   - 캡션 위치·크기·정렬은 reference 픽셀 그대로 (예: ref 가 우하단 작은 캡션이면 우하단 작은 캡션)
   - 슬라이드 텍스트 점유 픽셀 비율 ≤ reference 의 텍스트 점유 픽셀 비율
   - PROP INVENTORY 항목 누락 ❌ — reference 에 있는 물리 오브젝트는 슬라이드에도 반드시 등장

   reference 가 1장 미만이면 본 단계 스킵 → Layer 3·4 + brand_brief 디폴트로
4. **슬라이드별 1줄 시나리오 N개** — Hook 1 + 본문 N-2 + CTA 1. `carousel-narrative-arc.md § 1` 5장 매핑 예시 참조
5. **레이아웃 매핑** (`slide-templates.md`) — 슬라이드별 H/B/C 풀에서 1개 (Hook H1~H5 / 본문 B1~B5 / CTA C1~C5)
6. **자동 검수·치환**:
   - `text-density-caps.md` — 자수 캡 초과 시 압축
   - `banned-words.md` — "비드" → "캡슐" / 가격·% OFF 시각 영역 제거
   - `carousel-cta-library.md` — CTA 슬라이드를 6종 풀에서 1개로
7. **결과는 in-memory** (디스크 저장 ❌) — 슬라이드 N장 + 시각 일관성 5축 (배경·타이포·여백·모티프·로고 위치)

#### 1.5-3. 자산 슬롯 매핑

**1순위 — `01_brand/products/ASSET_GUIDE.md` 가 있으면 § 슬롯 매핑 표 그대로 인용**:
- 시나리오별 1순위 자산 컬럼을 슬라이드 N장에 자동 분배 (예: Hook → hero, 카드 5 → formula-macro, CTA → cutout + wordmark-kr)
- ASSET_GUIDE 가 권장하는 슬롯 매핑 (예: "에디토리얼 Hook → prop-shot") 우선

**2순위 — ASSET_GUIDE.md 부재 시 SKILL 디폴트 3행 표 fallback**:

| 슬롯 | 파일 | 등장 슬라이드 |
|------|------|-------------|
| `input_image_path_1` (제품) | `01_brand/products/<메인 히어로>` | 제품 등장 슬라이드 (보통 Hook 또는 본문 1장) |
| `input_image_path_1` (로고) | `01_brand/logos/<로고 PNG>` | 로고 등장 슬라이드 (보통 마지막 CTA 또는 모든 슬라이드 좌하단) |
| reference (텍스처) | `01_brand/products/<제형 매크로>` | 텍스처 매크로 슬라이드 (있으면) |

> ASSET_GUIDE 부재 + `01_brand/products/` 에 자산이 3개 이상 있으면, 사용자에게 1회 질의 후 ASSET_GUIDE.md 자동 작성 제안 (사용자 승인 시만 디스크 영구화).

---

### Step 2: Build Visual Direction (Layer 1~4)

크리에이티브 디렉션 4 레이어 (우선순위 1 > 2 > 3 > 4):

#### Layer 1: 시나리오 + 비주얼 시드 (1차 소스)

**분기 A**: confirmed_brief.md § 2·3·4 그대로 인용
**분기 B**: Step 1.5 도출 시나리오 + 골격 + 스타일 슬롯 (있으면) + brand_brief § 4-1·4-4

#### Layer 2: Style Reference Image (시각 강화, 옵션 — 단 있으면 ★ 1순위)

`references/styles/{선택한 슬롯}/` 폴더에 사용자 reference 가 있으면:
- 폴더 내 모든 reference 파일 enumerate (Glob `references/styles/{slot}/ref-*.png`)
- **2~3장** `Read` 로 시각 흡수 (1장만이면 노이즈에 흔들림, 4장 이상은 토큰 비용·디시전 분산)
  - reference 가 5~7장 있으면 "다양성이 큰 3장" 선택 (예: 인물 1 + 라벨 1 + 풀블리드 1)
  - 5장 미만이면 모든 장 흡수
- 4축 추출 — **BG·Photo·Illustration·Typography** (Step 1.5-2 ③ 와 동일 4축, Layer 1 시나리오와 결합)
- 추출 결과를 Step 4 `[GLOBAL STYLE]` 헤더 + 슬라이드별 `[1] BACKGROUND` `[3] EFFECT` `[4] TEXT EFFECT` 어휘에 인용

> ⚠️ Step 1.5-2 ③ "Reference 시각 흡수" 와 Layer 2 는 동일 작업의 두 단계 표현 — Step 1.5 는 시나리오 도출 시점, Layer 2 는 프롬프트 합성 시점. **반복 Read ❌ — Step 1.5 ③ 결과를 in-memory 변수로 보관 후 Layer 2 에서 인용.**

reference 가 없으면 본 레이어 스킵 → Layer 3·4 + brand_brief 디폴트로.

#### Layer 3: 2025 한국 카드뉴스 트렌드 (필수 참고)

`slide-templates.md § 트렌디 한국 카드뉴스 레이아웃 패턴` 절 인용:

✅ **권장**:
- 좌측 정렬 + 충분한 여백
- 1슬라이드 1메시지 (글자 3줄 미만)
- 핵심 단어만 컬러 강조 (시안 1장 = `BRAND-Signature` 1포인트)
- 손글씨·뱃지·말풍선 캘아웃
- 흑백 베이스 + 1포인트 컬러

❌ **피하기**:
- 풀 컬러 그라데이션 배경
- 빽빽한 본문 텍스트 (3줄 이상)
- 슬라이드마다 다른 폰트
- 과한 3D 효과·드롭쉐도우
- 스톡 포토 룩

#### Layer 4: 토픽·골격별 스타일 매핑

`carousel-narrative-arc.md § 3` + `slide-templates.md § 레이아웃 풀` 표 인용:

| 골격 | 추천 Hook 레이아웃 | 추천 본문 레이아웃 | 추천 CTA 레이아웃 |
|---|---|---|---|
| ① 정보형 | H1 빅 타이포 / H3 숫자 후킹 | B1 헤드+본문+제품 / B4 인포그래픽 | C1 솔리드 / C4 댓글 유도 |
| ② 스토리형 | H4 페인 인용 / H2 질문+제품 | B5 풀블리드 사진 / B3 인용+텍스처 | C2 저장 / C5 시리즈 |
| ③ 리스트형 | H3 숫자 후킹 / H1 빅 타이포 | B2 항목 카드 | C2 저장 (디폴트) |

> ★ **H0 — Reference Mockup** (신설 — 2026-05-11): reference 이미지가 **명확한 mockup 패턴**(폴라로이드+클립 / 잡지컷+마스킹테이프 / 노트북 페이지 + 종이 접힘 / 책 페이지 + 손글씨 등)을 가지면 H1~H5 매핑을 건너뛰고 **reference 의 prop 인벤토리를 그대로 재현**한다. 텍스트는 reference 의 캡션 사이즈·위치 그대로. 거대 마스트헤드·헤드라인을 임의로 덧붙이지 ❌.
> 
> H0 트리거 신호: PROP INVENTORY 축에 물리 오브젝트가 **2개 이상** 등장 / reference 의 텍스트 점유 픽셀 비율 < 15%.
> 
> 본·CTA 슬라이드도 같은 prop 인벤토리(클립·폴라로이드 보더 등)를 시그니처 모티프로 재사용해 N장 일관성 유지.

---

### Step 3: Determine Format and Slide Count

분기 A 면 confirmed_brief § 6 비율 인용. 분기 B 면 사용자 지정 또는 디폴트:

| Platform | Placement | Aspect Ratio | Dimensions | 슬라이드 수 권장 |
|---|---|---|---|---|
| **Instagram** (디폴트) | Carousel Feed | **4:5** | 1080×1350 | 5장 (3~10) |
| Instagram | Square | 1:1 | 1080×1080 | 5장 |
| Instagram | Story | 9:16 | 1080×1920 | 3~5장 (Story 시퀀스) |
| LinkedIn | Carousel Document | 4:5 / 1:1 | 1080×1350 / 1080×1080 | 5~10장 |
| Facebook | Carousel | 1:1 / 16:9 | 1080×1080 / 1200×628 | 3~5장 |

---

### Step 4: Build the Prompt (슬라이드별 5요소)

NanoBanana 슬라이드별 단일 영문 프롬프트. 한글 슬라이드 텍스트는 큰따옴표로 그대로 보존.

#### 공통 시스템 헤더 (모든 슬라이드 동일 — 시각 일관성)

```
[GLOBAL STYLE — applied to all N slides in this set]
- Background palette: <brand_brief § 4-1 슬롯 ID + HEX 1~2개>
- Typography family: <brand_brief § 4-4 폰트>
- Margin: 8% left/right (consistent across all slides)
- Recurring motif: <시그니처 소품 1개 — 예: capsule beads / sparkle particles>
- Logo placement: <위치 — 예: bottom-left, 80px from edge>
- Style: <STYLE-GUIDE.md 매핑 스타일 슬롯 어휘 — 없으면 "minimal Korean editorial 2025">
```

#### 슬라이드별 5요소 프롬프트

```
[1] BACKGROUND
   <Layer 1·2·3 종합 — 시안 전체 동일>

[2] PRODUCT (등장 시만) — ★ product-anchored AS-IS directive
   "Use input_image_path_1 as the IMMUTABLE GROUND TRUTH for the product.
    Composite the actual reference pixels.
    DO NOT redraw, repaint, regenerate, restyle, or 'improve' the product.
    Allowed: position, scale, slight rotation, lighting blend with the new background.

    ★ ANCHOR ATTRIBUTES (must match reference exactly, never infer from text):
      • Jar body color: <ASSET_GUIDE 의 jar-anchor 인용 — 예: opaque white #FFFFFF, NOT transparent, NOT tinted>
      • Lid color: <예: opaque white #FFFFFF, NOT transparent>
      • Label text glyphs: preserve every character exactly as in the reference pixels
        (do not respell, do not re-render, do not paraphrase the brand/product/ingredient names)
      • Formula appearance inside the jar (only visible when lid is removed in the reference):
        <ASSET_GUIDE 의 formula-anchor 인용 — 예: dark purple gel surface with small RED bead capsules,
         NOT pink-magenta gel, NOT vitamin pills, NOT large floating capsules>

    ★ DO-NOT-INFER-FROM-TEXT rule:
      Any product/formula description appearing elsewhere in this prompt
      (brand_brief § 4-4 제형 묘사 등) is for TEXTURE MACRO slides ONLY.
      For jar-front shots, ignore those text descriptions — the reference image is the only source of truth."

[3] EFFECT — 슬라이드별 부가 요소·소품
   <시그니처 모티프 + 슬라이드별 보강 — 예: 손글씨 화살표, 별 4개, 따옴표>

[4] TEXT EFFECT — 슬라이드 텍스트 시각 효과
   ★ 텍스트는 in-memory 시나리오 그대로 큰따옴표 인용 (분기 A: confirmed_brief / 분기 B: Step 1.5)
   • Headline: <폰트 패밀리>, <사이즈 상상치 — 예: 80pt>, color #<TEXT-Primary HEX>
   • Body: <폰트>, <사이즈>, #<TEXT-Sub HEX>
   • 1포인트 강조: <BRAND-Signature HEX> 시그니처 컬러 (시안 1장 = 1포인트)
   • Text content (정확히):
     - Headline: "<슬라이드 N장 헤드>"
     - Body (있으면): "<슬라이드 N장 본문>"

[5] LAYOUT — `slide-templates.md` H/B/C 풀에서 매핑된 1개
   <H1~H5 / B1~B5 / C1~C5 중 1개 어휘 그대로 인용>
   • 텍스트 위치: <상단/하단/좌측·우측 + 정확한 비율>
   • 제품/로고 위치 (있으면): <위치>
   • 페이지 인디케이터 (선택): "<N/총수>" 우상단 작게

[NEGATIVE]
   no extra text overlay (only the specified headline and body),
   no fictional product, no redrawn product or logo,
   no 3D text, no heavy drop shadows, no over-saturated neon,
   no clip-art starbursts, no plastic over-glossy fake highlights,
   no warped fingers/teeth/eyes (if model present),
   no horizontal full-color gradients (only soft 2-color brand gradients),
   no Korean text distortion (use clean rendering),
   ★ no English label text distortion — preserve every label character exactly
     (e.g., "LUMINOUS FIT" must not become "LUANNOUS FIT";
            "NIACINAMIDE" must not become "NIACAINNAMIDOE"),
   ★ no transparent / tinted / re-colored jar — the jar BODY and LID stay
     opaque white as in the reference (do not make jar glassy or see-through),
   ★ no vitamin pills, no large floating capsule pills inside the jar
     (the formula is a gel surface with small 1-3mm bead capsules, NOT pharmacy pills),
   ★ no inferring product appearance from any text description in this prompt —
     the input_image is the single source of truth for jar shape, color, label glyphs, and formula

[CLOSING]
   Premium Korean Instagram carousel slide, 2025 editorial aesthetic.
   Slide <N> of <총수> in the same visual set — must match the global style header above.
```

> ⚠️ AI 추정 한글 카피·HEX·제형 묘사 ❌. 분기 A 는 confirmed_brief, 분기 B 는 Step 1.5 in-memory + brand_brief 그대로 인용.

---

### Step 5: Generate Slides (N장 호출)

**도구 분기 (3 Method)**:

| Method | 시나리오 | 호출 |
|---|---|---|
| **Method 1 — Input Image Conditioning** | 제품 단독 등장 (Hook·본문 1장) | `gemini_edit_image` + `input_image_path_1=<제품>` |
| **Method 2 — BG-Only Generation** | 일러스트·텍스트만 (제품 미등장) 또는 풀블리드 BG 후 사용자 합성 | `gemini_generate_image` (input image ❌) |
| **Method 3 — Product + Logo Dual Input** | 제품·로고 동시 정확 배치 (CTA 슬라이드 / 카드 7) | `gemini_edit_image` + `input_image_path_1=<제품 cutout>` + `input_image_path_2=<로고 PNG>` + 프롬프트 명시 "place provided logo at bottom-left, do not redraw the logo glyph" |

> Method 3 는 Method 1 의 확장 — 로고가 텍스트로 들어가면 Gemini 가 글리프를 잘못 그릴 수 있어 input 으로 첨부 필요. 카드뉴스에서는 보통 시리즈 좌하단 로고 + Hook/CTA 1장에서 정확 배치 필요할 때 사용.

**호출 패턴** (5장 시안 예시):

```python
# 슬라이드 1 (Hook) — 제품 등장
mcp__nanobanana__gemini_edit_image(
    prompt="<공통 헤더 + Step 4 5요소 프롬프트>",
    input_image_path="01_brand/products/<메인 히어로>",
    output_path="07_carousel/<YYYY-MM-DD>_<캠페인-슬러그>/<브랜드>_<토픽>_instagram_conceptA-slide1-v1.png",
    aspect_ratio="4:5"
)

# 슬라이드 2 (본문 ①) — 일러스트만
mcp__nanobanana__gemini_generate_image(
    prompt="<공통 헤더 + Step 4 5요소>",
    output_path=".../<...>-slide2-v1.png",
    aspect_ratio="4:5"
)

# 슬라이드 3·4 (본문 ②·③) — 동일 패턴
# 슬라이드 5 (CTA) — 로고 등장 시 edit_image, 없으면 generate
```

**시각 일관성 강화**:
- 모든 호출에 동일 `[GLOBAL STYLE]` 헤더 박기
- 호출 후 N장 시각 비교 → 한 장만 톤 어긋나면 그 슬라이드 v2 재생성

**변형 디폴트 = 1세트 (N장)**. 사용자가 "v2~v3 시안 비교" 명시 시 conceptA·conceptB 로 시안 자체를 늘림 (같은 conceptA 5장을 N번 호출 ❌).

---

### Step 6: Save and Deliver (저장·보고)

**저장 경로**: `07_carousel/<YYYY-MM-DD>_<캠페인-슬러그>/` ★ (2026-05-25 도입)
- `<YYYY-MM-DD>` = 시안 **생성일** (오늘 날짜) · `<캠페인-슬러그>` = `04_brief/confirmed_brief.md` frontmatter `campaign:` 값 (분기 A) 또는 사용자 컨셉 자동 슬러그 (분기 B)
- 예: `07_carousel/2026-05-25_mybrand-summer-launch/`
- 폴더 없으면 호출 직전 `mkdir -p` 자동 생성

**파일명 규칙**:
- `{브랜드}_{토픽}_instagram_concept{ID}-slide{N}-v{N}.png`
- 예) `[브랜드명]_summer_instagram_conceptA-slide1-v1.png` ~ `slide5-v1.png`
- 같은 시안 변형 → v 증가 (덮어쓰기 ❌)
- 다른 시안 → conceptB / conceptC

**보고 포맷** (★ 사후 검수 정책 — v1 출력 직후 슬라이드 시나리오 채팅 동봉):

> "{토픽} 카드뉴스 5장 생성 완료 (골격: <①정보형/②스토리형/③리스트형>).
>
> 📝 슬라이드 시나리오
> - 1장 (Hook · 레이아웃 <H?>): "<...>"
> - 2장 (본문 ① · 레이아웃 <B?>): "<...>"
> - 3장 (본문 ② · 레이아웃 <B?>): "<...>"
> - 4장 (본문 ③ · 레이아웃 <B?>): "<...>"
> - 5장 (CTA · 레이아웃 <C?>): "<...>"
>
> 🎨 시각 일관성
> - 배경: <brand_brief § 4-1 슬롯>
> - 폰트: <§ 4-4 패밀리>
> - 시그니처 모티프: <소품 1개>
> - 스타일: <STYLE-GUIDE 매핑 슬롯 또는 'brand_brief 디폴트'>
>
> 출처: <페인 #N · USP #M · 경쟁사 행 K> (분기 B 만)
>
> 수정 요청 시 '3장 더 짧게' / '5장 저장 CTA로' / '골격 ③로 바꿔' / '슬라이드 2장만 v2' / '톤 더 부드럽게' 등으로 알려주세요. 변형은 v 증가하며 재생성합니다."

> ⚠️ confirmed_brief.md 디스크 저장 ❌ (분기 A 가 아니면). v2~ 반복은 in-memory 시나리오의 일부만 수정 후 호출.

---

## 변형 옵션 (사용자 요청 시만)

같은 토픽 v2~v5 = 다음 4축 중 1~2개 비틀어 **재작성** (같은 프롬프트 N번 ❌):

| 축 | 비틀기 예시 |
|---|---|
| 골격 | 정보형 ↔ 스토리형 ↔ 리스트형 |
| 스타일 | STYLE-GUIDE 다른 슬롯 |
| 슬라이드 수 | 3 / 5 / 7 / 10 |
| CTA 종류 | 저장 / 공유 / 댓글 / 프로필 / DM / 시리즈 |

---

## 호출 직전 체크리스트 (11항목)

```
□ 분기 판정 완료 (A: confirmed_brief.md 존재 / B: 부재 → Step 1.5 도출)
□ ★ brand_brief.md § 4-1 컬러 6슬롯 모두 채워짐
   (BG-Light / BG-Deep / BRAND-Signature / BRAND-Sub / TEXT-Primary / TEXT-Sub)
   — `[확인 필요]` 라벨 잔존 ❌. 슬롯 비면 호출 중단
□ 사용자 토픽 1줄 확정
□ 슬라이드 수·비율·플랫폼 확정 (디폴트 5장 / 4:5 / Instagram)
□ 분기 B: 골격 1개 (①/②/③) + 스타일 슬롯 (STYLE-GUIDE Quick Comparison 표 → 본문 풀 2단계)
□ ★ 선택한 스타일 슬롯 폴더 (`references/styles/{slot}/`) 의 reference 2~3장 시각 흡수 (Step 1.5-2 ③ · **5축**)
□ ★ PROP INVENTORY 축 작성 — reference 의 물리 오브젝트(클립·폴라로이드·테이프·종이 접힘 등) verbatim 리스트. [3] EFFECT 에 그대로 인용
□ ★ Reference-Literal Mode 검증 — reference 에 없는 마스트헤드/거대 헤드라인 임의 추가 ❌. 슬라이드 텍스트 점유 픽셀 비율 ≤ reference 비율
□ ★ H0 트리거 판정 — reference 에 prop 2개 이상 + 텍스트 점유 < 15% 면 H0 Mockup 모드 (H1~H5 매핑 건너뛰기)
□ ★ 자산 슬롯 매핑 — `01_brand/products/ASSET_GUIDE.md` 우선 인용. 없으면 SKILL 디폴트 3행 fallback
□ 시나리오 N장 in-memory 변수 (Hook + 본문 N-2 + CTA)
□ 자수 캡 검수 완료 (Hook ≤15자 / 본문 ≤30자×2 / CTA ≤12자)
□ CTA 슬라이드에 가격·% OFF·번들 직접 노출 ❌ (carousel-cta-library 6종 중 1개)
□ output_path = 07_carousel/<YYYY-MM-DD>_<캠페인-슬러그>/{파일명규칙}.png 절대경로
□ ★ 제품 등장 슬라이드는 무조건 Method 1 (`gemini_edit_image` + `input_image_path_1`).
   제품 묘사를 텍스트만으로 generate ❌
□ ★ [2] PRODUCT 어휘에 ASSET_GUIDE 의 jar-anchor (body/lid 색·라벨 글리프·formula anchor) 인용 박힘
□ ★ brand_brief.md § 4-4 제형 묘사는 텍스처 매크로 슬라이드만 인용.
   자(jar) 정면컷·라이프스타일 컷 prompt 에 인용 ❌ (인용 시 자 SHELL 까지 핑크 젤로 재드로잉됨)
```

---

## 디테일 회피 룰 (8줄)

- ❌ brand_brief.md § 4-1 6슬롯이 비어있는데 임의 HEX 추정 (호출 중단 후 `/01-brand-from-url` 안내)
- ❌ 시나리오 도출 없이 NanoBanana 바로 호출 (분기 B 는 Step 1.5 의무)
- ❌ 슬라이드별 다른 폰트·다른 배경 사용 (N장 시각 일관성 위반)
- ❌ CTA 슬라이드에 직접 가격·% OFF 시각 노출 (`banned-words.md § 2` 룰)
- ❌ Hook ≤15자 / 본문 ≤30자×2 캡 초과 (`text-density-caps.md` 자동 압축)
- ❌ 제품·로고 reference 없이 텍스트만으로 합성 (등장 시 input_image_path_1 의무)
- ❌ 같은 prompt 로 N장 호출 (슬라이드별 1메시지 룰 위반)
- ❌ 분기 B 에서 자동 도출한 시나리오를 confirmed_brief.md 로 디스크 저장 (사용자 명시 요청 시만 영구화)
- ❌ 제품 등장 슬라이드를 Method 2 (`gemini_generate_image`) 로 호출 (input 없이 텍스트 prompt 만으로) — 자(jar)·라벨 100% 재드로잉됨
- ❌ [2] PRODUCT 어휘에 jar-anchor (body/lid 색·라벨 글리프·formula anchor) 인용 누락 — Gemini 가 텍스트 prompt 의 제형 묘사를 자 SHELL 까지 적용해 투명/핑크 자로 재해석
- ❌ brand_brief § 4-4 제형 묘사를 자 정면컷·라이프스타일 컷 prompt 에 인용 (텍스처 매크로 슬라이드만 인용 허용)

---

## GPT 분기 (옵션)

사용자가 "GPT로", "gpt-image-1" 등을 명시 요청한 경우에만 GPT Image MCP 사용. 본 스킬의 § 핵심 원칙 5줄(컬러 팔레트 인용 포함)은 동일 적용 — 단 `image` 슬롯이 single binary 라 제품·로고 input 동시 첨부 ❌. 우선순위: 제품 컷 1장 binary + 로고는 prompt 에 절대경로 인용 + AS-IS directive.

---

## NanoBanana Unavailable Fallback

NanoBanana MCP 가 오류·미가용이면 즉시 사용자에게 보고:

> "NanoBanana MCP 호출 불가. 슬라이드 N장의 시나리오·프롬프트·스타일 디렉션을 카피·붙여넣기 가능한 형태로 정리해드릴까요? 다른 도구(Canva·Figma·외부 AI)로 수동 생성 가능합니다."

그 후 Step 4 의 슬라이드별 5요소 프롬프트 전체를 한국어·영문 묶음으로 전달.

---

## 다음 단계

카드뉴스 생성 완료 후:
> "(옵션) IG 캡션 본문·해시태그 작성을 도와드릴까요? 가격·할인은 캡션 본문에 (슬라이드 시각 영역에는 ❌)."
> "(옵션) 광고 소재로 전환하려면 `/05-ad-image-nanobanana` (단일 후킹 시안). 영상 변환은 `/06-ad-video-higgsfield`."
> "광고 집행 후 데이터가 모이면 `/06-meta-report` 로 성과 리포트를 만들 수 있습니다. (06 모듈은 추후 구축 예정)"

---
name: 05-ad-image-nanobanana
description: 01_brand(자사) + 02_competitor(경쟁사) + 03_customer(고객) 1페이지 분석을 통합 인풋으로 받아, `references/` 모듈(USP 4축 골격·앵글·금지어·자수 캡·CTA 라이브러리)로 USP 4축 (① User's Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion(+CTA)) 을 in-memory 도출 후 NanoBanana MCP (Gemini 기반) 로 광고 이미지(.png)를 생성해 `05_ad_image/{YYYY-MM-DD}_{캠페인-슬러그}/` 서브폴더에 저장하는 스킬. 사용자가 "이미지 만들어줘", "광고 제작해줘", "스토리보드 만들어줘", "광고 시안 짜줘", "/05-ad-image-nanobanana" 등으로 요청할 때 호출. **사전 컨펌 게이트 ❌** — v1 출력 직후 4축을 채팅에 동봉해 사용자가 사후 검수·v2 반복. 파워 유저가 `04_brief/confirmed_brief.md` 를 사전 작성한 경우만 § 3 4축 그대로 인용 (도출 단계 스킵). 비주얼은 brand_brief 6슬롯 + 트렌드 가이드 + 5요소 프롬프트로 조립.
---

# 05. 광고 이미지 생성 (NanoBanana → PNG)

> 이 스킬의 목표는 **01~03 분석 풀 디테일 → references 모듈 도출 → NanoBanana 프롬프트 → PNG + USP 4축 채팅 보고**.
> 카피·비주얼 시드는 references/ 5개 모듈 (`copy-4-axis-framework`, `message-angles`, `banned-words`, `copy-char-caps`, `cta-library`) 로 in-memory 도출. confirmed_brief.md 가 있으면 그 § 3 4축을 1순위로 인용 (도출 스킵). 비주얼은 `brand_brief.md` 6슬롯 + 2025 K-뷰티 트렌드 가이드 + 5요소 프롬프트(배경·제품·효과·텍스트효과·레이아웃) 로 조립.

## 호출 시점

- "이미지 만들어줘"
- "광고 제작해줘"
- "스토리보드 만들어줘" (04 deprecation 후 본 스킬이 흡수)
- "광고 시안 짜줘"
- "광고 소재 스토리보드 제작해줘"
- "/05-ad-image-nanobanana"
- 01~03 분석 3종이 모두 채워진 직후

## Prerequisites

**필수**:
- `.mcp.json` 에 `nanobanana` 서버 설정 — `mcp__nanobanana__gemini_edit_image` / `gemini_generate_image` 사용 가능 여부 확인
- `01_brand/brand_brief.md` § 4-1 컬러 6슬롯 채워짐 (없으면 → "`/01-brand-from-url <URL>` 로 컬러를 먼저 채워주세요" 안내 후 종료)
- `02_competitor/competitor_ads.md` (없으면 → "`/02-competitor-from-adlib <URL>` 로 경쟁사 분석을 먼저 해주세요" 안내 후 종료)
- `03_customer/pain_points.md` (없으면 → "`/03-pain-from-reviews <URL>` 로 고객 분석을 먼저 해주세요" 안내 후 종료)
- `01_brand/products/` 실재 제품컷 1장 이상

**선택**:
- `01_brand/logos/` 실재 로고 PNG (로고 배치 시)
- **`04_brief/confirmed_brief.md`** — 있으면 § 3 4축 (또는 § 2 메시지 + § 3 1차 4섹션) 그대로 인용, references 도출 단계 스킵 (분기 A). 없으면 references 로 자동 도출 (분기 B, 디폴트)

## Before You Start: Load Context

`01_brand/brand_brief.md` 1페이지를 읽고 다음을 추출한다 — 외부 브랜드 자료 ❌, refer/ 경로 ❌, OS_v1 외부 SOP 참조 ❌. 오직 `01_brand/` 만 사용:

- **보이스** (§ 톤·banned words) — 카피의 시각 효과 어휘 선택에 영향
- **비주얼** (§ 4-1 컬러 6슬롯·§ 4-2 사용 ❌ 컬러·§ 4-3 요소별 매핑·§ 4-4 폰트 패밀리) — 5요소 프롬프트의 BACKGROUND / TEXT EFFECT 에 그대로 인용
- **제품** (USP·가격·프로모션) — confirmed_brief § 3 4축의 데이터 라인과 정합 점검

> 특정 브랜드의 제품/카피/디자인 가이드를 본 스킬에 하드코딩하지 않는다. 모두 런타임에 `01_brand/brand_brief.md` 에서 동적 로드.

## 핵심 원칙 (5줄, 절대 위반 ❌)

✅ **제품 픽셀은 reference 그대로 합성** — 재그리기 / 리스타일 / "개선" ❌. 위치·크기·약간 회전·라이팅 블렌드만 허용
✅ **제품 등장 시 `gemini_edit_image` 의무** — `generate_image` 로 텍스트만으로 제품 그리기 ❌
✅ **제형도 reference 그대로** — AI 가 추정한 제형 묘사 ❌. reference 가 있으면 prompt 에 제형 색·텍스처 묘사 일체 ❌
✅ **로고도 reference 그대로** — `01_brand/logos/` 실재 PNG 첨부. 프롬프트 텍스트만으로 워드마크 합성 ❌
✅ **컬러는 brand_brief.md § 4-1 6슬롯 그대로 인용** — `BG-Light` / `BG-Deep` / `BRAND-Signature` / `BRAND-Sub` / `TEXT-Primary` / `TEXT-Sub` 슬롯 ID 매핑. AI 추정 HEX ❌. 슬롯 비어있으면 호출 중단

> **카피 도출 책임**: 분기 A (confirmed_brief.md 존재) 면 § 3 4축 (User's Pain Point · Solution · Creative Key Visual · Promotion) 그대로 인용. 분기 B (디폴트) 면 본 스킬의 Step 1.5 가 `references/` 5개 모듈로 in-memory 도출. v1 출력 시 채팅에 4축 동봉 → 사용자 사후 검수.

---

## Workflow (6 steps)

### Step 1: Gather Inputs (인풋 로드) + 분기 판정

먼저 `04_brief/confirmed_brief.md` 존재 여부를 확인해 분기:

- **분기 A — `confirmed_brief.md` 존재**: § 3 1차 4섹션 (User's Pain Point · Solution · Promotion · Creative Key Visual) 그대로 인용 (재해석 ❌). § 2 메시지 (= Solution 시드) 도 인용. **Step 1.5 (자동 도출) 스킵** → 바로 Step 2 로.
- **분기 B — `confirmed_brief.md` 부재 (디폴트)**: Step 1.5 "4축 자동 도출" 진입.

**brand_brief.md 에서 추출 (분기 무관 공통)**:
- **★ 컬러 팔레트** (§ 4-1): `BG-Light` · `BG-Deep` · `BRAND-Signature` · `BRAND-Sub` · `TEXT-Primary` · `TEXT-Sub` 의 HEX 6개
- **사용 ❌ 컬러** (§ 4-2)
- **요소별 매핑 표** (§ 4-3): 헤드라인·본문·CTA·뱃지의 슬롯 ID → HEX 매핑
- **폰트** (§ 4-4): 폰트 패밀리

**컬러 슬롯 점검** — 6슬롯이 모두 채워졌는지 호출 전 점검. `[확인 필요]` 라벨이 남아있거나 슬롯이 비어있으면 호출 중단:
> "brand_brief.md § 4-1 컬러 팔레트 슬롯 (`BG-Light` 등) 이 비어있습니다. `/01-brand-from-url <대표 상세페이지 URL>` 로 컬러를 먼저 채워주세요."

**분기 A 인풋 추출 (confirmed_brief.md 존재)**:
- **4축** (§ 3): ① User's Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion (CTA 흡수) — 그대로, 의역 ❌
- **무드** (§ 3 의 Creative Key Visual 텍스트에 포함된 무드 키워드 — 예: 절박·임상·시크릿·공감)
- **제품** (§ 3 Creative Key Visual 내 제품 묘사): `01_brand/products/` 의 reference 파일명 + 제형 묘사 텍스트
- **로고** (§ 3 Creative Key Visual 내 로고 슬롯): `01_brand/logos/` PNG 파일명 + 위치
- **포맷** (선택 — 없으면 디폴트 1:1)

---

### Step 1.4: Asset Discovery (★ 분기 무관 공통 — 파일명 무관 자산 분류)

> ⚠️ 학생마다 `01_brand/products/` 에 넣는 파일이 제각각 (영문·한글·`IMG_*.jpg` 등). 본 단계가 **파일명 → 콘텐츠 카테고리** 매핑을 호출 직전 자동 수행해 § 1.5-3 매트릭스가 룩업할 수 있는 in-memory 카탈로그를 만든다.

#### 1.4-1. 파일 전수 스캔

```bash
ls -R 01_brand/products/ 01_brand/logos/
```

서브폴더 구조·파일명 자유 (`main-angles/`·`studio/`·`lifestyle/` 같은 컨벤션은 권장이지 강제 ❌). `.png`·`.jpg`·`.jpeg`·`.heic`·`.webp` 모두 수용. `.DS_Store`·`.gitkeep` 제외.

#### 1.4-2. 1차 분류 — 파일명 힌트 매칭 (cheap, 토큰 ❌)

각 파일에 대해 파일명·서브폴더명 (대소문자·언더스코어·하이픈 무관) 에서 다음 정규 패턴을 매칭:

| 카테고리 | 파일명·서브폴더 힌트 (정규 패턴, 부분 매칭) |
|---|---|
| 단품 정면 풀샷 | `front`, `main`, `angle-?01`, `정면`, `메인` |
| 드로퍼·디테일·디스펜서 | `dropper`, `pump`, `detail`, `closeup`, `close-up`, `드로퍼`, `디테일` |
| 2제품 동시 (듀오) | `duo`, `pair`, `set-?2`, `2pcs`, `듀오`, `세트2` |
| 3+ 제품 라인업 | `lineup`, `line-?up`, `family`, `full(-?)set`, `라인업`, `풀세트`, `시리즈` |
| 제형 매크로 | `texture`, `formula`, `swatch`, `macro`, `제형`, `텍스처` |
| 라벨 매크로 | `label`, `라벨`, `label(-?)macro` |
| 라이프스타일·모델 | `lifestyle`, `model`, `lifestyle/` 서브폴더, `라이프스타일`, `모델` |

→ 매칭 성공 시 해당 파일을 카테고리에 등록 (1 파일 → 다중 카테고리 등록 가능, 예: `serum-front-label.png` 은 정면 풀샷 + 라벨).

#### 1.4-3. 2차 분류 — 비전 폴백 (1차 미매칭 파일에만)

1차에서 어떤 카테고리에도 매칭 안 된 파일은 `Read` (vision) 로 1장씩 열어 분류. 토큰 비용을 고려해 분류 프롬프트는 짧게:

> "이 사진은 다음 중 어느 카테고리인가? (1) 단품 정면 풀샷 (2) 드로퍼·디테일·디스펜서 클로즈업 (3) 2제품 동시 (4) 3+ 제품 라인업 (5) 제형 매크로 (6) 라벨 매크로 (7) 라이프스타일·모델 (8) 기타. 숫자만 답."

→ 분류 결과를 카테고리에 등록. **이미 1차에서 분류된 파일은 비전 호출 ❌** (토큰 절약).

#### 1.4-4. 카탈로그 점검 + 부재 처리

```
[카탈로그 예시 — in-memory 변수]
single_front:    [products/serum-main.jpg, products/our-product-front.png]
dropper_detail:  [products/dropper-zoom.heic]
duo_two_product: []                              ← 부재
lineup_three:    []                              ← 부재
formula_macro:   [products/IMG_4321.jpg]
label_macro:     [products/label-closeup.png]
lifestyle_model: [products/lifestyle/morning.jpg]
logos:           [logos/our-logo.png]
```

**부재 처리** (§ 1.5-3 의 룰 참조 — 다시 적시):

| 카테고리 | 부재 시 처리 |
|---|---|
| 단품 정면 풀샷 (필수) | **호출 중단** → "단품 정면 풀샷 (병/튜브 전체 + 라벨 식별 가능) 1장을 `01_brand/products/` 에 넣어주세요." |
| 라벨 매크로 | warning + `reference_images[0]` 슬롯 비우고 진행 → "라벨 매크로 컷 부재. 라벨 디테일 재해석 위험. 라벨 클로즈업 1장 추가 권장." |
| 듀오·라인업 (시안 요청 시 필요) | 해당 시안 스킵 + 고지 ("듀오 사진 부재 → Bundle 시안 생성 불가. 단품 시안만 생성합니다.") |
| 로고 | 슬롯 생략 OK (라벨에 워드마크 박혀있으면 충분) |

#### 1.4-5. 산출물

카탈로그는 **in-memory 변수** 로 다음 단계 (Step 1.5 도출 / Step 2 디렉션 / Step 5 호출) 가 룩업. 디스크 저장 ❌.

---

### Step 1.5: Derive 4-Axis (★ 분기 B 만, in-memory USP 4축 자동 도출)

> ⚠️ 분기 A (confirmed_brief.md 존재) 면 본 단계 전체 스킵.

#### 1.5-1. 인풋 로드 (섹션 지정 Read — 풀파일 ❌)

토큰 폭발 회피를 위해 각 파일에서 필요한 섹션만:

| 파일 | 추출 섹션 |
|------|----------|
| `01_brand/brand_brief.md` | § 4-1 컬러 6슬롯 + § 4-2 금지컬러 + § 4-4 폰트 + § USP 3개 + § 가격·번들·프로모션 + § Never 표현 |
| `03_customer/pain_points.md` | Top 5 페인 + Top 3 욕구 (리뷰 원문 ❌) |
| `02_competitor/competitor_ads.md` | 자주 쓰는 헤드라인 패턴 3개 · 경쟁사 빈틈 3개 (광고 풀텍스트 ❌) |

> ⚠️ **차별화 가드 (의무)**: 02 competitor 빈틈을 노려 차별 시안을 최소 ≥ 4장 확보. 경쟁사 헤드라인 어휘·앵글을 그대로 차용하지 말고 03 페인 + 자사 USP 기반으로 변주.

#### 1.5-2. references/ 5개 모듈 로드 + 4축 도출

```
references/copy-4-axis-framework.md   → 골격 A~E + DOMINANT 5앵글 적층 룰 + 4축 마스터 정의
references/message-angles.md          → 16개 앵글 풀
references/banned-words.md            → 자동 검수·치환 (한글 카피)
references/copy-char-caps.md          → 자수 캡 (Pain Point ≤15자 / Solution ≤26자 / Promotion ≤18자)
references/cta-library.md             → 호기심 유발형 CTA 5종 (Promotion 안의 CTA 풀바·버튼 — 직접 가격 ❌)
```

도출 순서:

1. **페인↔USP 매핑** — `pain_points.md` Top 5 페인 × `brand_brief.md` USP 3 → 매칭 강도 1위 페어 선택
2. **골격 선택** — 매칭된 페인 성격에 따라 골격 A~E 중 1개 (`copy-4-axis-framework.md § 1` 의 매핑 표 사용)
3. **1차 후보 6~9개 in-memory 생성** — 페인↔Solution·욕구↔Solution·경쟁사 빈틈↔차별 Solution 3축에서 각 2~3개
4. **최종 1개 압축** — 가장 강한 후보를 USP 4축 (① Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion(+CTA)) 으로 확정
5. **자동 검수·치환**:
   - `banned-words.md` — "비드" → "캡슐" 등 한글 카피 치환
   - `copy-char-caps.md` — 자수 캡 초과 시 토큰 단위 압축
   - **★ Promotion 강제 압축** (`copy-char-caps.md § 3-1`) — ④ 혜택 ≥ 3개면 우선순위 1~2개만 (가격 수치 ≫ 사은품 ≫ 시급성 ≫ 신뢰). 환불·배송·임상 안전 안내는 ④ Promotion 에서 분리 → ② Solution RTB 슬롯 또는 ③ Creative Key Visual 인증 뱃지로 이동. 02 경쟁사 평균 자수 8~13자 기준
   - **★ 텍스트 중복 검수** (`copy-char-caps.md § 4`) — 한 시안 안에 같은 핵심 단어·숫자 (`-20%` / `1+1` / `농가` / `23%` 등) **최대 2회, 권장 1회**. 헤드 + USP 뱃지 + ④ 박스에 같은 키워드 3회 등장 ❌. 검수 시 발견되면 영역별 정보 차원으로 분리 (① 페인 / ② 약속+RTB / ③ 큰 숫자 1포인트 / ③ USP 뱃지 다른 USP / ④ 혜택 명사 / ④ CTA 동사)
   - **★ 할인율 부호 표기** (`copy-char-caps.md § 4-4`) — `-N%` → `N%` 또는 `N% OFF` 자동 치환. K-뷰티 광고 표준 (02 경쟁사 4사 모두 `-` 부호 사용 ❌)
   - `cta-library.md` — ④ Promotion 안의 CTA 풀바를 호기심 유발형 5종 중 1개로 (직접 가격·% OFF ❌)
6. **결과는 in-memory 변수 (디스크 저장 ❌)** — NanoBanana 프롬프트 [4] TEXT EFFECT 블록 큰따옴표 인용으로 직행. v1 보고 시 채팅에 동봉.

#### 1.5-3. 자산 슬롯 매핑 (통일 순서 — Step 5 파라미터와 동일)

> ⚠️ **파일명 종속 ❌**: 학생마다 `01_brand/products/` 에 넣는 파일명이 제각각 (영문·한글·`IMG_4321.jpg` 등). 본 매트릭스는 **콘텐츠 카테고리** (사진이 어떤 컷인지) 만 명시. 파일명 → 카테고리 매핑은 **Step 1.4 Asset Discovery** 가 수행.

**기본 슬롯 순서** (모든 시안 공통):

| 슬롯 | 콘텐츠 카테고리 | 설명 |
|------|------|------|
| `image_path` (메인) | 시안 컨셉에 맞는 메인 컷 | 의무. 시안 카테고리 매트릭스 참조 (아래) |
| `reference_images[0]` | **라벨 매크로** (라벨만 크게 — 브랜드 워드마크·서브 카피 식별 가능) | **★ 의무 — 라벨 디테일 lock 용. 매번 첨부**. 부재 시 Gemini 가 라벨 비율·폰트·로고 타이포를 매번 재해석함. Asset Discovery 가 "라벨 매크로 없음" 판정 시 warning + 슬롯 비우고 진행 |
| `reference_images[1]` | 시안 컨셉별 보조 컷 (콘텐츠 카테고리 매트릭스 참조) | 옵션 |
| `reference_images[2]` | 로고 PNG | 로고 별도 배치 시 (라벨에 이미 워드마크 박혀있으면 생략 OK) |

**시안 컨셉별 콘텐츠 카테고리 매트릭스** (어느 카테고리 컷을 메인으로 박을지 — 파일명 무관):

| 시안 컨셉 | `image_path` 카테고리 | `reference_images[1]` 보조 카테고리 |
|---|---|---|
| Hero / Discount / Proof / Review / Scarcity / Ingredient (단일 제품 후킹) | **단품 정면 풀샷** | — |
| BeforeAfter / 한 방울 / 흡수 신 (디테일·드로퍼·디스펜서 후킹) | **드로퍼·디테일·디스펜서 클로즈업** | 단품 정면 풀샷 (병 전체 형태 참조) |
| Bundle (듀오 = 2제품 세트) | **2제품 동시 촬영 컷** (세럼+로션, 본품+증정 등) | 단품 정면 풀샷 (단품 형태 참조) |
| 풀세트 (3+ 제품 라인업) | **3+ 제품 라인업 컷** | — |
| 텍스처 / 제형 후킹 | 드로퍼·디테일·디스펜서 클로즈업 | **제형 매크로** (질감·점도·색 확인 가능한 클로즈업) |
| 라벨 매크로 (성분·인증 강조) | **라벨 매크로** | 단품 정면 풀샷 (병 전체 형태 참조) |

**콘텐츠 카테고리 정의** (Asset Discovery 가 분류할 때 기준):

- **단품 정면 풀샷** — 제품 1개, 병/튜브/박스 전체 가시, 라벨 식별 가능, 정면 또는 정면에 가까운 각도, 누끼 ❌
- **드로퍼·디테일·디스펜서 클로즈업** — 제품 일부 (드로퍼·펌프·노즐·라벨 일부) 가 크게 잡힘, 손·물방울 동반 가능
- **2제품 동시 촬영 컷** — 같은 프레임에 제품 2개 (듀오·세트·본품+증정)
- **3+ 제품 라인업 컷** — 같은 프레임에 제품 3개 이상 (풀라인업·시리즈 컷)
- **제형 매크로** — 액체·크림·젤 등 내용물 텍스처가 크게 잡힘 (제품 패키지 부재 또는 매우 일부)
- **라벨 매크로** — 라벨만 크게, 브랜드 워드마크·제품명·서브 카피·인증 마크 식별 가능
- **라이프스타일·모델** — 모델·손·환경(욕실·책상·여행) 과 함께 (현재 매트릭스에서는 보조용, 메인 카테고리 ❌)

> ⚠️ **카테고리-매핑 룰**: `image_path` 를 모든 시안에 단품 정면 풀샷 1장으로 채우면 듀오·풀세트·드로퍼 디테일 시안에서 AI 가 부재 부분을 텍스트로만 그려서 실재 패키지와 다른 결과가 나옴. 호출 직전 Step 1.4 Asset Discovery 결과를 본 매트릭스에 매핑할 의무.

> ⚠️ **카테고리 부재 처리**: Asset Discovery 결과 필요 카테고리가 부재 시:
> - **단품 정면 풀샷 부재 (필수)** → 호출 중단. "단품 정면 풀샷 (병/튜브 전체 + 라벨 식별 가능) 1장을 `01_brand/products/` 에 넣어주세요."
> - **라벨 매크로 부재** → `reference_images[0]` 슬롯 비우고 warning ("라벨 매크로 컷이 없어 라벨 디테일 재해석 위험. `01_brand/products/` 에 라벨 클로즈업 1장 추가 권장.")
> - **듀오 컷 부재 + Bundle 시안 요청** → Bundle 시안 스킵 고지. "듀오 사진이 없어 Bundle 시안은 생성 불가. 단품 시안만 생성합니다."
> - **라인업 컷 부재 + 풀세트 시안 요청** → 풀세트 시안 스킵 고지 (동일)

---

### Step 2: Build the Creative Direction (Layer 1~4)

크리에이티브 디렉션은 4 레이어로 쌓는다. 앞 레이어가 우선순위가 높다. **Layer 1 > 2 > 3 > 4**.

#### Layer 1: USP 4축 (1차 소스)

분기에 따라 인풋 소스가 다르다:

**분기 A (confirmed_brief.md 존재)** — § 3 4섹션 그대로 인용:
- **① User's Pain Point** — 헤드라인 카피 (재해석 ❌)
- **② Solution** — USP 약속 + RTB (임상·1위·인증) 한 줄 (재해석 ❌)
- **③ Creative Key Visual** — 비주얼 시드: 룩앤필 무드 + 컬러 팔레트 방향 + 제품 reference 묘사 + 뱃지 위치 + 타이포 방향
- **④ Promotion (+ CTA)** — 혜택·할인·증정 카피 + 호기심 CTA 1개 (재해석 ❌)

**분기 B (디폴트, Step 1.5 도출 결과 사용)**:
- **① User's Pain Point** — Step 1.5 in-memory 변수
- **② Solution** — Step 1.5 in-memory 변수
- **③ Creative Key Visual** — pain_points 페인 톤 + brand_brief Never 표현 회피 + brand_brief § 4-1 시그니처 슬롯 + `01_brand/products/` 메인 히어로 + 제형 매크로 (있으면) + brand_brief § 4-4 폰트
- **④ Promotion (+ CTA)** — Step 1.5 in-memory 변수
- **감정적 트리거** — 골격 A/B/C/D/E 에 따라 호기심·긴급성·소속감·FOMO·열망·편안함 중 매칭

#### Layer 2: Reference Image (시각 강화, 옵션)

사용자가 reference 이미지를 첨부했으면 `Read` 로 열어 시각 속성 추출:

- **컬러 팔레트와 온도** — 지배색·강조색·웜/쿨/뉴트럴
- **라이팅 품질** — 소프트 디퓨즈드 / 드라마틱 / 브라이트 / 무디
- **구도 접근법** — 요소 배치·여백·포컬 포인트
- **타이포 위계** — 사이즈 대비·웨이트 대비
- **무드와 에너지** — 차분·볼드·럭셔리·플레이풀·긴급
- **텍스처와 마감** — 매트·글로시·그레인·클린·미니멀

이 속성들은 Layer 1 의 디렉션을 시각적으로 강화한다. brief 가 명시적인 부분은 brief 가 우선. brief 가 비어있는 부분만 reference 가 채운다. 결과물은 reference 의 재현이 아니라 **브랜드 정체성을 통과한 오리지널 디자인**.

reference 가 없으면 이 레이어는 스킵.

#### Layer 3: 2025 K-뷰티 디자인 트렌드 (필수 참고)

##### 트렌디한 레이아웃 패턴

| 패턴 | 설명 | 적합한 상황 |
|------|------|------------|
| **모델+제품 분할** | 좌측 모델, 우측 제품+정보 (또는 반대) | 신제품, 프로모션 |
| **모델 오버레이** | 모델이 제품을 들고, 텍스트가 주변에 자연스럽게 배치 | 브랜드 캠페인 |
| **제품 히어로** | 제품 중앙, 원재료/텍스처 소품과 함께 플로팅 | 성분 강조 |
| **비포애프터 분할** | 좌/우 또는 상/하 분할 | 임상·결과 소구 |
| **텍스처 매크로** | 제형 클로즈업 | 제형 후킹 시안 |

##### 트렌디한 타이포그래피

- **헤드라인**: 굵고 임팩트 있는 고딕체, 한글+영문 믹스
- **핵심 단어 컬러 강조**: brand_brief § 4-1 `BRAND-Signature` 1슬롯만 (시안 1장 = 1포인트)
- **말풍선/스티커 캘아웃**: 손글씨 스타일 "Pick!", "추천" 등
- **가격**: 정가 작게 취소선 + 할인가 크고 볼드하게

##### 트렌디한 컬러 (brand_brief § 4-1 우선)

- **배경**: brand_brief 6슬롯 기반 소프트 그라데이션 (2컬러, 단순하게)
- **피해야 할 것**: 과채도, 네온, 복잡한 그라데이션
- **시그니처 강조**: `BRAND-Signature` 솔리드 또는 `BRAND-Signature` → `BRAND-Sub` 그라데이션

##### 트렌디한 그래픽 요소

- **뱃지**: 라운드 필 뱃지 (NEW, GIFT), 리본 배너 (단독, 한정)
- **효과**: ✨ 스파클 (글로우 제품), 💧 수분 (보습), 부드러운 그림자
- **소품**: 원재료 (성분에 맞춰), 텍스처 스워치
- **피해야 할 것**: 과도한 3D 효과, 무거운 드롭쉐도우, 빽빽한 레이아웃

##### 피해야 할 촌스러운 패턴

| ❌ 피하기 | ✅ 대신 사용 |
|----------|------------|
| 과도한 3D 텍스트 | 플랫하고 볼드한 타이포 |
| 무거운 드롭쉐도우 | 부드러운 박스쉐도우 또는 없음 |
| 복잡한 그라데이션 | 단순한 2컬러 소프트 그라데이션 |
| 과채도/네온 컬러 | 소프트 파스텔, 뮤트 톤 |
| 빽빽한 텍스트 | 충분한 여백과 계층 구조 |
| 정적인 정중앙 배치 | 다이나믹한 앵글과 비대칭 |

#### Layer 4: 캠페인 타입별 스타일 매핑

`brand_brief.md` 의 비주얼 가이드를 1순위로 적용. 캠페인 타입별 스타일 권장:

| 캠페인 타입 | 권장 스타일 디렉션 | 이유 |
|---|---|---|
| 신제품 런칭 | 모델+제품 분할 + NEW 뱃지 | 제품 중심, 신제품 강조 |
| 할인/특가 프로모션 | 큰 % OFF + 가격 대비 강조 | 직접 반응 유도 |
| 단독/한정 기획 | "ONLY" 뱃지 + 한정 느낌 | 희소성 강조 |
| 베스트셀러 소구 | 판매량/리뷰 숫자 강조 | 사회적 증거 |
| 증정 이벤트 | +GIFT 뱃지 + 증정품 플로팅 | 추가 가치 |
| 임상/결과 소구 | 비포애프터 분할 + 수치 뱃지 | 신뢰 구축 |

> **★ 6종 변형 동시 생성 시 레이아웃 다양화 의무 (2026-05-25)** — 같은 캠페인의 6 앵글을 한 폴더에 동시 생성할 때 (04 § Step 4 흐름) **시각 시그니처는 유지하되 레이아웃·구도·제품 위치는 6장 모두 다르게** 강제. K-뷰티 실전 (경쟁사 A·B·C) 표준 — 시그니처는 일관 (브랜드 인지), 레이아웃은 변주 (피드 피로도 ↓).
>
> **유지 (6장 공통)**: 컬러 6슬롯 · ④ Promotion 박스 색 (`BRAND-Signature` 솔리드) · 폰트 페어링 (Noto Serif 헤드 + Pretendard 본문) · 한글 카피 자수 캡
>
> **변주 (6장 각자 다르게)**: 제품 위치 (우측 사선 / 우상단 코너 / 하단 띠 / 인서트 등) · 헤드라인 위치 (좌상단 / 상단 풀폭 / 인용 박스) · ④ 박스 위치 (우하단 / 하단 풀폭 띠 / 우상단) · 메인 시각 요소 (제품 / 거대 숫자 / 분할 얼굴 / 원물 매크로 / 3대 숫자 스택 등)
>
> **★ 미니멀 디폴트 룰** — 시각 영역 정보 밀도 = LOW. 한 시안에 텍스트 요소 ≤5개. **4종 인증 뱃지 좌하단 2×2 그리드는 디폴트 ❌** — 뱃지로 가득 채우면 정보 과부하로 광채·제품이 묻힘. 깔끔 우선:
> - **디폴트 (인증 가시화 ❌)**: Hero·A·B·C → **USP 강조 뱃지 1개만** (예: "23% 농축", "임산부 가능" 같은 1포인트). 인증 라벨 5C7A3D 그린 뱃지 좌하단 2×2 그리드 ❌
> - **신뢰 캠페인 (인증 가시화 ✅)**: D·E·F → 1~2개만 선택 노출. 전체 4종 ❌. 캠페인 정합 1~2개
> - **사용자가 "4종 풀세트 노출" 명시 요청 시만** 4종 풀세트 (2×2 또는 가로 1줄)
>
> **레이아웃 패턴 룩업 표** (04 § Step 4 와 동일):
>
> | 앵글 | 레이아웃 패턴 |
> |---|---|
> | A 할인 | BIG % OFF 풀블리드 — 거대 `-N%` 중앙, 제품 코너 작게 |
> | B 성분 | 원물 매크로 풀블리드 — 원재료가 화면 절반+, 제품 우측 인서트 |
> | C 번들 | 2제품 가로 split — 좌 50% 단품 / 우 50% 세트 |
> | D 사회증거 | 3대 숫자 풀스택 — 세로 3분할, 제품 하단 띠 |
> | E 비포애프터 | 얼굴 좌우 분할 풀블리드 — 얼굴 50-60%, 제품 하단 작게 |
> | F 리뷰형 | 모델+제품 split — 좌 UGC 모델 / 우 제품+별점+인용 |
>
> 단발 변형 (5변형 비틀기) 은 본 룰 적용 ❌ — 같은 앵글의 변주만이라 시그니처+레이아웃 모두 유지하고 5축 (시각 각도·무드·구도·컬러 온도·프레이밍) 만 비틈.

#### 레이어 우선순위 요약

Step 4 의 프롬프트는 모든 레이어를 반영하되 다음 순서로 가중:

1. **Layer 1 (USP 4축)** — 토대. 명시 지시는 절대 오버라이드 ❌
2. **Layer 2 (Reference Image)** — Layer 1 이 비운 시각 디테일을 채움
3. **Layer 3 (트렌드 가이드)** — 전략적 깊이·구도 원칙
4. **Layer 4 (캠페인 스타일 매핑)** — brand_brief 가 1순위, 본 표는 fallback

### Step 3: Determine Format and Ratio

`references/ad-format-specs.md` 에 플랫폼·플레이스먼트별 정확한 사양표가 있다. 분기 A 면 `confirmed_brief.md § 6` 값이 1순위, 분기 B 면 사용자 지정 또는 Quick defaults.

> **★ 디폴트 aspect_ratio = `1:1` (1080×1080)**. 사용자가 *"4:5 세로"*, *"9:16 스토리"*, *"포트레이트"* 등으로 **명시 요청 시에만** 다른 비율 사용. 메인 컷·인스타 피드 표준이 1:1 이고, 캐러셀·구글 디스플레이 스퀘어와도 호환성 최고. confirmed_brief.md § 6 이 비어있거나 사용자 지정이 없으면 **무조건 1:1**. 모델 측면·매거진 구도라고 4:5 자동 선택 ❌.

Quick defaults:

| Platform | Placement | Aspect Ratio | Dimensions |
|---|---|---|---|
| **Meta (FB/IG)** | **Feed ad (디폴트 ★)** | **1:1** | **1080x1080** |
| Meta (FB/IG) | Feed ad (portrait — 명시 시만) | 4:5 | 1080x1350 |
| Meta (FB/IG) | Story/Reel ad (명시 시만) | 9:16 | 1080x1920 |
| Meta (FB/IG) | Carousel ad | 1:1 | 1080x1080 per slide |
| Google Display | Landscape banner | 16:9 | 1200x628 |
| Google Display | Square | 1:1 | 1200x1200 |
| Pinterest | Promoted pin | 2:3 | 1000x1500 |
| TikTok | In-feed ad | 9:16 | 1080x1920 |
| Email | Promo banner | 3:2 | 1200x800 |

다중 포맷 요청 시 각 포맷별로 별도 호출 (한 이미지를 크롭해서 우기지 않는다).

### Step 4: Build the Prompt (5요소 프롬프트)

NanoBanana 공식 가이드(Gemini API 이미지 생성 문서) 의 권장 어휘 — **장면·주체·환경·라이팅·구도·스타일** — 을 따라 단일 영문 프롬프트로 합성한다. 한글 카피는 큰따옴표로 그대로 보존.

```
[1] BACKGROUND — brand_brief § 4-1 컬러 팔레트 슬롯에서 인용. 다음 4옵션 중 무드에 맞는 1개 선택
   ─ 옵션 A (디폴트): `BG-Light` 솔리드 또는 `BG-Light` → `#FFFFFF` 2컬러 소프트 그라데이션
       예) "soft 2-color gradient from #<BG-Light HEX> to #FFFFFF"
   ─ 옵션 B: 제품 제형 매크로 텍스처를 배경으로 확장 (제형 후킹 시안)
       예) "liquid gel surface, water droplets and soft gloss highlights
            around (NOT on) the product, gradient #<BG-Light> → #<BG-Deep>"
   ─ 옵션 C: `BRAND-Signature` 솔리드 단색 (퍼포먼스·결정 압박 시안)
       예) "solid #<BRAND-Signature HEX> background, clean and minimal"
   ─ 옵션 D: 존(zone) 분할 — 헤드 띠 `BRAND-Signature` / 본문 `BG-Light` / 푸터 `BG-Deep`
       (절박 톤·복합 정보 레이아웃에 적합)

[2] PRODUCT — image_path + reference_images[0] (라벨 매크로) AS-IS 합성
   "Use image_path AS-IS for the main product silhouette and reference_images[0]
    AS-IS for the label detail. Composite the actual reference pixels into
    the layout. DO NOT redraw, repaint, regenerate, or restyle the product
    or its formula.

    ★ LABEL LOCK (강제):
    - Label text reads exactly '<brand_brief.md § 한 줄 정의 의 브랜드명>' as printed
      on reference. Sub-text reads exactly as on reference (e.g., '<제품 라인명
      from brand_brief 가격표>'). DO NOT alter label proportions, fonts, layout,
      color blocking, or wordmark typography. Label position, scale, and rotation
      on the bottle must match reference within 5%.
    - Cap color, collar color, dropper shape: exactly from reference. DO NOT
      swap cap material (no chrome/gold cap if reference is matte black, no
      all-beige cap if reference is black+cream-collar, etc.).
    - Bottle silhouette (height/width ratio, base thickness, neck length):
      exactly from reference.
    - Bundle/세트 시안의 보조 제품(로션·마스크·클렌징 등)은
      reference_images[1] 의 패키지 형태·라벨을 그대로 인용. 부재 시 텍스트로
      그리지 말고 호출 중단.

    Allowed: position on canvas, scale, slight rotation (≤15°), lighting blend
    with new background. The jar/cap/label/formula must be visually
    indistinguishable from reference."
   ⚠️ reference 가 있을 때 prompt 에 제형 색·텍스처 묘사 일체 ❌
   (분기 A 면 confirmed_brief § 3 Creative Key Visual 제형 묘사 인용. 분기 B 면 reference 만 박고 묘사 ❌)

[3] EFFECT — 광고 컨셉을 살리는 부가 요소·소품·모델 (생성 OK)
   • 원재료·텍스처 스워치·물방울·스파클·후광·연기·꽃잎·실리콘 비드 등
   • 모델 등장 시 손/제스처/실루엣 위주 (얼굴 디테일은 요청 시만)
   • 효과는 무드 키워드에 종속 — 분기 A: confirmed_brief § 3 Creative Key Visual / 분기 B: Step 1.5 도출 무드
   예) "soft sparkle particles around the product, fresh dew droplets
        on the jar surface, model's hand gently holding the jar"

[4] TEXT EFFECT — 카피의 시각 효과 (1~2개 선택)
   ★ 컬러는 brand_brief § 4-3 요소별 매핑 표 그대로 인용 (슬롯 ID → HEX)
   ★ 카피 텍스트 자체는 USP 4축 그대로 큰따옴표로 박는다 (재해석 ❌)
       — 분기 A: confirmed_brief § 3 4섹션 인용
       — 분기 B: Step 1.5 in-memory 4축 변수 인용 (검수·치환 완료된 최종본)
   • stroke: "white text with #<BRAND-Signature HEX> stroke outline, 4px"
   • drop shadow: "subtle drop shadow bottom-right, 4px / 30% opacity"
   • rounded box: "rounded rectangle background #<BRAND-Sub HEX>, 12px radius"
   • highlight bar: "horizontal highlight bar behind text, #<BRAND-Sub HEX>
                     semi-transparent (40%)"
   • glow halo: "soft 4px diffusion glow, NOT neon"
   • strikethrough (정가): "strikethrough line, smaller, 60% opacity"
   • 폰트: brand_brief § 4-4 폰트 패밀리 그대로 (예: Pretendard ExtraBold)
   • 핵심 키워드 1포인트 컬러 = `BRAND-Signature` 1슬롯만 (시안 1장 = 1포인트)
   • 본문 텍스트 = `TEXT-Primary` / 라벨·캡션 = `TEXT-Sub` / 어두운 BG 위 = `#FFFFFF`

[5] LAYOUT — 컨셉을 잘 드러내는 창의적 구도
   • 모델+제품 분할 / 제품 히어로 / 텍스처 매크로 / 비포애프터 분할 /
     캐러셀 시퀀스 등 — 스토리보드 컨셉 그대로
   • 비대칭 구도, 충분한 여백, 정보 계층 (① Pain Point → ② Solution → ④ Promotion)
   • 로고 위치는 confirmed_brief § 3 Creative Key Visual 그대로 (좌상단 / 우상단 / Promotion 박스 중 1)
   • Promotion 박스 = `BRAND-Signature` 솔리드 + 화이트 텍스트 (CTA 풀바·버튼 흡수) / 뱃지 = `BRAND-Sub`

[PROMOTION / DATA] — ④ Promotion 그대로 (분기 A: confirmed_brief § 3 / 분기 B: Step 1.5 도출)
   가격·1+1·할인율·임상 수치·뱃지 (출처 표기) + CTA 버튼 (호기심 유발형 1개)
   배경 박스는 `BRAND-Signature` 솔리드, 텍스트는 화이트 권장
   ⚠️ 시각 영역 CTA 풀바·버튼은 직접 가격·% OFF ❌ (`references/cta-library.md` 호기심 유발형 5종)

[NEGATIVE]
   no fictional product, no redrawn product or formula, no fabricated
   label text, no chrome 3D text, no heavy drop shadows, no over-saturated
   neon, no clip-art starbursts, no 80s starburst badges, no thick black
   outline text, no plastic over-glossy fake highlights,
   no fish-shaped beads, no teardrop beads, no pearls, no glitter,
   no homogeneous opaque mass (when reference is translucent),
   no syringe/pill/pharmaceutical imagery,
   no warped fingers/teeth/eyes (if model present)

[CLOSING]
   Make it feel like a premium <카테고리> ad that stops the scroll
   while staying <confirmed_brief § 3 Creative Key Visual 무드 키워드 2~3개>.
   Editorial-grade composition, magazine-quality lighting,
   2025 Korean beauty ad aesthetic.
```

> ⚠️ AI 가 추정한 카피·HEX·제형 묘사 ❌. 분기 A 는 confirmed_brief.md, 분기 B 는 Step 1.5 도출본 + brand_brief.md 토큰을 그대로 인용해 채운다.

### Step 5: Generate the Image (도구 호출)

**도구 분기**:
- 제품 등장 → `mcp__nanobanana__gemini_edit_image` **의무**
- 제품 미등장 (추상 비주얼만) → `mcp__nanobanana__gemini_generate_image` 허용

**파라미터**:
- `image_path` = Step 1.4 카탈로그에서 시안 컨셉에 맞는 카테고리 첫 파일 (절대경로, 누끼 PNG ❌. § 1.5-3 카테고리 매트릭스 참조)
- `reference_images` (통일 순서 — § 1.5-3 표와 동일, Step 1.4 카탈로그 룩업):
  - `[0]` 라벨 매크로 카테고리 첫 파일 ★ **의무 — 부재 시 슬롯 비우고 warning** (라벨 디테일 lock)
  - `[1]` 시안 컨셉별 보조 카테고리 첫 파일 (단품 정면 풀샷 / 듀오 / 라인업 / 제형 매크로 중 매트릭스가 지정)
  - `[2]` 로고 카테고리 첫 파일 (있을 때만)
- `output_path`: `05_ad_image/{YYYY-MM-DD}_{캠페인-슬러그}/{파일명}` 절대경로 (메모리 룰 — 항상 명시). 서브폴더 없으면 호출 직전 `mkdir -p` 로 자동 생성
- `aspect_ratio`: **디폴트 `1:1`**. 분기 A 의 confirmed_brief § 6 값 또는 사용자 명시 요청 시에만 변경. 모델 측면·매거진 구도라고 임의로 4:5 ❌

**변형 디폴트 = 1장**. 사용자가 "5변형 만들어줘" / "v2~v5 까지" 등 명시할 때만 5축 비틀어 재작성 (같은 프롬프트 5번 ❌).

**캐러셀 다중 슬라이드** 요청 시 슬라이드 1장 = 호출 1회. 시안 일관성을 위해 라이팅·컬러 트리트먼트·타이포 스타일을 슬라이드 간 통일.

### Step 6: Save and Deliver (저장·보고)

**저장 경로**: `Claudecode_MarketingOS_student/05_ad_image/{YYYY-MM-DD}_{캠페인-슬러그}/` ★ (2026-05-25 도입)
- 서브폴더가 없으면 호출 직전 자동 생성 (`mkdir -p`)
- `{YYYY-MM-DD}` = 시안 **생성일** (오늘 날짜). 같은 캠페인 재생산 (며칠 후) 이면 새 서브폴더로 자연 분리
- `{캠페인-슬러그}` = `04_brief/confirmed_brief.md` frontmatter `campaign:` 값 그대로 (분기 A). 분기 B 면 사용자 컨셉 한 줄에서 영소문자+하이픈으로 자동 슬러그
- v2~ 수정 요청은 **같은 서브폴더 안에서 v 증가** (날짜는 v1 생성일 그대로)

**★ thumb 파일 자동 정리** — NanoBanana MCP 가 본 PNG 옆에 `*_thumb.jpeg` 를 자동 생성한다. 저장 직후 해당 서브폴더의 thumb 파일을 일괄 삭제:

```bash
rm -f 05_ad_image/{YYYY-MM-DD}_{캠페인-슬러그}/*_thumb.jpeg
```

캐러셀·랜딩페이지 폴더 (`07_carousel/{YYYY-MM-DD}_{캠페인-슬러그}/`, `08_landing/{YYYY-MM-DD}_{토픽}/images/`) 도 동일 룰 적용. 본 정리는 v1 호출 후·v2 호출 후 매번 실행.

**파일명 규칙** (CLAUDE.md § 5):
- 싱글: `{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-v{N}.png`
  - 예) `05_ad_image/2026-05-25_mybrand-summer-launch/mybrand_summer-launch_meta-feed_conceptHero-v1.png`
- 캐러셀: `{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-slide{N}-v{N}.png`
- 같은 시안 수정 → v 증가 (덮어쓰기 ❌)
- 다른 시안 → conceptB / conceptC

**보고**: 생성된 경로 + 사용된 5요소 1줄 요약 + **★ USP 4축 동봉** (★ 사후 검수 정책). 사용자가 v1 보고 결과를 보고 자연 반복.

분기 무관 보고 형식:

> "{파일명} 생성 완료.
>
> 📝 사용된 USP 4축
> - ① User's Pain Point   : "<...>"
> - ② Solution            : "<USP 약속 + RTB 한 줄>"
> - ③ Creative Key Visual : "<비주얼 1줄 묘사 — 제품·구도·인증 뱃지>"
> - ④ Promotion (+ CTA)   : "<혜택 + 시급성> / CTA: <호기심 유발형 1개>"
>
> 기반 골격: <A~E 중 1개> / 출처: <페인 #N · USP #M · 경쟁사 행 K> (분기 B 만)
>
> 수정 요청 시 '① 더 짧게' / '④ 1+1으로' / '골격 D로 바꿔' / '③ 비주얼 더 어둡게' 등으로 알려주세요. 변형은 v 증가하며 재생성합니다."

> ⚠️ confirmed_brief.md 디스크 저장 ❌ (분기 A 가 아니면). v2~ 반복은 in-memory 4축의 일부만 수정 후 호출 → 디스크 영구화는 사용자가 명시 요청한 경우만.

---

## 변형 옵션 (사용자 요청 시만)

같은 시안 5변형 = 5축 중 1~2개 비틀어 **재작성** (같은 프롬프트 5번 ❌):

| 축 | 비틀기 예시 |
|---|---|
| 시각 각도 | 오버헤드 / 아이레벨 / 클로즈업 / 와이드 / 45° |
| 무드 | 따뜻 / 활기 / 드라마틱 / 에디토리얼 / 퍼포먼스 |
| 구도 | 중앙 / 황금분할 / 비대칭 / 풀블리드 / 분할 |
| 컬러 온도 | 브랜드 팔레트 내에서 따뜻 / 차갑게 |
| 프레이밍 | 타이트 / 인-컨텍스트 / 라이프스타일 / 텍스처 매크로 |

---

## 호출 직전 체크리스트 (13항목)

```
□ 분기 판정 완료 (A: confirmed_brief.md 존재 / B: 부재 → Step 1.5 도출)
□ USP 4축 in-memory 변수 또는 confirmed_brief § 3 4섹션 추출 완료
   (① User's Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion+CTA)
□ ★ brand_brief.md § 4-1 컬러 팔레트 6슬롯 모두 채워짐
   (BG-Light / BG-Deep / BRAND-Signature / BRAND-Sub / TEXT-Primary / TEXT-Sub)
   — `[확인 필요]` 라벨 잔존 ❌. 슬롯 비면 호출 중단
□ ★ Step 1.4 Asset Discovery 완료 — `01_brand/products/` 전수 스캔 + 파일명 힌트
   1차 분류 + 비전 폴백 2차 분류 + 부재 카테고리 처리 완료 (in-memory 카탈로그 확보)
□ ★ image_path = 카탈로그에서 시안 컨셉 카테고리 첫 파일 (§ 1.5-3 매트릭스 —
   단일 후킹이면 단품 정면 풀샷, BeforeAfter 면 드로퍼 클로즈업, Bundle 이면
   2제품 동시 컷, 풀세트면 3+ 라인업 컷). 모든 시안에 정면 풀샷 1장 ❌
□ ★ reference_images[0] = 라벨 매크로 카테고리 첫 파일 — 라벨 디테일 lock.
   부재 시 슬롯 비우고 warning 출력 (Gemini 가 라벨 재해석 위험)
□ ★ Bundle / 풀세트 / 듀오 시안이면 reference_images[1] = 단품 정면 풀샷 첨부
   (세트 구성원 외형 lock)
□ 제품 등장 시 gemini_edit_image 선택 (generate_image ❌)
□ [PRODUCT] 블록에 "AS-IS 합성, 재그리기 ❌" + ★ LABEL LOCK 강제 어휘
   (라벨 텍스트·캡 컬러·병 실루엣 5% 이내) 명시
□ output_path = 05_ad_image/{YYYY-MM-DD}_{캠페인-슬러그}/{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-v{N}.png 절대경로 (★ 서브폴더 의무, 없으면 mkdir -p 선행)
□ ★ aspect_ratio = `1:1` (디폴트). 사용자가 4:5·9:16 등 명시 요청한 경우만 변경
□ 호출 직후 `rm 05_ad_image/*_thumb.jpeg` 로 thumb 정리
□ 분기 B: banned-words / copy-char-caps / cta-library 자동 검수·치환 완료
```

---

## 디테일 회피 룰 (11줄)

- ❌ 01~03 분석 3종이 안 채워졌는데 임의 4축 도출 (Prerequisites 충족 후 진입)
- ❌ brand_brief.md § 4-1 6슬롯이 비어있는데 임의 HEX 추정해서 채우기
- ❌ 제품 등장 시 `generate_image` 사용 (`edit_image` 의무)
- ❌ 제품·로고 reference 없이 텍스트만으로 합성 (다른 브랜드로 환각)
- ❌ reference 가 제공됐는데 prompt 에 제형 색·텍스처 묘사
- ❌ Step 1.4 Asset Discovery 스킵하고 임의 파일을 image_path 에 박기 (학생 환경은 파일명 제각각 — 카탈로그 분류 의무)
- ❌ 시안 컨셉이 듀오·풀세트·드로퍼 디테일인데 `image_path` 를 단품 정면 풀샷 1장만으로 채우기 (§ 1.5-3 카테고리 매트릭스 참조)
- ❌ `reference_images[0]` (라벨 매크로) 슬롯을 비워둔 채 호출 — Asset Discovery 가 라벨 매크로 카테고리 부재 판정 시는 예외 (warning 후 슬롯 비우고 진행 OK)
- ❌ 같은 프롬프트 5번 호출해서 변형 채우기 (5축 중 1~2개 비틀어 재작성)
- ❌ output_path 미지정 (메모리 룰)
- ❌ 분기 B 에서 자동 도출 결과를 confirmed_brief.md 로 디스크 저장 (사용자 명시 요청 시만 영구화)

## GPT 분기 (옵션)

사용자가 "GPT로", "gpt-image-1" 등을 명시 요청한 경우에만 GPT Image MCP 사용. 본 스킬의 § 핵심 원칙 5줄(컬러 팔레트 인용 포함)은 동일 적용 — 단 `image` 슬롯이 single binary 라 제품컷 1장만 binary, 로고는 prompt 에 절대경로 인용 + AS-IS 합성 directive.

## 다음 단계

이미지 생성 완료 후:
> "광고 집행 후 데이터가 모이면 `/06-meta-report` 로 성과 리포트를 만들 수 있습니다. (06 모듈은 추후 구축 예정)"

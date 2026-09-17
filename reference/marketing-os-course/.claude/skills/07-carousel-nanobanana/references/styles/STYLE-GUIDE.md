# 카드뉴스 스타일 가이드 — Reference URL/이미지 기반 5스타일 풀

> 본 파일은 07-carousel-nanobanana 스킬이 슬라이드 비주얼 디렉션을 결정할 때 1차 풀로 사용한다. 사용자가 `styles/reference-urls.md` 에 인스타 URL 을 넣거나 PNG/JPG 를 슬롯 폴더에 직접 드롭하면, 스킬이 시각 흡수해 아래 5개 스타일 슬롯에 매핑·작성한다.
>
> 작성 주체: 07 스킬 (사용자가 "스타일 가이드 만들어줘" 호출 시).
> 최종 작성: **2026-05-11** (해외 브랜드 앵커 네이밍으로 재편 — 강의용으로 국내 브랜드 reference 비사용).

---

## 사용 절차 (사용자 → 스킬)

### Step 1: 사용자가 reference 드롭

다음 중 1개 방식:

- **방식 A — Apify 자동 다운로드 (★ 권장, 가장 빠름)**: `styles/reference-urls.md` 에 `URL → 슬롯` 형식으로 라인별 입력 후 → `python3 .claude/skills/07-carousel-nanobanana/_scripts/fetch_style_refs.py` 실행. Apify `apify/instagram-post-scraper` 액터가 IG 차단 우회·다운로드. 슬롯 폴더에 자동 분배.
- **방식 B — 수동 드롭**: 5개 스타일 슬롯 하위 폴더 (`01-versed/`, `02-glowrecipe/`, `03-glossier/`, `04-tula/`, `05-herbivore/`) 에 PNG/JPG 직접 드롭. **스타일당 5~7장 권장** (1장만이면 시각 흡수 약함)
- **방식 C — 혼합**: A 로 일부 + B 로 보강

> 방식 A 사전 준비: `export APIFY_TOKEN="apify_api_..."` (https://console.apify.com/settings/integrations) + 액터 1회 활성화 (https://apify.com/apify/instagram-post-scraper). 비용은 1000 게시물당 약 $1.30 — 25장이면 거의 무료.

### Step 2: 스킬이 자동 시각 흡수 + 본 파일 작성

스킬 호출 시:

1. 슬롯 폴더 내 모든 reference 자료 enumerate
2. URL → Playwright `browser_navigate` + `browser_take_screenshot` 으로 시각 캡처
3. 이미지 → `Read` 로 직접 시각 분석
4. 시각 속성 추출 (컬러·라이팅·구도·타이포·무드·텍스처)
5. 비슷한 무드끼리 클러스터링 → 5개 스타일 슬롯에 매핑
6. 본 파일의 § 5스타일 풀 섹션 자동 작성

### Step 3: 사용자 확인 + 작업 시작

스킬이 작성 완료 후 사용자에게 보고. 사용자는 "글로시어 스타일로 카드뉴스 만들어줘" 식으로 호출 (브랜드 앵커명 = 슬롯).

---

## 호출 매핑 (사용자 발화 → 슬롯)

| 사용자 발화 예 | 슬롯 |
|---|---|
| "베르사드(Versed) 스타일", "클린 미니멀", "흰 배경 산세리프" | `01-versed` |
| "글로우레시피 스타일", "컬러 풀블리드", "비비드 컬러 블록", "과일 모티프" | `02-glowrecipe` |
| "글로시어 스타일", "핑크·뉴트럴", "소프트 페미닌", "세리프 믹스" | `03-glossier` |
| "툴라 스타일", "프로바이오틱 더마", "사이언티픽 데이터", "그리드·숫자" | `04-tula` |
| "허비보어 스타일", "내추럴", "보태니컬", "헤리티지" | `05-herbivore` |

---

## 5스타일 풀 (★ 2026-05-11 해외 브랜드 재편)

### 스타일 ① — Versed 톤 (클린 미니멀)

- **브랜드 앵커**: @versed (US 클린·뉴트럴 미니멀 더마코스메)
- **슬롯**: `01-versed`
- **무드 키워드** (2~3개): 클린·뉴트럴·정직
- **컬러**:
  - BG: 순백 #FFFFFF / 오프화이트 #FAFAF7
  - TEXT-Primary: 잉크 블랙 #1A1A1A
  - TEXT-Sub: 미들 그레이 #767676
  - ACCENT: 라이트 그레이 라벨 박스 (#F0F0F0) — 성분/단가 표기용
  - `brand_brief.md § 4-1` 매핑: BG-Light = 백 / TEXT-Primary = 잉크 / 시그니처 컬러는 라벨 박스 1색만 사용 (브랜드 시그니처 동적 치환)
- **타이포**:
  - Hook: 한글 산세리프 (Pretendard·Spoqa Han Sans 류), Bold, 우측 또는 좌측 정렬
  - 줄바꿈 의도적 (3~4줄 짧게 분절)
  - 강조 어휘에 미세한 자간 ↓
- **레이아웃 특징**: `slide-templates.md` § H1 (빅 타이포) + § B1 (헤드+본문+제품) 친화. 제품 단일 컷이 슬라이드 70% 차지, 카피는 여백에 정렬
- **소품·텍스처**: 성분명 라벨 박스 (농도 표기), 제품 단일컷, 텍스처 클로즈업 (제형 캡슐/액상), 흰 그림자 거의 없음·플랫
- **Best for**:
  - 성분 교육·정보형 (`carousel-narrative-arc.md` § ① 정보형 골격)
  - 임상수치·결과 강조 (수치 라벨이 라벨 박스 안에 들어감)
  - 가격·심플 메시지 — 산만함 ❌
- **참조 자료**: `01-versed/` 폴더 enumerate (5~7장 권장)
  - 폴더 내 모든 PNG/JPG 를 시각 흡수
  - 1차 시드: @versed
  - 추가 권장 출처: @theinkeylist, @bubble, @vichy
- **NanoBanana 프롬프트 어휘 시드** (영문, 5요소 [1]~[5] 블록 합성용):
  - BACKGROUND: `pure white seamless background, soft natural studio light, no shadows`
  - TEXT EFFECT: `precise Korean sans-serif headline, ink black, multi-line aligned right, generous line spacing, small science-label box bottom-left with ingredient name`
  - LAYOUT: `single product hero shot 60-70% frame, headline copy to opposite side, balanced negative space, editorial poster composition`
  - MOOD/STYLE: `editorial minimal, scientific clean, neutral tone, pharmacy-grade clarity`

---

### 스타일 ② — Glow Recipe 톤 (컬러 블록 빅 타이포)

- **브랜드 앵커**: @glowrecipe (US K-뷰티 비비드 컬러·과일 모티프)
- **슬롯**: `02-glowrecipe`
- **무드 키워드** (2~3개): 컬러 풀·임팩트·후크
- **컬러**:
  - BG: 풀 컬러 블록 (워터멜론 핑크 #FFAAB8 / 망고 옐로우 #FFC857 / 아보카도 그린 #B7D087 / 블루베리 #6B8FE3 — 제품 컨셉 컬러 1개)
  - TEXT-Primary: 잉크 블랙 #1A1A1A 또는 다크 톤 (BG 비비드 시 보색 다크)
  - TEXT-Sub: 다크 톤 (BG 보색)
  - ACCENT: 흰 라벨 박스 또는 BG 보색 박스
  - `brand_brief.md § 4-1` 매핑: BRAND-Signature 가 풀 BG 로 격상, BG-Light 는 사용 ❌
- **타이포**:
  - Hook: 한글 산세리프 굵게 + 매우 큰 size (슬라이드 폭 80%)
  - 한 줄에 2~3 글자만, 의도적 줄 끊기로 시각 압박감
  - 강조 부분만 다른 색·다른 weight
- **레이아웃 특징**: `slide-templates.md` § H1 (빅 타이포 풀블리드) + § H3 (질문 던지기) 친화. 제품 컷이 비비드 BG 안에 떠 있거나 trim 됨
- **소품·텍스처**: 과일·식물 모티프 일러스트 (워터멜론·망고·아보카도 등 제품 키 인그리디언트), 작은 라벨 박스, 큐트한 손글씨 디테일
- **Best for**:
  - 페인 공감·스토리형 Hook 슬라이드 (`carousel-narrative-arc.md` § ② 스토리형)
  - 리스트형 (`carousel-narrative-arc.md` § ③) 의 표지·구분 슬라이드
  - 임팩트 강한 첫 슬라이드용 (저장·공유 KPI ↑)
  - 단일 키 인그리디언트 브랜딩 (예: 비타민C, 펩타이드)
- **참조 자료**: `02-glowrecipe/` 폴더 enumerate (5~7장 권장)
  - 폴더 내 모든 PNG/JPG 를 시각 흡수
  - 1차 시드: @glowrecipe
  - 추가 권장 출처: @drunkelephant, @youthtothepeople, @milkmakeup
  - BG 컬러는 brand_brief § 4-1 BRAND-Signature 와 톤 매칭되는 reference 우선
- **NanoBanana 프롬프트 어휘 시드**:
  - BACKGROUND: `vivid solid color block background (watermelon pink / mango yellow / avocado green — match brand signature), seamless flat, optional fruit illustration motif`
  - TEXT EFFECT: `oversized Korean sans-serif headline, ink black, 2-3 characters per line, intentional line breaks, contrast against vivid background`
  - LAYOUT: `full-bleed color, headline dominates 70% of frame, small ingredient label box bottom, product shot trimmed at edge`
  - MOOD/STYLE: `bold poster, high contrast, retail-window impact, K-beauty pop, fruity playful`

---

### 스타일 ③ — Glossier 톤 (소프트 페미닌·뉴트럴)

- **브랜드 앵커**: @glossier (US 핑크·뉴트럴 페미닌 미니멀)
- **슬롯**: `03-glossier`
- **무드 키워드** (2~3개): 부드러운·페미닌·뉴트럴
- **컬러**:
  - BG: 글로시 핑크 #FFC7C2 / 누드 베이지 #F4E5D6 / 크림 #F5EBDB / 살구 #F4D5C2
  - TEXT-Primary: 다크 브라운 #3C2A1E 또는 다크 라벤더 #4A3B5C
  - TEXT-Sub: 미디엄 누드 (#C9A998, #B89B85)
  - ACCENT: 골드/브론즈 영문 로고 (#B89968)
  - `brand_brief.md § 4-1` 매핑: BG-Light = 파스텔 핑크/누드, BRAND-Signature = 같은 톤 다크 변형
- **타이포**:
  - Hook: 한글 세리프 (Noto Serif KR·나눔명조) + 영문 디스플레이 세리프 믹스
  - 영문은 "GLOSSIER", "DEW", "SKIN FIRST" 같은 큰 디스플레이 폰트
  - 한글은 부제로 작게, 동글동글한 산세리프
  - 한·영 혼합 레이아웃이 핵심 특징
- **레이아웃 특징**: `slide-templates.md` § H5 (비포애프터) + § B5 (풀블리드 사진) 친화. 제형/제품 사진이 슬라이드 풀블리드로 깔리고, 텍스트는 상단 또는 하단에 짙은 톤으로
- **소품·텍스처**: 글로시한 제형 매크로, 작은 영문 로고 마크, 모델 손·입술 클로즈업, 셀카톤 라이프스타일 컷
- **Best for**:
  - 라이프스타일·후기 (`carousel-narrative-arc.md` § ② 스토리형)
  - 페미닌 브랜드 (스킨케어·립·향수)
  - 부드러움이 브랜드 코어
- **참조 자료**: `03-glossier/` 폴더 enumerate (5~7장 권장)
  - 폴더 내 모든 PNG/JPG 를 시각 흡수
  - 1차 시드: @glossier
  - 추가 권장 출처: @rarebeauty, @merit, @summerfridays
  - 한·영 혼합 레이아웃 + 누드 톤 reference 우선
- **NanoBanana 프롬프트 어휘 시드**:
  - BACKGROUND: `soft pastel background (glossy pink / nude beige / cream), warm natural light, slight gradient, intimate close-up ambiance`
  - TEXT EFFECT: `Korean serif headline + English display serif (e.g., "GLOSSIER" "DEW"), mixed-script layout, dark brown or plum text, generous letter-spacing on English`
  - LAYOUT: `full-bleed dewy texture macro or model lifestyle, headline overlay top or bottom, small gold/bronze logo mark at corner`
  - MOOD/STYLE: `soft feminine, dewy minimal, romantic neutral, you-but-better skin aesthetic`

---

### 스타일 ④ — TULA 톤 (사이언티픽 데이터·그리드)

- **브랜드 앵커**: @tula (US 프로바이오틱 더마 사이언티픽)
- **슬롯**: `04-tula`
- **무드 키워드** (2~3개): 데이터·임상·신뢰
- **컬러**:
  - BG: 콜드 그레이 #E8EAED / 라이트 그레이 #F2F2F2 / 클리니컬 블루 틴트 #DEE6F0
  - TEXT-Primary: 차콜 #1F2225
  - TEXT-Sub: 미디엄 그레이 #5C6068
  - ACCENT: 클리니컬 블루 #2E5BFF 또는 임상 그린 #00A86B — 수치 강조용
  - `brand_brief.md § 4-1` 매핑: BG-Light = 콜드 그레이, BRAND-Signature = 클리니컬 블루/그린, TEXT 는 차콜
- **타이포**:
  - Hook: 한글 산세리프 + 큰 숫자 (디스플레이 numeric, Bold)
  - 숫자가 시각 자산: "3", "82%", "4주" 등이 슬라이드 30~50% 차지
  - 수치 옆에 작은 출처·단위 (`*임상 N=30`)
  - 일관 산세리프 (영문은 Helvetica/Inter 류)
- **레이아웃 특징**: `slide-templates.md` § B3 (수치·통계 박스) + § B4 (제품 그리드) 친화. 제품을 가로 N열 그리드로 정렬, 숫자가 그리드 상단/중앙에 빅 사이즈
- **소품·텍스처**: 제품 라인업 그리드 (3~5개 줄지어 배치), 차트·바 그래프 미니, 측정 자/수치 마커, 클리닉 노트 텍스처, 프로바이오틱 미생물 일러스트
- **Best for**:
  - 임상수치·결과 강조 (`carousel-narrative-arc.md` § ① 정보형)
  - 리스트형 (`carousel-narrative-arc.md` § ③) — N가지 제품 비교
  - 더마·기능성 화장품 — 신뢰 톤
- **참조 자료**: `04-tula/` 폴더 enumerate (5~7장 권장)
  - 폴더 내 모든 PNG/JPG 를 시각 흡수
  - 1차 시드: @tula
  - 추가 권장 출처: @paulaschoice, @theinkeylist, @vichy
  - 임상수치·결과·비교가 들어간 reference 위주 — 무드샷·라이프스타일은 ❌
- **NanoBanana 프롬프트 어휘 시드**:
  - BACKGROUND: `cool light gray seamless background, clinical lab vibe, soft top-down lighting, faint grid lines`
  - TEXT EFFECT: `oversized numeric display ("3", "82%", "9 days"), Korean sans-serif sub-headline, clinical blue or green accent on number, small footnote attribution`
  - LAYOUT: `horizontal product lineup grid (3-5 products), number anchored top-center or center, micro chart/bar overlay, lab-note composition`
  - MOOD/STYLE: `data-driven, scientific dermatology, trust-building, clinical clarity, probiotic-skin-science tone`

---

### 스타일 ⑤ — Herbivore Botanicals 톤 (내추럴·보태니컬 헤리티지)

- **브랜드 앵커**: @herbivorebotanicals (US 내추럴·식물·헤리티지)
- **슬롯**: `05-herbivore`
- **무드 키워드** (2~3개): 내추럴·식물·헤리티지
- **컬러**:
  - BG-Light: 따뜻한 백 #FAF7F2 / 라이트 베이지 #F0E8DC / 세이지 #C5D2BF
  - BG 자연 슬라이드: 자연광 풀블리드 식물·텍스처 사진
  - TEXT-Primary: 잉크 블랙 #1A1A1A 또는 다크 그린 #2C3D2E
  - ACCENT: 빈티지 검정 라벨 박스 + 흰 글씨 또는 식물 일러스트 — 헤리티지 약초학 컨벤션
  - `brand_brief.md § 4-1` 매핑: BG-Light = 따뜻한 백/베이지/세이지, BRAND-Signature = 검정 라벨 또는 다크 그린, TEXT 는 잉크
- **타이포**:
  - Hook 1: 자연 슬라이드 — 한글 산세리프 작게, 사진/식물 자체가 메인
  - Hook 2: 헤리티지 라벨 슬라이드 — 영문 디스플레이 세리프 (브랜드 로고 클래식) + 검정 박스 안 큰 흰 글씨 한글
  - 작은 영문 attribution ("Botanically formulated / Vegan / Cruelty-free")
- **레이아웃 특징**: `slide-templates.md` § H5 (비포애프터·자연 비유) + § B1 (헤드+본문+제품) 친화. 슬라이드 시퀀스에서 자연·식물 슬라이드(공감) → 라벨 슬라이드(브랜드 신뢰) 교차
- **소품·텍스처**: 식물·꽃잎·허브 자연광 클로즈업, 빈티지 라벨 박스, 헤리티지 attribution 텍스트, 약초학 노트 모티프, 압화·드라이플라워
- **Best for**:
  - 페인 공감·스토리형 (`carousel-narrative-arc.md` § ② 스토리형) — 자연·식물이 강한 공감 트리거
  - 후기·리얼 보이스 (#내추럴라이프 같은 UGC 시리즈)
  - 헤리티지·비건·내추럴 브랜드 — 식물성 원료 출신 스토리
- **참조 자료**: `05-herbivore/` 폴더 enumerate (5~7장 권장, 자연·라벨 양쪽 균형)
  - 폴더 내 모든 PNG/JPG 를 시각 흡수
  - 1차 시드: @herbivorebotanicals
  - 추가 권장 출처: @youthtothepeople, @beboldforbeauty, @ranavat
  - 자연 reference 는 자연광·실제 식물 (스톡 일러스트 ❌)
- **NanoBanana 프롬프트 어휘 시드**:
  - BACKGROUND:
    - 자연 슬라이드: `natural daylight botanical close-up, neutral warm tone, real plant detail, pressed flower or herb arrangement`
    - 라벨 슬라이드: `warm off-white background (#FAF7F2), heritage apothecary aesthetic, light sage green accent`
  - TEXT EFFECT:
    - 자연: `minimal Korean sans-serif overlay, small, bottom-aligned, dark forest green`
    - 라벨: `classic vintage black label box with white Korean sans-serif inside, English display serif brand mark above, small attribution footer ("Botanically formulated" style)`
  - LAYOUT: `alternating botanical full-bleed + classic apothecary label slide, attribution footer with vegan/cruelty-free marks`
  - MOOD/STYLE: `botanical apothecary, natural-real, plant-derived, heritage herbalism, clean beauty trust`

---

## 스타일 선택 매핑 (사용자 토픽 → 스타일)

사용자가 스타일 미명시 시 자동 매핑:

| 사용자 토픽·골격 | 추천 스타일 슬롯 | 이유 |
|---|---|---|
| 성분 교육·정보형 | ① Versed (`01-versed`) | 흰 배경 + 산세리프 + 라벨 박스가 성분/농도/임상 어휘를 정직하게 전달. 산만함 ❌ |
| 페인 공감·스토리형 | ⑤ Herbivore (`05-herbivore`) 또는 ② Glow Recipe (`02-glowrecipe`) | ⑤ 자연·식물이 공감 트리거 ↑ / ② 빅 타이포가 첫 슬라이드 후크에 강함 |
| 팁·리스트형 | ④ TULA (`04-tula`) | N개 항목/제품 그리드 + 숫자 라벨이 리스트 시각화에 최적 |
| 임상수치·결과 강조 | ④ TULA (`04-tula`) | 큰 숫자 + 임상 출처 + 클리니컬 블루 액센트가 신뢰 톤 |
| 라이프스타일·후기 | ③ Glossier (`03-glossier`) | 누드 톤 + 한·영 세리프 + 글로시 매크로가 라이프스타일 컨버전 ↑ |
| 단일 키 인그리디언트 (비타민C·펩타이드 등) | ② Glow Recipe (`02-glowrecipe`) | 과일·식물 모티프가 키 인그리디언트 비유에 최적 |
| 비건·내추럴·식물 원료 | ⑤ Herbivore (`05-herbivore`) | 식물·약초학 코드가 코어 가치와 정합 |

> ⚠️ 5스타일은 해외 브랜드 앵커 기반 (2026-05-11 재편). "글로시어 스타일로 카드뉴스 만들어줘" 같은 자연어 호출 → `03-glossier` 슬롯으로 자동 라우팅.

---

## 5스타일이 다 채워지지 않은 상태에서 호출 시

스킬이 사용자에게 보고:
> "현재 슬롯 폴더에 reference 자료가 N개 있고, 작성된 스타일은 M개입니다. 다음 중 선택해주세요:
> - (A) 작성된 M개 스타일 중 1개로 진행
> - (B) reference 추가 드롭 후 5개 완성 후 진행
> - (C) brand_brief.md + 트렌드 가이드만으로 무 스타일·디폴트 진행"

---

## Quick Comparison (5스타일 한눈 비교)

토픽 → 스타일 결정을 1초 내 가능하게 하는 5×5 매트릭스. 본문 5스타일 풀을 다 읽기 전에 본 표로 1차 후보 좁히기.

| 스타일 (브랜드 앵커) | Photo Use | Illustration | Typography Focus | Visual Density | Mood |
|---|---|---|---|---|---|
| ① Versed (`01-versed`) | 단일 제품 히어로 (60-70% 프레임) | 라벨 박스 미니어처만 | 한글 산세리프 + 라벨 영문 | Low | Scientific clean, neutral |
| ② Glow Recipe (`02-glowrecipe`) | 가장자리 trim 또는 풀컬러 빠짐 | 과일·식물 모티프, 라벨 박스 | 빅 한글 산세리프 (한 줄 2-3자) | Low-Medium | Bold poster, K-beauty pop, fruity |
| ③ Glossier (`03-glossier`) | 풀블리드 글로시 매크로/모델 | 작은 영문 로고, 골드 디테일 | 한글 세리프 + 영문 디스플레이 세리프 (혼합) | Medium | Soft feminine, dewy neutral |
| ④ TULA (`04-tula`) | 제품 라인업 그리드 (3-5개) | 차트·바·자·미생물 마커 | 큰 숫자 디스플레이 + 한글 산세리프 | Medium-High | Data-driven, clinical trust, probiotic |
| ⑤ Herbivore (`05-herbivore`) | 풀블리드 식물·자연 클로즈업 | 빈티지 검정 라벨, 압화·허브 | 한글 산세리프 + 영문 헤리티지 세리프 | Low (자연) / Medium (라벨) | Botanical apothecary, natural-real |

> 매핑 휴리스틱: **단일 제품·정보형** → ① Versed / **첫 슬라이드 후크·임팩트·과일 모티프** → ② Glow Recipe / **라이프스타일·후기·매크로** → ③ Glossier / **임상수치·N개 비교** → ④ TULA / **자연·식물·헤리티지** → ⑤ Herbivore

---

## 스타일 추가·갱신 시

사용자가 새 reference 를 슬롯 폴더에 드롭하거나 기존 스타일 톤을 바꾸고 싶으면:
1. 본 파일의 해당 스타일 슬롯 (① ~ ⑤) 갱신
2. SKILL.md 호출 시 동적 로드 (캐시 ❌)
3. 작업 중 카드뉴스가 있으면 v 증가하며 재생성

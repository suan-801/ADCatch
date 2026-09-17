# Nike ACG 브랜드 브리프

> 소스: PDP — [ACG Aireez Women's Button-Up Long-Sleeve Graphic Trail Running Top](https://www.nike.com/t/acg-aireez-womens-button-up-long-sleeve-graphic-trail-running-top-p8Lwq7N4/IU8152-070) (Style: IU8152-070)
> 홈페이지 URL은 미제공 — PDP 단일 소스 기준 분석. 라인업 전체 시야가 필요하면 홈페이지/카테고리 URL 추가 후 재실행 권장.

## 한 줄 정의

Nike ACG(All Conditions Gear)는 트레일 러닝·아웃도어 익스플로러를 위해 검증된 퍼포먼스 기술(Dri-FIT, UV 차단)을 기능적 디테일(스냅 포켓, 버튼다운 칼라)에 담아 "어떤 조건에서도 달릴 수 있다"고 약속하는 Nike의 테크니컬 아웃도어 서브 브랜드.

## USP 3개

1. **Nike Dri-FIT 기술** — 땀을 피부에서 빠르게 배출해 건조·쾌적 유지 (자사 독자 기술명)
2. **UV 차단 + 팝업 칼라** — UVA/UVB 차단 원단 + 목·목덜미 추가 커버용 칼라 (트레일 러닝 특화 기능)
3. **기능성 디테일** — 젤·이어폰 수납용 스냅 클로저 체스트 포켓, 러닝 중 흔들림 최소화하는 버튼다운 칼라, 리플렉티브 디테일(야간 시인성)

## 타겟

- **Primary**: 트레일 러닝·아웃도어 액티비티를 즐기는 여성, 기능성 장비를 중시하는 테크웨어 지향 소비자
- **구매 결정 트리거**: 뙤약볕 아래 장거리 러닝/트레일 상황에서의 실사용 기능 (UV 차단, 땀 관리, 수납) — 패션보다 "조건 대응력"이 우선

## 톤 — Always / Never

**Always**
- 짧고 리드미컬한 문장 ("Blazing sun, miles to run.")
- 2인칭 직접 호출 + 행동 촉구 ("What are you waiting for?")
- 액티비티/조건 중심 서술 (더위·트레일·달림 그 자체를 주어로)

**Never**
- 장황한 설명형 카피
- 감성/라이프스타일 위주 문구 (기능·조건 언급 없이 "예쁘다"류)
- 느낌표 남발 (에너제틱하되 절제된 톤)

## 비주얼

### 컬러 팔레트 6슬롯

| 슬롯 | 용도 | HEX | 출처 |
|---|---|---|---|
| `BG-Light` | 배경 시작점·평면 베이스 | `#FFFFFF` | PDP 페이지 배경 (computed style) |
| `BG-Deep` | 배경 끝점·푸터 | `#111111` | PDP CTA 버튼 배경 (computed style) — 니어블랙, 순수 블랙 아님 |
| `BRAND-Signature` | 시그니처 메인 — CTA·키워드·1포인트 강조 | `#111111` | "Add to Bag" 버튼 배경, 헤드라인 텍스트 컬러 |
| `BRAND-Sub` | 보조 강조 — 뱃지·서브 강조 | `#D33918` | "Recycled Materials" 뱃지 텍스트 (Nike Move to Zero 지속가능성 배지 컬러) |
| `TEXT-Primary` | 메인 텍스트 | `#111111` | 상품명·가격 텍스트 (computed style) |
| `TEXT-Sub` | 보조 텍스트 (라벨·캡션) | `#707072` | "United States" 지역 라벨 등 보조 텍스트 (computed style) |

> ACG 실제 제품 컬러웨이(스크린샷 확인): 다크 스모크 그레이/화이트(대표 이미지) · 화이트 · 카키/스톤 · 핫핑크 4종 전개 — 시그니처 컬러는 블랙 계열이되, 서브 컬러웨이로 대담한 포인트(핑크) 병행. 광고 소재 배경/CTA는 `BRAND-Signature` 블랙 기준, 포인트 강조에 핑크 계열 사용 가능(단 이번 PDP 페이지 UI에서 HEX 미확인 — `[확인 필요]`).

### 사용 ❌ 컬러

- ❌ 네온·형광 (블랙 기반 미니멀 톤 이탈)
- ❌ 무지개 그라디언트 / 4컬러 이상 그라데이션
- ❌ 파스텔 톤 전면 사용 (ACG는 테크니컬 톤 — 파스텔은 라이프스타일 라인과 혼동 우려)

### 요소별 컬러 매핑

| 디자인 요소 | 사용 슬롯 | 비고 |
|---|---|---|
| 메인 배경 | `BG-Light` | 화이트 베이스, 제품 사진 중심 레이아웃 |
| 푸터·CTA 배경 띠 | `BG-Deep` / `BRAND-Signature` | 블랙 솔리드 |
| 헤드라인 (메인 카피) | `TEXT-Primary` | 배경이 어두우면 `#FFFFFF`로 반전 |
| 서브 카피·라벨·캡션 | `TEXT-Sub` | 상품 스펙·지역 정보 등 |
| 지속가능성/기능 뱃지 | `BRAND-Sub` | "Recycled Materials"류 배지 전용, 남용 금지 (1개 시안당 1개) |
| CTA 버튼 (배경) | `BRAND-Signature` 솔리드 | 버튼 텍스트는 `#FFFFFF` |
| 박스·도형 외곽선 | `BRAND-Signature` 18% opacity | 두꺼운 솔리드 외곽선 지양 |

### 폰트 + 제형(소재) 묘사

- **폰트 패밀리**: Helvetica Now Text (본문, weight 400) / Helvetica Now Display Medium (헤드라인 h1, weight 500) / Helvetica Now Text Medium (버튼·가격·라벨, weight 500) — PDP computed style 실측
- **소재 묘사**: 72% 나일론 / 28% 스판덱스 혼방 taffeta 소재, 가볍고 신축성 있음. 매트한 표면감(광택 낮음), 버튼다운 칼라 + 체스트 스냅 포켓의 유틸리티 디테일이 실루엣의 핵심 (페이지 상품 이미지 인용)

## 가격 + 메인 오퍼

- **가격**: $125 (프로모션/할인 미노출 — 정가 판매 중)
- **부가 오퍼**: "Members: Free Shipping on Orders $50+" (멤버십 무료배송 배너, 사이트 공통 프로모션으로 이 제품 전용 오퍼 아님)
- **분납 옵션**: "From $11/mo" 표기 확인 (제품 페이지 하단, 정확 결제 서비스명은 `[확인 필요]`)

## 신뢰/기술 자산

- Nike Dri-FIT 기술 (자사 독자 기술명)
- UVA/UVB 차단 (단, PPE 미해당 명시 — 노출부는 별도 자외선차단제 권장 문구 포함)
- Recycled Materials 뱃지 (Nike Move to Zero 지속가능성 라인)
- 리플렉티브 디테일 (야간 시인성)

## 디테일 회피 룰 준수 메모

- 시크릿몰/랜딩페이지 아님, 본 브랜드 공식 PDP 1개 소스로 분석 완료
- CTA 버튼·뱃지 컬러는 실측 computed style 기준, 추정 HEX 없음
- 컬러웨이 4종 중 대표 이미지(다크 스모크 그레이) 기준 시그니처 컬러 확정, 핑크 등 서브 컬러웨이 정확 HEX는 `[확인 필요]` (제품 스와치 썸네일에서 시각 확인만 가능, DOM에서 HEX 값 노출 안 됨)
- 홈페이지 미분석으로 Nike 전사 브랜드 톤(코어 라인업)까지는 다루지 않음 — ACG 서브 브랜드 PDP 기준 분석

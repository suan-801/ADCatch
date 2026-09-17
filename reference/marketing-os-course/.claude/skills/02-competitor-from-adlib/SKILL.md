---
name: 02-competitor-from-adlib
description: 경쟁사 Meta 광고라이브러리 URL **하나만** 받으면 ① page_name 으로 슬러그 자동 도출 → ② Apify 액터로 광고 크롤링 → ③ 이미지·영상·메타(제목·랜딩 URL·캡션) 저장 → ④ **USP 분석법 3 항목**(User's Problem · Solution · Promotion (+ Creative Key Visual 별도 축)) 으로 소재 분석 (영상은 ffmpeg 키프레임 6장 추출 → Gemini 멀티모달 이미지 분석. 대본·오디오 추출 ❌) → ⑤ HTML 대시보드 빌드 → ⑥ 경쟁사별 트렌드 요약 리포트 작성. 사용자가 "경쟁사 광고 분석해줘", "경쟁사 A 광고 봐줘", "/02-competitor-from-adlib" 등으로 요청할 때 호출. 산출물은 `04_brief` 시안 작성과 `05_ad_image` 이미지 생성 시 빈틈·차별화 인풋으로 쓰임.
---

# 02. 경쟁사 광고 분석 (Meta Ad Library → Apify → USP 3 항목 + Creative Key Visual + ad_pattern → 대시보드 + 트렌드 리포트)

## 언제 호출되는가

- "경쟁사 광고 분석해줘"
- "경쟁사 A 광고 봐줘"
- "/02-competitor-from-adlib"
- `01_brand/brand_brief.md` 가 이미 있고, 경쟁사 분석을 추가/갱신할 때

## 인풋 (Less is More — 한 파일에 URL 만)

- **권장 (Mode 1 — 통합 파일):** `02_competitor/_inputs/competitors.md` 에 경쟁사 URL 을 한 줄씩 적어두면, 스크립트가 이 파일만 읽고 모든 경쟁사 폴더·분석·대시보드를 자동 생성합니다. 사용자가 편집하는 **유일한 파일**.
  ```markdown
  ## 직접경쟁
  https://www.facebook.com/ads/library/?...&view_all_page_id=111   # 경쟁사 A
  https://www.facebook.com/ads/library/?...&view_all_page_id=222   # 경쟁사 B
  ## 간접경쟁
  https://www.facebook.com/ads/library/?...&view_all_page_id=333   # 경쟁사 C
  ```
- **단발 추가 (Mode 2):** URL 1개만 인자로 던지기 — `python3 fetch_competitor_ads.py "<URL>"`
- **옛 방식 호환 (Mode 3):** `python3 fetch_competitor_ads.py brand-a` — `_inputs/brand-a.md` 단일 갱신
- 슬러그·브랜드명 등 나머지는 스크립트가 Apify 응답의 `page_name` 으로 자동 도출
- **자격증명 등록** (Step 2 에서 필요) — **`09_tracking/.env`** 에 한 줄씩 작성 (스크립트가 자동 로드, `python-dotenv` 의존성 ❌, stdlib 파서 내장):
  - `APIFY_TOKEN=apify_api_...` — Apify API 토큰 (https://console.apify.com/settings/integrations)
  - `GEMINI_API_KEY_FREE=AQ...` — **무료 티어 키** (디폴트, 결제 미연결, 250 RPD 한도)
  - `GEMINI_API_KEY_PAID=AQ...` — 유료 티어 키 (선택, `--paid` 플래그 시 사용)
  - `GEMINI_API_KEY=AQ...` — 단일 키 운영 시 (둘 다의 폴백, 구버전 호환)
  - 임시 `export` 도 가능하지만 셸 종료 시 휘발. `.env` 등록이 표준
  - 템플릿: `09_tracking/.env.example` 참고
  - **무료 키 만들기**: AI Studio → "Create API key" → 결제 계정 연결 안 함 → 영구 0원 (단, 250 RPD 초과 시 자동 정지)
  - **★ 키 형식 (2026년 새 정책)**: 새로 발급하는 Gemini 키는 `AIza` 가 아니라 **`AQ` 로 시작**합니다 (표준 키 → 인증 키 전환, 보안 강화). 그대로 복사해 쓰면 됩니다. 예전에 받아둔 `AIza` 키는 2026년 9월 전까지만 동작하니 그 전에 새 키(`AQ`)로 교체하세요. 코드 수정은 불필요 — `.env` 값 한 줄만 바꾸면 됩니다.
- **사용 액터**: `curious_coder/facebook-ads-library-scraper`

## 아웃풋 (폴더 구조)

```
02_competitor/
├── _inputs/
│   ├── README.md                       # 입력 모드 가이드
│   ├── competitors.md                  # ★ 통합 입력 (사용자가 편집하는 유일한 파일)
│   └── {slug}.md                       # 경쟁사별 시드 (자동 생성, 추적·이력용)
├── _scripts/
│   ├── fetch_competitor_ads.py         # Apify + Gemini 크롤·분석
│   ├── build_dashboard.py              # HTML 대시보드 빌드
│   └── README.md
├── _reference/
│   └── reference_analysis_method.md    # ★ USP 분석법 3 항목 정의 (User's Problem · Solution · Promotion + Creative Key Visual)
├── {slug}/                             # 경쟁사별 폴더 (예: brand-a/)
│   ├── ad-creatives/
│   │   ├── metadata.json               # Apify 원본 광고 카드
│   │   ├── analysis.json               # Gemini USP 3 항목 분석 결과 (ad_id 별)
│   │   ├── images/{ad_id}_{n}.jpg
│   │   ├── videos/{ad_id}_{n}.mp4
│   │   └── keyframes/{ad_id}_*_kf{1..6}.jpg   # 영상 키프레임 6장 (시각 분석용)
│   └── ad-creatives.md                  # 경쟁사별 1페이지 분석 (USP 3 항목 적용)
├── dashboard/
│   ├── index.html                      # 단일 페이지 HTML 대시보드
│   ├── dashboard.json                  # 통합 데이터
│   └── media/{slug}/{images,videos}/   # 미디어 사본
└── competitor_ads.md                   # ★ 통합 트렌드 요약 리포트 (모든 경쟁사 한 파일)
```

---

## 작업 순서 (7 단계)

### Step 1. URL 입력 — 통합 파일 1곳에서 관리

**기본 흐름 (Mode 1 — 통합 파일):** 사용자는 `02_competitor/_inputs/competitors.md` 한 곳에 경쟁사 URL 을 한 줄씩 적어두기만 하면 됩니다.

```markdown
## 직접경쟁
https://www.facebook.com/ads/library/?...&view_all_page_id=111   # 경쟁사 A
https://www.facebook.com/ads/library/?...&view_all_page_id=222   # 경쟁사 B

## 간접경쟁
https://www.facebook.com/ads/library/?...&view_all_page_id=333   # 경쟁사 C
```

```bash
python3 02_competitor/_scripts/fetch_competitor_ads.py
```

스크립트가 자동 처리하는 것:
- `competitors.md` 의 모든 URL 추출 (헤딩 → classification, `# 메모` → brand_kr 힌트)
- URL 별로 Apify 첫 응답의 `page_name` 으로 슬러그 자동 도출
- `_inputs/{slug}.md` 자동 생성 (추적·이력용 — 사용자 편집 불필요)
- URL 라인 맨 앞에 `#` 붙이면 비활성화 (다음 실행 스킵)

**Mode 2 (단발 URL 추가):** `competitors.md` 안 건드리고 한 번만 처리
```bash
python3 02_competitor/_scripts/fetch_competitor_ads.py "https://www.facebook.com/ads/library/?...&view_all_page_id=123"
```

**Mode 3 (옛 방식 호환, 슬러그 단일 갱신):**
```bash
python3 02_competitor/_scripts/fetch_competitor_ads.py brand-a
```

> Page ID 기반 딥링크 권장. 검색 쿼리 URL 은 동명·유사 브랜드 노이즈 섞임.
> 모기업 단위 페이지는 한 페이지에 여러 브랜드 광고 — `competitors.md` 의 `# 메모` 에 명시.

### Step 2. Apify 크롤링 — `_scripts/fetch_competitor_ads.py`

> 💡 토큰은 **`09_tracking/.env`** 에 한 번만 등록하면 스크립트가 자동 로드합니다 (셸을 닫아도 유지). 등록 안 됐으면 아래 `export` 폴백 사용.

```bash
# (선택) 등록 안 했을 때 임시 폴백 — 현재 셸에서만 유효
# export APIFY_TOKEN="apify_api_..."
# export GEMINI_API_KEY="AQ..."   # 2026년 새 키는 AQ 로 시작 (옛 AIza 키는 9월 전까지만 동작)

# (권장) 통합 파일 일괄 — competitors.md 의 모든 URL 처리
python3 02_competitor/_scripts/fetch_competitor_ads.py

# URL 1개만 단발 처리 (competitors.md 안 건드림)
python3 02_competitor/_scripts/fetch_competitor_ads.py "https://www.facebook.com/ads/library/?...&view_all_page_id=123"

# 슬러그 단일 갱신 (옛 방식 호환)
python3 02_competitor/_scripts/fetch_competitor_ads.py brand-a

# 옵션
python3 02_competitor/_scripts/fetch_competitor_ads.py --max 50     # 광고 최대 N개
python3 02_competitor/_scripts/fetch_competitor_ads.py --no-gemini  # 분석 스킵 (수집만)
python3 02_competitor/_scripts/fetch_competitor_ads.py --md-only    # 기존 데이터로 보고서만 재생성
python3 02_competitor/_scripts/fetch_competitor_ads.py --paid       # 유료 키(GEMINI_API_KEY_PAID) 사용. 무료 한도 신경 안 쓰고 즉시 풀 분석
```

> 💡 **무료 키 운영 (디폴트)**: 일일 250 요청 초과 시 자동 graceful 정지. 한도 도달한 광고는 `analysis.json` 에 `status: "quota_exceeded"` 로 마킹되고, 24시간 후 재실행 시 미분석 광고만 자동 재시도. 대시보드 카드 우상단 배지로 분석 상태 시각화: 🟢 분석완료 / ⏸️ 분석대기 / 🚫 무료한도 / ❌ 분석실패.

스크립트가 하는 일:
1. 인자 없으면 → `_inputs/competitors.md` 우선 파싱 (없으면 `_inputs/*.md` 슬러그 시드 폴백)
2. URL 직접 입력이면 → Apify 첫 응답의 `page_name` 으로 슬러그 자동 생성 + `_inputs/{slug}.md` 자동 작성
3. 슬러그 입력이면 → `_inputs/{slug}.md` 만 파싱
4. Apify 액터 `curious_coder/facebook-ads-library-scraper` 실행 (URL → 광고 dataset)
5. 광고 카드별 메타 + 미디어 다운로드 → `{slug}/ad-creatives/`
6. 모든 처리 끝나면 `02_competitor/competitor_ads.md` 통합 트렌드 리포트 갱신

### Step 3. 미디어 + 메타 저장 — `{slug}/ad-creatives/`

광고 카드 1건 = 다음 7필드를 `metadata.json` 의 한 항목으로 저장:

| 필드 | 설명 |
|---|---|
| `ad_id` | Meta 광고 ID |
| `title` | 광고 제목 (캡션 헤더) |
| `caption` | 본문 카피 |
| `cta_text` | 버튼 라벨 (예: "지금 구매") |
| `link_url` | 랜딩 URL |
| `landing_domain` | 랜딩 도메인 (자사몰·올리브영 등) |
| `active_period` | 첫 게시 ~ 최근 활성일 |
| `media` | `images/`, `videos/` 경로 배열 |

미디어는 `excluded_keys` (페이지 프로필·표지·썸네일) 제외하고 다운로드.

### Step 4. 광고 소재 상세 분석 — USP 분석법 3 항목

분석 프레임 정의 파일: `02_competitor/_reference/reference_analysis_method.md` (Read 필수).

**USP 3 항목 + Creative Key Visual + ad_pattern 분석:**

1. **User's Problem** — 고객의 어떤 문제를 해결하는가? (공감언어·상황. 페인/욕구/호기심/트렌드 톤)
2. **Solution** — 내 제품이 그 문제를 해결하는 이유 (USP 차별성 + RTB 권위·통념·숫자 + 결과 시각화)
3. **Promotion** — 지금 구매해야 하는 이유 (가격 혜택 + 리스크 제거 + 시급성)
4. **★ Creative Key Visual** — 메시지 3축과 *별개*의 시각축. 핵심 비주얼 1컷 묘사

**ad_pattern (1개 라벨 강제):**
- `default` — 페인 후킹 + Solution 자연 연결 + Promotion 약 (가장 흔함)
- `trust_anchor` — User's Problem 약, Solution(권위·랭킹·인증) 강 (예: 올리브영 1등 + 별점)
- `promotion_anchor` — Promotion 거의 전부 (할인·1+1·한정 강조 BOFU)
- `hybrid` — 2개 이상 동시 강조

> ⚠️ **모든 광고가 페인 후킹 아님** — 신뢰 자산 강조형(`trust_anchor`)·할인 강조형(`promotion_anchor`)도 정상 패턴. `ad_pattern` 라벨로 변주 명시.

**소재 유형별 처리:**

- **이미지 광고** → 이미지를 직접 Read (멀티모달) → USP 3 항목 + Creative Key Visual + ad_pattern 추출
- **영상 광고** →
  1. ffmpeg 로 키프레임 6장 추출 (8/22/40/58/75/92%) → `keyframes/{ad_id}_*_kf{1..6}.jpg`
  2. 키프레임 6장을 Gemini 멀티모달 이미지로 일괄 전송 → USP 3 항목 + Creative Key Visual + ad_pattern 분석 회신
  3. 결과는 `analysis.json` 의 `{ad_id}` 항목에 통합 (`_method: "keyframes"` 마킹)
  4. ★ **대본·오디오 추출 ❌** — 자막·텍스트 오버레이만 키프레임에서 읽음. Gemini Files API 영상 업로드 경로는 코덱·내부 처리 실패율이 높아 폐기. 시각 후킹·자막·구조 분석은 키프레임으로 충분.

**`analysis.json` 항목 예시:**
```json
{
  "ad_id": "1234567890",
  "type": "video",
  "ad_pattern": "default",
  "analysis": {
    "users_problem": "30대 민감성 피부 여성 — 기능성 화장품 자극·진정 제품 효과 없음 사이 고민 (페인 후킹)",
    "solution": "CeraShield Complex™ 4주 임상 — 자극 0등급 + 홍조 -37%. USP: 자사 독자 성분 + 권위(임상 28명) + 숫자",
    "promotion": "글로우 스타터 키트 48,000원, 30일 환불 보장, 첫 구매 -10%",
    "creative_key_visual": "민낯 클로즈업 → 4주 후 비포애프터 컷 (라이프스타일형)"
  },
  "messaging_keywords": ["민감성", "자극 0등급", "4주 임상"],
  "cta_phrase": "글로우 스타터 키트 48,000원 · 30일 환불 보장",
  "landing_url": "https://...",
  "media_paths": {"images": [...], "videos": [...]}
}
```

**`trust_anchor` 예시 (페인 없는 변주):**
```json
{
  "ad_pattern": "trust_anchor",
  "analysis": {
    "users_problem": "약함 — 페인 카피 없음. '민감 피부도 편하게' 욕구형 살짝",
    "solution": "올리브영 1등 + 별점 4.9 + 무기자차 + 산뜻촉촉 — 랭킹(권위) + 숫자(별점) 메인",
    "promotion": "OLIVE YOUNG 1+1 특가 — 채널 한정 시급성",
    "creative_key_visual": "푸른 하늘 배경 + 제품 2개 1+1 강조 + 별점 카드 (신뢰 자산형)"
  }
}
```

### Step 5. 경쟁사별 1페이지 — `{slug}/ad-creatives.md`

`analysis.json` 통합 → 경쟁사 1개당 마크다운 1페이지. 섹션:

1. 한 줄 요약 (USP / 톤 / 빈틈)
2. 활성 광고 N건 / 포맷 믹스 / 활성 기간
3. **USP 3 항목 패턴 통합** (반복되는 User's Problem · Solution · Promotion (+ Creative Key Visual 별도 축) Top 3)
4. 강조 메시지 키워드 빈도 Top 10
5. 시각 패턴 (주 컬러·모델·레이아웃)
6. 자사 빈틈 (자사 USP 와 비교 — `01_brand/brand_brief.md` 참조)

### Step 6. 대시보드 — `dashboard/index.html`

```bash
python3 02_competitor/_scripts/build_dashboard.py             # 전체 빌드
python3 02_competitor/_scripts/build_dashboard.py --no-copy   # HTML/JSON 만 갱신
```

대시보드 컴포넌트:
- 경쟁사 탭/필터 (slug 별)
- 광고 카드 그리드 (썸네일 + USP 3 항목 핵심 인용 + CTA)
- 영상 인라인 재생
- 메시지 키워드 워드클라우드
- 활성 기간 타임라인
- 정적 HTML — 로컬 더블클릭 또는 Vercel 정적 배포 가능

### Step 7. 통합 트렌드 요약 — `competitor_ads.md`

★ **이 파일이 사용자가 가장 자주 보는 산출물.** 모든 경쟁사를 한 파일에 통합하여 트렌드를 한눈에.

골격:

```markdown
# 경쟁사 광고 트렌드 요약 — {YYYY-MM-DD}

## 분석 대상
| 슬러그 | 브랜드 | 활성 광고 수 | 마지막 분석 |
|---|---|---|---|

## 강조 메시지 매트릭스 (경쟁사별 × 메시지 각도)
| 메시지 각도 | brand-a | brand-b | brand-c | ... |
|---|---|---|---|---|
| 단기간 효과 (X일·X주) | ✅ 14일 | ✅ 7일 | — | |
| 임상 수치 강조 | ✅ | — | ✅ | |
| ...

## 카피라이팅 패턴 (USP 3 항목별 Top 인용)

### ad_pattern 분포 (광고 유형별 비율)
- default: N건 / trust_anchor: N건 / promotion_anchor: N건 / hybrid: N건
- → 경쟁사가 default 가 70%면 우리는 trust_anchor 로 빈틈 공략 가능

### User's Problem · 공감언어·상황 — 반복 패턴
- (brand-a) "..." (페인/욕구/호기심/트렌드 톤 명시)
- (brand-b) "..."

### Solution · USP·근거 — 반복 패턴
- USP 차별성 Top 5
- RTB 유형 (권위·통념·숫자) 분포
- 결과 시각화 방식 Top 3

### Promotion · 지금 사야 하는 이유 — 반복 패턴
- 가격 혜택 패턴 / 리스크 제거 / 시급성

### Creative Key Visual · 시각 후킹 — 변주 분포
- 제품 단독 / 시연 / 라이프스타일 / 인포그래픽 / 신뢰 자산 비율

## CTA 문구 라이브러리 (경쟁사별)
| 경쟁사 | 대표 CTA | 가격 혜택 | 리스크 제거 |
|---|---|---|---|

## 시각 패턴 (트렌드)
- 컬러: ... / 모델: ... / 포맷: ...

## 빈틈 (자사가 비집고 들어갈 White Space)
- 어느 메시지 각도가 비어있는가
- 어느 CTA 문법이 비어있는가
- 자사 USP 3개와 매핑

## 다음 모니터링 트리거
- [ ] 신규 활성 광고 N건 이상 → 재실행
- [ ] 특정 키워드 새로 등장 → 알림
- [ ] 기존 광고 비활성 → 비교
```

---

## 분석 프레임 — USP 분석법 (★)

이 스킬은 모든 광고 소재를 **USP 분석법 3 항목 (User's Problem · Solution · Promotion) + Creative Key Visual + ad_pattern** 으로 일관 분석합니다. 메시지 3축과 시각축을 분리하고, 광고 유형은 `ad_pattern` 1개 라벨로 분류.

| 축 | 의미 · 추출 질문 | 광고 카피·이미지에서 어디를 보는가 |
|---|---|---|
| **User's Problem** | 고객의 어떤 문제를 해결하는가? (공감언어·상황. 페인/욕구/호기심/트렌드 톤) | 헤드라인 첫 줄, 영상 0-3초 자막, 모델 표정·자세, 인터뷰 톤 |
| **Solution** | 내 제품이 그 문제를 해결하는 이유? (USP 차별성 + RTB 근거 + 결과 시각화) | 서브 카피, 임상 수치, 1위 배지, 권위 인용, 비포애프터 |
| **Promotion** | 지금 구매해야 하는 이유? (가격 혜택 + 리스크 제거 + 시급성) | CTA 버튼, 가격·할인, 1+1, 환불·교환·체험, 한정 |
| **★ Creative Key Visual** | 카테고리 노이즈를 뚫는 핵심 비주얼 1컷 | 메인 이미지·시연·라이프스타일·인포그래픽·신뢰 자산 비주얼 |

**ad_pattern** (1개 라벨 강제):
- `default` (페인 후킹) / `trust_anchor` (신뢰 자산 강조) / `promotion_anchor` (할인 BOFU) / `hybrid` (2개 이상 결합)

> 정의 원본: `02_competitor/_reference/reference_analysis_method.md`

### ★ 5단 카피 매핑 (04-brief-synthesizer 와의 다리)

USP 분석법 3 항목은 04/05 의 5단 카피 (User's Pain Point · USP · Solution · Promotion · CTA) 와 다음과 같이 자연 정합:

| USP 분석법 | 5단 카피 |
|---|---|
| **User's Problem** | **1단 User's Pain Point** (페인 후킹) |
| **Solution** | **2단 USP** (자사 차별) + **3단 Solution** (작동 원리·RTB) |
| **Promotion** | **4단 Promotion** (혜택·할인·증정·리스크 제거) |
| Creative Key Visual | (별도 축 — 5단 카피와 분리되어 confirmed_brief.md § 6 비주얼 무드 시드로 이전) |

5단 5번째 **CTA** 는 `cta-library.md` 호기심 유발형 6종에서 별도 도출.

---

## 디테일 회피 룰

- ❌ Hook 점수 9/10 같은 정성 평가 (이 스킬은 패턴 추출만)
- ❌ PDP·리뷰·기사 4축 분석 (이 스킬은 광고 소재 단일 축)
- ❌ 페르소나·ICP·SWOT 통합 분석 (전략 브리프는 별도)
- ❌ 모든 광고 1건당 풀 페이지 분석 — USP 3 항목 표 + JSON 항목으로 충분

## 트러블슈팅

| 상황 | 대응 |
|---|---|
| `_inputs/` 비어 있음 | 사용자에게 `competitors.md` 작성 안내 (Step 1 양식) |
| Apify 액터 차단 | URL 형식 점검 → Page ID 딥링크로 변경 권장 |
| 모기업 페이지 노이즈 | 본문에 "공유 페이지 노출 — N건 중 M건이 {brand}" 표기 |
| ffmpeg 미설치 (영상 키프레임 추출 단계) | `brew install ffmpeg` (macOS) 또는 패키지 매니저 설치 후 재실행 |
| 영상 키프레임 분석 결과 빈약 | 영상에 자막·텍스트 오버레이가 거의 없는 BGM 영상일 가능성. 캡션·랜딩 URL·CTA 메타만으로 USP 3 항목 보조 추론 |
| Gemini 무료 한도 초과 (429) | **자동 처리** — 부분 결과 보존 + 대시보드에 🚫 무료한도 배지 표시. 24h 후 재실행 시 자동 이어서 분석 또는 즉시 완료 필요 시 `--paid` 플래그 |
| 대시보드 미디어 누락 | `build_dashboard.py --no-copy` 후 수동 `media/` 점검 |

## 다음 단계 안내

> "경쟁사별 `ad-creatives.md`, 통합 `competitor_ads.md`, 대시보드 `dashboard/index.html` 작성 완료. 다음은 `/03-pain-from-reviews` 로 고객 페인포인트를 추출하세요."

## 관련 파일

- `02_competitor/_inputs/competitors.md` — ★ 사용자 편집 통합 입력 (URL 리스트)
- `02_competitor/_inputs/README.md` — 입력 모드 가이드
- `02_competitor/_reference/reference_analysis_method.md` — USP 분석법 3 항목 정의 (User's Problem · Solution · Promotion + Creative Key Visual)
- `02_competitor/_scripts/fetch_competitor_ads.py` — Apify+Gemini 크롤·분석
- `02_competitor/_scripts/build_dashboard.py` — HTML 대시보드 빌드
- `01_brand/brand_brief.md` — 자사 USP 비교축 (Step 5·7 에서 Read)

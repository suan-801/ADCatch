---
name: 03-pain-from-reviews
description: 3축 고객 분석 — ① 자사 리뷰 → 만족 포인트(욕구) Top 3, ② 경쟁사 PDP(올리브영 우선) 부정 리뷰 → 페인포인트 Top 5, ③ Perplexity 리서치 → 트렌드 키워드·카피 시드를 통합해 `03_customer/pain_points.md` 1페이지로 저장하는 스킬. **★ 인풋은 `03_customer/_inputs/reviews_pdp.md` 한 파일에서 통합 관리** (자사·경쟁사 PDP URL + 트렌드 시드). 올리브영 PDP URL 인풋 시 `03_customer/_scripts/oliveyoung_crawler.py` (Playwright + 비로그인 cursor API + **4트랙 dedupe**) 호출 — `RATING_ASC` 트랙으로 저평점 oversampling. **★ 분석 완료 후 워드클라우드 자동 생성** — Step 6.5 에서 빈도 CSV(`visuals/wordcloud_frequency.csv`) 작성, Step 7 에서 `_scripts/wordcloud_gen.py` 자동 호출 → `visuals/{pain,desire,trend}_wordcloud.png` PNG 생성 (brand_brief.md 컬러 팔레트 6슬롯 동적 로드). 사용자가 "고객 분석해줘", "리뷰 보고 페인포인트 뽑아줘", "/03-pain-from-reviews <URL>" 등으로 요청할 때 호출. 6파일짜리 풀 페르소나·ICP·메시지 프레임 풀 산출은 하지 않음 — 광고 1단(후킹) + 2단(약속) + 카피 시드 1페이지 + 워드클라우드 2장.
---

# 03. 고객 페인포인트 (3축 리뷰 분석 → 1페이지)

## 언제 호출되는가

- "고객 분석해줘"
- "리뷰 보고 페인포인트 뽑아줘"
- "/03-pain-from-reviews https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=..."
- `01_brand` + `02_competitor` 가 이미 있고, `03_customer` 가 비어 있을 때

## 핵심 철학

> **3축으로 분석한다 — 우리는 어디가 좋고, 경쟁사는 어디가 싫으며, 시장은 어떤 단어로 말하는가.**

페르소나·ICP를 처음부터 만들지 않습니다. 자사 USP를 강화할 **만족 포인트(욕구)**, 경쟁사를 비집고 들어갈 **페인포인트**, 광고 카피에 그대로 차용할 **고객 언어**만 1페이지로 응축합니다.

| 축 | 데이터 출처 | 도구 | 산출 |
|---|------------|----|----|
| **① 자사 만족 포인트** | 자사 리뷰 (사용자 입력 또는 자사 PDP) | Read / `oliveyoung_crawler.py` (자사 올영 PDP) / Playwright | 욕구 Top 3 |
| **② 경쟁사 불만족 포인트** | 경쟁사 PDP 부정 리뷰 (올리브영 우선) | **`oliveyoung_crawler.py` (Playwright + cursor API + 4트랙 dedupe)** | 페인포인트 Top 5 |
| **③ 트렌드 키워드·카피** | 외부 시장·고객 언어 리서치 | **Perplexity** (`perplexity_ask`) | 트렌드 키워드 + 카피 시드 3개 |

---

## 인풋 (Less is More — 한 파일에 PDP URL 만)

### Mode 1 — 통합 파일 `_inputs/reviews_pdp.md` (★ 권장 · 02 패턴과 동일)

사용자가 편집하는 **유일한 파일**. 한 곳에서 자사·경쟁사 PDP·트렌드 시드를 관리. 스크립트가 이 파일만 읽고 자사 만족 포인트·경쟁사 페인포인트·트렌드 키워드를 통합 분석.

**파일:** `03_customer/_inputs/reviews_pdp.md`

**포맷:**
```markdown
## 자사 PDP (만족 포인트·욕구 Top 3 분석)
https://www.oliveyoung.co.kr/...goodsNo=A0000XXX   # {브랜드명} 대표 제품
https://{브랜드도메인}/products/{제품-슬러그}      # 자사몰 (Playwright 폴백)

## 경쟁사 PDP (페인포인트 Top 5 분석)
https://www.oliveyoung.co.kr/...goodsNo=A0000YYY   # {경쟁사 1} (직접경쟁)
https://www.oliveyoung.co.kr/...goodsNo=A0000ZZZ   # {경쟁사 2} (직접경쟁)

## 카테고리·트렌드 시드 (Perplexity 1쿼리 리서치)
{카테고리 키워드}
{타겟 페르소나·페인 키워드}
```

**규칙:**
- URL 한 줄에 하나
- 헤딩 `## 자사 PDP` / `## 경쟁사 PDP` / `## 카테고리·트렌드 시드` 로 분류
- 올리브영 PDP URL → `oliveyoung_crawler.py` 4트랙 dedupe 자동 호출 (★ 디폴트 경로)
- 자사몰·쿠팡·네이버 → Playwright MCP 폴백
- URL 뒤 `# 메모` 는 brand/제품명 힌트 (선택)
- URL 라인 맨 앞 `#` = 일시 비활성화
- `## 카테고리·트렌드 시드` 비어있으면 `01_brand/brand_brief.md` 카테고리·USP 자동 추출

### Mode 2 — 단발 URL (Mode 1 무시)

```bash
/03-pain-from-reviews "https://www.oliveyoung.co.kr/...goodsNo=A0000XXX"
```

### Mode 3 — 폴더 인풋 (자사몰·시크릿몰 리뷰 자료가 있을 때, 보조)

```
03_customer/reviews/
├── our/                # 자사 리뷰 원본 (사용자 직접 드롭, 이미지·텍스트)
└── competitor/         # 경쟁사 리뷰 원본
```

### 인풋 우선순위 + 통합

같은 호출에서 여러 인풋이 동시에 있으면 다음 순서로 처리:

```
1. 명령어 인자 (URL 직접 전달) — Mode 2
2. _inputs/reviews_pdp.md — Mode 1 (디폴트)
3. 03_customer/reviews/{our,competitor}/ 폴더 — Mode 3 (보조)
4. 01_brand/brand_brief.md 의 카테고리·USP 시드 자동 추출
```

→ 1·2·3 중 **1개 이상** 있으면 분석 가능. 3개 모두 있으면 가장 풍부한 통합 분석.
→ `## 자사 PDP` 또는 `## 경쟁사 PDP` 한 축이 비어있어도 가능한 축만 분석 (산출물에 `(자사 리뷰 미수집)` 명시).
→ Perplexity 트렌드 리서치는 **항상 실행** (1쿼리 보완).

### 캐시·재실행

- `03_customer/outputs/raw/<goodsNo>_*.{json,csv,stats.json}` 캐시가 있으면 재호출 ❌, Read 우선.
- 동일 goodsNo 24시간 이내면 자동 재사용.
- 강제 재크롤 필요 시 해당 캐시 파일 삭제 후 재실행.

> 상세 사용자 가이드: `03_customer/_inputs/README.md` (Mode 1·2·3 + FAQ)

---

## 아웃풋

- `03_customer/pain_points.md` 1개 (1페이지, ~250줄)
- (자동) `03_customer/outputs/raw/<goodsNo>_<ts>.{json,csv}` + `_stats.json` — 크롤러가 직접 저장
- (자동·★ 신설) `03_customer/visuals/wordcloud_frequency.csv` — 페인·욕구·트렌드 빈도 표 (Step 6.5)
- (자동·★ 신설) `03_customer/visuals/pain_wordcloud.png` — 경쟁사 페인 워드클라우드 (강도 색)
- (자동·★ 신설) `03_customer/visuals/desire_wordcloud.png` — 자사 욕구 워드클라우드 (brand_brief 컬러)
- (자동·옵션) `03_customer/visuals/trend_wordcloud.png` — 트렌드 키워드 (bucket=trend 행이 있을 때)
- (선택) `03_customer/reviews/raw/<source>_<note>.md` — 폴더 인풋 원본 정리

---

## 폴더 구조

```
03_customer/
├── _inputs/                                # ★ 사용자 편집 영역 (02 패턴과 동일)
│   ├── README.md                           # 입력 모드 가이드 (Mode 1·2·3 + FAQ)
│   └── reviews_pdp.md                      # ★ 통합 입력 — 자사·경쟁사 PDP URL + 트렌드 시드
├── _scripts/
│   ├── oliveyoung_crawler.py               # 올영 4트랙 dedupe 크롤러
│   ├── reviews_inputs.py                   # _inputs 파서
│   └── wordcloud_gen.py                    # ★ generic 워드클라우드 빌더 (Step 7)
├── pain_points.md                          # 최종 1페이지 산출물
├── visuals/                                # ★ 워드클라우드 자동 산출물
│   ├── wordcloud_frequency.csv             # 빈도 표 (Step 6.5 — Claude 작성)
│   ├── pain_wordcloud.png                  # 경쟁사 페인 (Step 7 자동 생성)
│   ├── desire_wordcloud.png                # 자사 욕구 (Step 7 자동 생성)
│   └── trend_wordcloud.png                 # (옵션) bucket=trend 있을 때
└── reviews/                                # Mode 3 폴더 인풋 (보조)
    ├── our/                                # 자사 리뷰 원본 (사용자 직접 드롭)
    └── competitor/                         # 경쟁사 리뷰 원본

03_customer/outputs/raw/   # ← oliveyoung_crawler.py 자동 저장 위치
└── <goodsNo>_<ts>.{json,csv,stats.json}
```

---

## 작업 순서

### Step 0. 인풋 분기

```
1. 우선순위에 따라 인풋 수집:
   ① 명령어 인자 (URL 직접 전달) — Mode 2
   ② _inputs/reviews_pdp.md 파싱 — Mode 1 (디폴트)
       - `## 자사 PDP` 섹션 URL → 자사 리뷰 수집 큐
       - `## 경쟁사 PDP` 섹션 URL → 경쟁사 리뷰 수집 큐
       - `## 카테고리·트렌드 시드` 섹션 → Perplexity 쿼리 시드
   ③ 03_customer/reviews/{our,competitor}/ 폴더 파일 — Mode 3 (보조)
   ④ 01_brand/brand_brief.md 카테고리·USP 자동 추출 (트렌드 시드 비어있을 때 fallback)

2. `## 카테고리·트렌드 시드` 와 brand_brief 모두 비어있으면 사용자에게 1회 확인.

3. 03_customer/reviews/{our,competitor} 폴더 mkdir (Mode 3 사용자 입력용).

4. 03_customer/outputs/raw/ 캐시 확인 — 동일 goodsNo 24시간 이내 데이터 있으면 재사용.
```

---

### Step 1. ① 자사 만족 포인트 — 욕구 Top 3

**리뷰 수집**
- 자사 올영 PDP URL: `python3 03_customer/_scripts/oliveyoung_crawler.py --url <URL>` 실행 → 4트랙 자동 dedupe → `outputs/raw/<goodsNo>_<ts>.csv` 생성 → Read
- 자사몰·시크릿몰·펀딩몰: Playwright MCP 로 리뷰 탭 스크롤 → 평점 4~5점, 최신순 30~50건
- 폴더 인풋: `03_customer/reviews/our/` 의 모든 파일 Read (이미지는 멀티모달, 텍스트는 직접)

**욕구 Top 3 추출**
- 4축으로 분류: **기능 / 감각 / 사회 / 정체성**
- 자사 `01_brand/brand_brief.md` RTB 와 매핑되는 것 우선
- **고객 원문 그대로 인용** — 가공 ❌
- 빈도 + 자사 USP 강화도 순으로 정렬

**자기 발등 안전장치 (★ 반드시 수행)**
- 자사 리뷰의 부정 신호도 함께 점검 — `RATING_ASC` 트랙에서 자사 자극·트러블·효과 미흡 멘션 빈도 메모.
- 경쟁사 페인을 공격하는 카피가 자사도 가지고 있는 신호면 **즉시 부메랑** → 카피에서 제외 / 또는 자사가 그 페인을 명시적으로 해소한다는 근거 확보.

---

### Step 2. ② 경쟁사 불만족 포인트 — 페인포인트 Top 5

#### 2-A. 올리브영 PDP 인 경우 (★ 디폴트 경로)

**`oliveyoung_crawler.py` 호출 — Playwright + cursor API + 4트랙 dedupe**

```bash
python3 03_customer/_scripts/oliveyoung_crawler.py \
  --url "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=<GOODS>" \
  --tracks "USEFUL_SCORE_DESC:ALL,USEFUL_SCORE_DESC:PHOTO,RATING_ASC:ALL,RATING_DESC:ALL" \
  --size 10 --sleep 0.4
```

**왜 4트랙 dedupe 인가**
- 비로그인 cursor API 는 `(sortType, reviewType)` 페어별 **100건 cap**. 단일 트랙은 100건 한계.
- 4트랙 합산 후 reviewId dedupe → **~150~400건** 확보 (페어 간 중복률에 따라 변동).
- **`RATING_ASC × ALL`** 이 페인 신호의 핵심 — ★1~2 oversampling 으로 모집단 비중(★1+★2=2%) 대비 30~60배 농축.
- `RATING_DESC × ALL` 은 만족 신호 + 체험단 유입 비교용 (5점 도움돼요 상위가 거의 동일 도입 문구이면 체험단 비중 큼 — 신뢰성 페인 발견).
- 같은 트랙 7페이지 이상 누적 시 WAF rate-limit 차단 가능 → 트랙별 자연 종료 허용.

**자동 부산물**
- `outputs/raw/<goodsNo>_<ts>.json` — raw 리뷰 전체
- `outputs/raw/<goodsNo>_<ts>.csv` — 분석용 핵심 필드 (review_id, rating, useful_point, skin_type, content 등)
- `outputs/raw/<goodsNo>_<ts>_stats.json` — 모집단 통계 (총 리뷰·평균·별점 분포·피부타입 만족도·자극도)

**실패 폴백**
- WAF rate-limit / Playwright 세션 실패: 5분 대기 후 1회 재시도. 그래도 실패면 Playwright MCP 로 PDP 리뷰 탭 직접 스크롤 → 평점 1~2점 30건 + 최신순 30건.

#### 2-B. 자사몰·쿠팡·네이버 인 경우

- Playwright MCP 로 PDP 리뷰 탭 펼치기 → 평점순 정렬 → 1~2점 30건
- 또는 `03_customer/reviews/competitor/` 폴더 파일 Read

#### 2-C. 페인포인트 Top 5 추출 (★ 핵심 산출물)

**4축 분류 + 강도 표기**
- 축: **자극·트러블 / 효과 미흡 / 사용감(끈적·기름·향) / 신뢰성·가성비**
- 강도 시그널 (medicube_pdrn_painpoints v0.2 검증된 방법):
  - 🔴🔴🔴 = ★1 멘션 빈도 가장 높음 + 도움돼요 1만+ 리뷰 포함
  - 🔴🔴 = ★1 빈도 높음 + 도움돼요 1천+
  - 🟠 = ★1~3 분산 멘션
  - 🟡 = ★3~4 부정 멘션
  - 🟢🔵 = 비교 탐색 / 광고 피로 / 디바이스 의존 등 부수적

**키워드 빈도 표 (Top 5 각각)**
- ★1 본문 텍스트마이닝: 페인 키워드 멘션 빈도 (대략값 OK — "~25", "~10")
- 도움돼요 점수 가중: 도움돼요 1만+ 리뷰는 별도 표시 (잠재 고객 검색 진입점)

**대표 리뷰 인용**
- 페인포인트당 3~5건. **★ + 도움돼요 점수** 함께 표기.
- 원문 그대로 — 가공·요약 ❌. (단, 닉네임·실명·구체 위치 마스킹)

**모집단 메타 명시**
- stats.json 에서: 총 리뷰 수, 평균 별점, 별점 분포(★5/4/3/2/1 %), 피부타입 만족도, **자극도 (자극없이 순해요 X% / 보통 / 자극 느껴짐 X%)**.
- "자극 느껴짐 2%" = 모집단 N건의 잠재 부작용 — 정량 근거로 인용.

---

### Step 3. ③ 트렌드 키워드·카피라이팅 — Perplexity

**1쿼리 통합 리서치**

```
도구: mcp__perplexity__perplexity_ask
모델: sonar-pro (또는 sonar-reasoning)
쿼리 템플릿:

"<카테고리(예: 기미·잡티 케어 세럼)> 시장에서 2025~2026년 한국 소비자가
실제로 사용하는 표현·해시태그·후킹 카피를 알려주세요.
다음을 포함:
1. 트렌드 키워드 Top 10 (인스타·블로그·맘카페 자연 발화 기준)
2. 효과·기간을 강조한 카피 패턴 5개
   (예: 'N일 만에 톤 변화!', 'X일/X시간 안에', 'N% 개선')
3. 부정 발화로 자주 나오는 페인 표현 Top 5
4. 경쟁사 광고가 차용 중인 후킹 문장 3개
근거 인용·출처 함께."
```

**카피 시드 3개 도출**
- Perplexity 결과 + Step 1·2 의 자사 욕구·경쟁 페인을 결합.
- 효과 약속형(기간·신체부위·감정 단어) 위주.
- 카피 시드 1개 = "후킹 문장 1개 + 차용 단어 2~3개 + 활용 채널".

> ⚠️ **의약품 연상 단정 표현 금지** — "드라마틱한 변화" 같은 표현은 의문문으로 변환 ("드라마틱한 변화 없으셨죠?").
> ⚠️ **경쟁사명 직접 비방 금지** — "베지톨로지보다" → "5만원대 OO보다"로 변환.

---

### Step 4. 페인 ↔ 욕구 페어링 3세트 (★ 광고 메시지 골격)

광고 1세트 = **1단(후킹·페인) + 2단(약속·욕구) + 3단(근거·USP)**.

- 1세트 = 페인 1개 + 욕구 1개 + 자사 USP 1개
- 자사 `01_brand/brand_brief.md` USP 3개와 매핑
- 매핑 강도 ★★★ ★★ ★ 표기
- Step 3 의 **카피 시드를 1단 후킹 문장**으로 직접 삽입

> **★ 5단 카피 매핑** (04-brief-synthesizer 가 본 페어링 Set A 를 5단 카피로 변환):
> - 페어링 **1단 페인** → 5단 **1단 User's Pain Point** (의문문 변환)
> - 페어링 **3단 USP** → 5단 **2단 USP** (자사 차별 한 줄)
> - 페어링 **2단 욕구** + brand_brief RTB → 5단 **3단 Solution** (메커니즘 + 임상)
> - (페어링에 없음 — brand_brief 가격) → 5단 **4단 Promotion** (할인·환불·증정)
> - (페어링에 없음 — cta-library) → 5단 **5단 CTA** (호기심 유발형)

---

### Step 5. 차용 단어장 (광고 카피용 VoC)

| 분류 | 단어 (高빈도) | 출처 |
|----|------------|----|
| 페인 단어 | "좁쌀여드름", "모낭염", "자극", "기름짐" | 경쟁사 ★1 부정 리뷰 |
| 욕구 단어 | "촉촉", "톤업", "광채", "환해짐" | 자사 긍정 리뷰 |
| 트렌드 단어 | "쫀쫀", "결잡", "유리피부", "속광" | Perplexity |

---

### Step 6. 저장

`03_customer/pain_points.md` 마크다운 1페이지로 저장.

```markdown
# <자사 브랜드> 고객 분석 — 페인 & 욕구 1페이지

> 작성일: YYYY-MM-DD
> 인풋:
>   ① 자사 리뷰 N건 (소스)
>   ② 경쟁사 <올리브영 goodsNo> N건 (`oliveyoung_crawler.py` 4트랙 dedupe, ★1 N건)
>   ③ Perplexity 1쿼리 (카테고리)

## 0. 표본 한계
- 모집단 / 표본 크기 / 표본 별점 분포 / oversampling 의도 명시

## 1. ① 자사 만족 포인트 — 욕구 Top 3
| # | 욕구 (1줄) | 원문 인용 2건 | 자사 RTB 매핑 |
|---|---------|----------|----------|

## 2. ② 경쟁사 불만족 포인트 — 페인포인트 Top 5
> 출처: <경쟁사명> 올영 PDP (goodsNo: ...) — `oliveyoung_crawler.py` 4트랙, 표본 N건 (★1 N건 / ★3 N건)
> 모집단: 총 N건 / 평균 ★X.X / 자극 느껴짐 X%

| # | 페인 (1줄) | 강도 | 키워드 빈도 | 대표 리뷰 (★+도움돼요) | 자사 흡수 가능성 |
|---|---------|----|----|----|----|
| 1 |  | 🔴🔴🔴 | 좁쌀여드름~25, 모낭염~10 | ★1 도움 11,700: "..." | ★★★ |

## 3. ③ 트렌드 키워드·카피라이팅 (Perplexity)
**트렌드 키워드 Top 10**: ...
**카피 시드 3개**:
1. "N일 만에 톤 변화!"
2.
3.

## 4. 페인 ↔ 욕구 페어링 3세트 (★ 광고 시드)
### 세트 A — ★★★ (Hero)
- 1단 후킹 (페인): "..."
- 2단 약속 (욕구): "..."
- 3단 근거 (USP): "..."
### 세트 B — ★★
### 세트 C — ★

## 5. 차용 단어장 (VoC)

## 6. 자기 발등 안전장치
- 자사 리뷰 자체 부정 신호 점검 결과
- 공격할 페인 / 피해야 할 페인

## 7. 다음 스킬 전달
- /04-brief-synthesizer 인풋: 페어링 3세트 + 카피 시드 + 차용 단어장
```

---

### Step 6.5. 빈도 CSV 작성 (★ 워드클라우드 인풋)

Step 1·2·5 에서 도출한 페인·욕구·트렌드 단어를 한 파일로 저장.

**파일:** `03_customer/visuals/wordcloud_frequency.csv`

**스키마:**
```csv
label,count,bucket,category
좁쌀여드름,25,pain,h
모낭염,10,pain,h
끈적임,18,pain,m
두 통 효과 X,8,pain,l
환해짐,15,desire,func
한 방울로 충분,12,desire,sense
임산부도 매일,9,desire,social
자존감 챙겨주는,6,desire,identity
유리피부,7,trend,
속광,5,trend,
```

**컬럼 규칙:**
- `label` — 워드클라우드에 그대로 표시될 단어/구 (Step 1·2·5 에서 추출)
- `count` — 멘션 빈도 (Step 2 도움돼요 가중 합산 또는 단순 멘션 빈도)
- `bucket` — `pain` / `desire` / `trend` 중 하나
- `category` — 색상 매핑용 sub-bucket:
  - `pain` 의 경우: `h` (🔴🔴🔴 강도 최상) / `m` (🔴🔴) / `l` (🟠) / `n` (🟢, 부수)
  - `desire` 의 경우: `func` (효과·증거) / `sense` (감각·제형) / `social` (신뢰·인증) / `identity` (자존감·일상)
  - `trend` 의 경우: 비워둠

**최소 행 수:** 페인 5~15개, 욕구 5~15개 권장 (너무 적으면 시각적 풍부함이 떨어짐).

---

### Step 7. 워드클라우드 자동 생성 (★ 신설)

Step 6.5 의 `wordcloud_frequency.csv` 를 읽어 PNG 2~3장 자동 생성.

```bash
python3 03_customer/_scripts/wordcloud_gen.py
```

**산출:**
- `03_customer/visuals/pain_wordcloud.png` — `bucket=pain` 행을 강도(h/m/l/n) 컬러로 렌더링
- `03_customer/visuals/desire_wordcloud.png` — `bucket=desire` 행을 brand_brief 6슬롯 컬러로 렌더링
- `03_customer/visuals/trend_wordcloud.png` — (옵션) `bucket=trend` 행이 있으면 생성

**스크립트 동작:**
- `01_brand/brand_brief.md` 컬러 팔레트 6슬롯 표에서 HEX 6개 자동 추출 (실패 시 폴백 컬러)
- 배경: `BG-Light` / 욕구 메인: `BRAND-Signature` / 텍스트: `TEXT-Primary`
- 페인 강도 컬러: `h=#D63C2F` (크랜베리 레드) → `n=#7A6651` (워밀 그레이) 4단계
- 한글 폰트: `/System/Library/Fonts/AppleSDGothicNeo.ttc` (macOS 시스템)
- 의존성: `pip install wordcloud matplotlib` (미설치 시 친절한 안내 메시지)

**옵션 (수동 호출 시):**
```bash
python3 03_customer/_scripts/wordcloud_gen.py \
  --csv 03_customer/visuals/wordcloud_frequency.csv \
  --out-dir 03_customer/visuals \
  --brand-brief 01_brand/brand_brief.md
```

**스킬 후속 안내**
- v1 후 사용자가 PNG 보고 "끈적임 더 크게" / "페인 단어 추가해줘" 식 자연 반복 요청 가능.
- 빈도 조정은 `wordcloud_frequency.csv` 의 `count` 값을 늘리거나 행을 추가한 후 Step 7 재실행.

---

## `oliveyoung_crawler.py` 운용 가이드

```
- 위치: 03_customer/_scripts/oliveyoung_crawler.py
- 의존: playwright (sync_api). 미설치 시 `pip install playwright && playwright install chromium`.
- 캐시: outputs/raw/<goodsNo>_<ts>.{json,csv,stats.json} — 동일 goodsNo 24시간 이내면 재호출 ❌, Read 우선.
- 트랙 옵션: --tracks "USEFUL_SCORE_DESC:ALL,USEFUL_SCORE_DESC:PHOTO,RATING_ASC:ALL,RATING_DESC:ALL"
  - 페인만: "RATING_ASC:ALL"
  - 풀 분석: 4트랙 디폴트
- rate-limit: 0.4초 sleep + 트랙별 자연 종료. 같은 IP 에서 7페이지 이상 누적 시 WAF 차단 가능 → 5분 대기 후 재시도.
- 100건 cap 우회: 단일 (sortType, reviewType) 페어는 100건이 한계 → 4트랙 dedupe 필수.
```

---

## 카피 차용 룰 (반드시 명시)

✅ 차용
- 고객 원문 단어 그대로 (기간·신체부위·감정 단어)
- 1단 후킹은 **의문문 변환** ("드라마틱한 변화 없으셨죠?")
- 트렌드 카피 패턴 (기간형·% 형) 차용
- ★1 도움돼요 1만+ 리뷰의 키워드는 잠재 고객 검색 진입점 — 카피 헤드라인 1순위

❌ 금지
- 경쟁사명 직접 비방 — "베지톨로지보다" → "5만원대"로 변환
- "드라마틱한 변화" 등 의약품 연상 단정 표현 → 의문문으로만
- 1단 단독 사용 ❌ — 반드시 2단(약속) 즉시 페어링
- Perplexity 결과 출처 미표기 사용 ❌
- 자사도 가지고 있는 페인을 공격하는 카피 (자기 발등)

---

## 디테일 회피 룰 (Less is More)

- 페르소나 3종 작성 ❌ (이 스킬은 페인↔욕구·카피 시드만)
- ICP 정의 ❌
- 5단계 메시지 프레임 풀 산출물 ❌ (페어링 3세트가 그 골격)
- 4파일·6파일 풀 페르소나 산출물 ❌ → 그건 `2-3_customer_market_analysis/customer-analyzer` 스킬의 역할.

---

## 토큰·비용 가이드

| 단계 | 도구 | 예상 비용 |
|----|----|--------|
| Step 1 자사 리뷰 (자체 크롤러·Playwright) | `oliveyoung_crawler.py` | $0 (셀프호스팅) |
| Step 2 경쟁사 4트랙 dedupe | `oliveyoung_crawler.py` | $0 (~5~10분) |
| Step 3 Perplexity 1쿼리 | sonar-pro | ~$0.04 |
| Step 4·5·6 합성·저장 | Claude Sonnet | (스킬 호출 포함) |
| **총 1회 분석** | | **~$0.05~$0.10** |

> Apify 액터 대비 비용 ↓ + 수집량 ↑ + RATING_ASC 트랙으로 페인 신호 농축. 단점: WAF rate-limit 시 10분 정도 추가 대기.

---

## 출력 검증 체크리스트

- [ ] `03_customer/pain_points.md` 1페이지 (~250줄) 저장
- [ ] 자사 만족 포인트(욕구) Top 3 — 각 항목 원문 인용 2건 + RTB 매핑
- [ ] 경쟁사 페인포인트 Top 5 — 강도(🔴🔴🔴~🟢) + 키워드 빈도 표 + 대표 리뷰(★+도움돼요) + 자사 흡수 강도
- [ ] `oliveyoung_crawler.py` 4트랙 dedupe 호출 — 표본 N건, ★1 N건 명시
- [ ] stats.json 통계 메타 인용 — 총 리뷰·평균 별점·자극도 %
- [ ] Perplexity 1쿼리 → 트렌드 키워드 Top 10 + 카피 시드 3개
- [ ] 페인↔욕구 페어링 3세트 — 1단/2단/3단 + ★ 매핑
- [ ] 차용 단어장 (페인·욕구·트렌드 3분류)
- [ ] **자기 발등 안전장치** — 자사 자체 부정 신호 점검 결과 명시
- [ ] 경쟁사명 직접 비방·의약품 연상 표현 0건
- [ ] (★ 신설) `03_customer/visuals/wordcloud_frequency.csv` 저장 — 페인 5~15행 + 욕구 5~15행
- [ ] (★ 신설) `03_customer/visuals/pain_wordcloud.png` + `desire_wordcloud.png` 자동 생성 — `wordcloud_gen.py` 호출 로그 확인

---

## 관련 파일

- `03_customer/_inputs/reviews_pdp.md` — ★ 사용자 편집 통합 입력 (자사·경쟁사 PDP URL + 트렌드 시드)
- `03_customer/_inputs/README.md` — 입력 모드 가이드 (Mode 1·2·3 + FAQ)
- `03_customer/_scripts/reviews_inputs.py` — 통합 입력 파일 파서 (02 의 `competitor_inputs.py` 와 동일 패턴)
- `03_customer/_scripts/oliveyoung_crawler.py` — 올영 4트랙 dedupe 크롤러
- `03_customer/_scripts/wordcloud_gen.py` — ★ generic 워드클라우드 빌더 (Step 7 자동 호출)
- `03_customer/outputs/raw/` — 원본 리뷰·CSV·stats.json 자동 저장
- `03_customer/visuals/wordcloud_frequency.csv` — ★ 워드클라우드 인풋 (Step 6.5)
- `03_customer/visuals/{pain,desire,trend}_wordcloud.png` — ★ 자동 산출 워드클라우드
- `03_customer/pain_points.md` — 최종 1페이지 산출물
- `01_brand/brand_brief.md` — 자사 USP·RTB·카테고리 (Step 1·4·5 인풋)
- `02_competitor/competitor_ads.md` — 경쟁사 광고 USP (Step 4 페어링 시 cross-reference)

---

## 다음 단계 안내

> "03_customer/pain_points.md 작성 완료 + 워드클라우드 자동 생성 완료 (visuals/pain_wordcloud.png · visuals/desire_wordcloud.png). 페어링 3세트 + 카피 시드는 다음 광고 제작 스킬들이 자동 인용합니다:
> - `/05-ad-image-nanobanana` — 5단 카피 도출 시 페어링 3세트를 1·2단으로 인용
> - `/07-carousel-nanobanana` — 카드뉴스 슬라이드 1·2번에 페인↔욕구 매핑
> - `/08-landing-page` — Hero·USP·신뢰 섹션 카피 시드로 인용
>
> (04-storyboard-brief 는 2026-05-11 deprecated — 05 광고 이미지 스킬로 통합됨)"

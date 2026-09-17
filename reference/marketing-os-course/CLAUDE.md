# Performance Marketing OS — 클로드코드 가이드

> 1인 마케터·소상공인이 **광고 소재 1세트 + 데이터 리포트**를 클로드코드로 만드는 단순한 OS.
> 철학: **Less is More** — 필요한 만큼만, 매 단계 1페이지로.

## 작업 흐름

```
[09] 트래킹 셋업     GA4·Clarity·Meta → .mcp.json / 09_tracking/.env (★ 최초 1회)
       ↓
[01] 브랜드 분석     URL → brand_brief.md (+ logos·products 에셋)
       ↓
[02] 경쟁사 분석     Meta 광고라이브러리 → competitor_ads.md
       ↓
[03] 고객 분석       경쟁사 PDP 리뷰 → pain_points.md
       ↓
[04] 브리프 합성     /04-brief-synthesizer → confirmed_brief.md
       ↓
[05~08] 크리에이티브  이미지·영상·카드뉴스·랜딩 (v1 즉시 → 사후 검수)
       ↓
[10~12] 데이터 분석   일일 슬랙·대시보드·기간 리포트
```

## 폴더 규칙

| 폴더 | 용도 | 산출물 |
|---|---|---|
| `01_brand/` | 자사 분석 | `brand_brief.md` |
| `01_brand/logos/` | 로고 원본 | (사용자가 넣음, 05 reference) |
| `01_brand/products/` | 제품 이미지 | (사용자가 넣음, 05 reference) |
| `02_competitor/` | 경쟁사 광고 분석 | `competitor_ads.md` |
| `03_customer/` | 고객 페인포인트 | `pain_points.md` |
| `03_customer/reviews/` | 리뷰 원본 (URL이 안 될 때) | (사용자가 넣음) |
| `04_brief/` | 브리프 합성 (3C → USP 4축) | `confirmed_brief.md` (★ /04-brief-synthesizer 자동 산출 — 05/07/08 분기 A 진입점) + `archive/{캠페인-슬러그}_brief.md` |
| `05_ad_image/` | 광고 이미지 (NanoBanana) | `{YYYY-MM-DD}_{캠페인-슬러그}/*.png` ★ |
| `06_ad_video/` | 광고 영상 (Higgsfield) | `{YYYY-MM-DD}_{캠페인-슬러그}/*.mp4` ★ |
| `07_carousel/` | 카드뉴스 캐러셀 슬라이드 (NanoBanana) | `{YYYY-MM-DD}_{캠페인-슬러그}/{브랜드}_{캠페인}_carousel-v{N}_slide{i}.png` ★ |
| `08_landing/` | 랜딩페이지 (NanoBanana + HTML 단일 파일) | `{YYYY-MM-DD}_{캠페인-슬러그}/index-v{N}.html` + `{YYYY-MM-DD}_{캠페인-슬러그}/images/*.png` ★ |
| `09_tracking/` | 트래킹 셋업 산출물 (Meta `.env`, GA4 서비스 계정 키 등) | `.env`, `.env.example` |
| `10_daily/` | 일일 슬랙 리포트 (10-daily-slack 스킬) | `{brand}/{YYYY-MM-DD}-*.{txt,json}` |
| `11_dashboard/` | 대시보드·CRO·모니터링 (11-monitor 스킬) | `dashboards/`, `cro/`, `recommendations/`, `setup/` |
| `12_period/` | 기간 리포트 (12-period-report 스킬) | `{brand}/*.{md,html,pdf}` |
| `_shared/` | 공용 라이브러리 (10·11·12 스킬 런타임 자원) | `scripts/`, `lib/`, `templates/`, `config/`, `data/`, `logs/` |

## 스킬 호출 규칙

각 폴더는 같은 번호의 스킬 1개와 1:1 매핑.

- `/04-brief-synthesizer` → `04_brief/confirmed_brief.md` (★ 3C → USP 4축 1세트 (① Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion(+CTA)) + 컨셉 한 줄 + 앵글 자동 합성)
- `/01-brand-from-url <URL>` → `01_brand/brand_brief.md`
- `/02-competitor-from-adlib <URL>` → `02_competitor/competitor_ads.md`
- `/03-pain-from-reviews <URL>` → `03_customer/pain_points.md`
- ~~`/04-storyboard-brief`~~ → (deprecated 2026-05-11) — 후속 스킬은 위 `/04-brief-synthesizer` (2026-05-19 신설)
- `/05-ad-image-nanobanana` → `05_ad_image/*.png` (★ 카피 자동 도출 + v1 후 USP 4축 채팅 동봉)
- `/06-ad-video-higgsfield` → `06_ad_video/*.mp4`
- `/07-carousel-nanobanana` → `07_carousel/*.png` (★ 인스타 카드뉴스 N장, 시각 일관성 5축 강제, v1 후 시나리오 채팅 동봉)
- `/08-landing-page` → `08_landing/{토픽}/index-v{N}.html` (★ 체험단·이벤트·단일 LP 3타입, 신청 CTA 는 구글폼·Tally 외부 URL, v1 후 시나리오 채팅 동봉)
- `/09-tracking-setup` → `.mcp.json` (analytics-mcp · clarity 항목 env 값 채움) + Meta Developer App + System User Token (`ads_read` 만, 만료 없음) + `09_tracking/.env` 4개 변수 (.gitignore 등록) — 최초 1회 셋업. `SETUP_GUIDE.md` 를 single source of truth 로 단계별 안내

스킬을 명시적으로 부르지 않아도, "브랜드 분석해줘" / "경쟁사 광고 봐줘" / "고객 분석해줘" / "브리프 만들어줘" / "광고 컨셉 도출해줘" / "USP 4축 시안" / "광고 시안 짜줘" / "카드뉴스 만들어줘" / "캐러셀 만들어줘" / "랜딩페이지 만들어줘" / "체험단 페이지" / "이벤트 페이지" / "셋업 도와줘" / "트래킹 환경 만들어줘" / "GA4 연결" / "Clarity 연결" / "Meta API 연결" 같은 자연어 요청에서 자동 라우팅됩니다. "브리프 만들어줘" / "광고 컨셉 도출" 는 **04 로 라우팅** (3C → confirmed_brief.md). "스토리보드 만들어줘" / "광고 시안 짜줘" 는 05 로 라우팅 (구 04-storyboard-brief deprecated). "카드뉴스" / "캐러셀" / "인스타 슬라이드" 는 07 로 라우팅. "랜딩페이지" / "LP" / "체험단 페이지" / "이벤트 페이지" 는 08 로 라우팅. 단, **데이터 분석 슬라이드·대시보드는 08 범위 ❌** — `10_daily/`·`11_dashboard/`·`12_period/` (10~12 스킬) 에서 처리.

## 에이전트 라우팅

복합 캠페인 요청은 5명 직무 에이전트로 위임. Claude Code 가 색별로 작업 상태 표시 → 강의 5강 슬라이드의 *5색 동시 작업* 시연 그대로 재현.

### ★ 트리거 우선순위 (가장 중요)

1. **슬래시 명시 호출** (`/02-competitor-from-adlib ...` 등) → **항상 메인 세션이 직접 실행** (에이전트 위임 ❌, 오버헤드 0). 사용자가 슬래시로 호출했다는 건 단일 산출물 의도.
2. **자연어 단발 요청** (예: "경쟁사 2개만 빠르게", "이 광고 1장 분석") → **메인 세션이 해당 슬래시를 직접 호출**. 에이전트 안 띄움.
3. **자연어 복합 요청** (2개 이상 다른 산출물 + 병렬화 효용 있음) → **에이전트 위임**. 메인 세션이 분배·회수.

→ 헷갈리면 사용자에게 `슬래시 직접 호출 / 에이전트 위임 중 어느 쪽?` 한 줄 확인.

### 에이전트 카탈로그 (복합 요청 시 라우팅 대상)

| 요청 키워드 | 위임 대상 | 컬러 |
|---|---|---|
| 경쟁사·고객·페르소나·업계 벤치마크 분석 | `researcher` | 🔵 파랑 |
| 카피·메시지·USP 4축 후보·슬랙 메시지 | `copywriter` | 🟠 주황 |
| 이미지·영상·카드뉴스·랜딩페이지·차트 비주얼 | `creator` | 🟣 보라 |
| ROAS·CPM·대시보드·캠페인 회고·CRO 리포트·기간 리포트 | `analyst` | 🔴 빨강 |
| 캠페인 브리프·메시지 전략·결재선·5월 안 1·2·3 | `planner` | 🩷 핑크 |

복합 요청 (예: *"4월 결과 분석 + 5월 전략 + 경쟁사 + 광고 소재"*) 은 자동 분해되어 위 5명에게 병렬·직렬로 위임됩니다. 메인 세션이 오케스트라 지휘자, 에이전트는 각자 컨텍스트·메모리·도구를 가진 직무 단위 일꾼.

### 위임 금지 (사용자 직접 영역)

1. **자사 분석** — 브랜드 정체성·미션·USP는 사용자만 결정 → `/01-brand-from-url <URL>` 직접
2. **전략 의사결정** — 안 1·2·3 제시까지만 (planner), 선택은 사용자
3. **트래킹·인프라** — GA4·Meta·Clarity 1회성 셋업은 직접 처리 → `/09-tracking-setup`
4. **단일 산출물 미세 작업** — *"이 카피 한 줄만 다듬어줘"* 같은 건 메인 세션이 즉답 (에이전트 오버헤드 ❌)

원칙: **의사결정 권한은 항상 사용자**. 정리·후보 제시·수집은 위임, 결정은 위임 ❌.

### 단일 산출물은 슬래시 직접 호출 (에이전트 안 띄움)

**리서치** (정보 수집·정리):
- 경쟁사 1~2개 분석 → `/02-competitor-from-adlib <URL>`
- 고객 페인포인트 1세트 → `/03-pain-from-reviews <URL>`

**크리에이티브** (산출물 생성):
- 광고 이미지 1장 → `/05-ad-image-nanobanana`
- 광고 영상 1편 → `/06-ad-video-higgsfield`
- 카드뉴스 1세트 → `/07-carousel-nanobanana`
- 랜딩페이지 1개 → `/08-landing-page`

**리포트**:
- 일일 리포트 → `/10-daily-slack`
- 기간 리포트 → `/12-period-report`

**에이전트로 전환하는 시점** = 2개 이상 산출물 + 의존 관계 + 병렬화 가치 (예: *"4월 회고 + 5월 전략 + 경쟁사 4개 + 광고 6장"*). 단일 스킬 호출은 규모와 무관하게 슬래시 직접이 정답 — 경쟁사 4개를 한 번에 분석하더라도 `/02-competitor-from-adlib` 한 번이면 충분.

### 병렬·직렬 데모 시나리오 (강의 5강 [21]~[27])

```
사용자 한 줄: "4월 캠페인 결과 분석 + 5월 전략 + 경쟁사 트렌드 + 광고 소재"

1단계 병렬: 🔴 analyst (4월 회고)  +  🔵 researcher (경쟁사 5월)
              ↓ 결과 메인으로 회수
2단계 직렬: 🩷 planner (5월 브리프 안 1·2·3 → 사용자 선택)
              ↓ 선택된 안
3단계 병렬: 🟠 copywriter (카피 3안)  +  🟣 creator (이미지 6장)

→ 30~40분 후 5종 산출물:
   12_period/4월회고.{html,pdf}
   02_competitor/5월트렌드.md
   04_brief/brief_5월_2026-05-14-v1.md
   카피 3안 (채팅 동봉)
   05_ad_image/{브랜드}_5월_*.png × 6
```

## 핵심 룰

### 1. 1페이지 원칙
모든 분석 산출물은 마크다운 1페이지(~200줄). 4파일·5파일짜리 풀스펙 분석은 이 OS의 범위가 아닙니다.

### 2. 사후 검수 정책 (★ 사전 컨펌 게이트 폐기)
`05-ad-image-nanobanana` 는 카피·이미지를 한 번에 만들고, **v1 출력 직후 USP 4축을 채팅에 동봉**합니다. 사용자는 v1 결과 보고 "① 더 짧게" / "④ 1+1으로" 식으로 자연 반복 → v2 호출.
- ✅ v1 후 사용자가 카피·비주얼 검수 → 수정 요청 → v2
- ❌ 사전 컨펌용 HTML 스토리보드 생성
- **분기 A** (디폴트 추천 흐름): `/04-brief-synthesizer` 가 `04_brief/confirmed_brief.md` 자동 생성 → 05/07/08 이 § 3 USP 4축 그대로 인용 → v1 즉시
- **분기 B** (분기 A 미사용 시): 05/07/08 이 01/02/03 동적 로드 + `references/` 5 모듈로 in-memory 도출 → v1 생성

### 3. 톤·비주얼은 컨텍스트에서 동적 로드
스킬 정의에 브랜드명·컬러·톤 규칙을 하드코드하지 마세요. 런타임에 `01_brand/brand_brief.md` 에서 로드합니다.

### 4. NanoBanana 저장 경로 항상 명시
NanoBanana MCP 호출 시 `output_path` 파라미터에 `05_ad_image/{파일명}.png` 항상 지정. 가능하면 `01_brand/logos/` · `01_brand/products/` 의 실제 파일을 reference image 로 첨부해 비주얼 일관성 확보.

### 5. 파일·폴더명 규칙 (★ 날짜·캠페인 서브폴더 의무)

**서브폴더 규칙** (★ 2026-05-25 도입):
- 05·06·07·08 의 모든 산출물은 **`{nn_folder}/{YYYY-MM-DD}_{캠페인-슬러그}/`** 서브폴더 안에 저장
- 날짜 = 시안 **생성일** (캠페인 시작일 아님). 같은 캠페인을 며칠에 걸쳐 재생산하면 날짜별 서브폴더가 자연 분리됨
- 캠페인-슬러그 = `04_brief/confirmed_brief.md` 의 frontmatter `campaign:` 값 그대로 (예: `mybrand-summer-launch`). 분기 B (brief 없음) 면 사용자 컨셉 한 줄에서 영소문자+하이픈으로 자동 슬러그 (예: `mybrand-8sec-glow`)
- 예: `05_ad_image/2026-05-25_mybrand-summer-launch/`

**파일명** (서브폴더 안의 파일):
- 광고 이미지: `{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-v{N}.png`
  - 예: `05_ad_image/2026-05-25_mybrand-summer-launch/mybrand_summer-launch_meta-feed_conceptHero-v1.png`
- 광고 영상: `{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-{모델키}-v{N}.mp4`
  - 모델키: `kling30` / `veo31` / `veo3` / `seedance20` / `wan27` / `hailuo` (소문자, 점·하이픈·언더스코어 없음 — GitHub `higgsfield-ai/cli` 모델 ID 변형)
  - 예: `06_ad_video/2026-05-25_mybrand-1plus1/mybrand_1plus1_meta-reel_conceptA-kling30-v1.mp4`
- 카드뉴스 슬라이드: `{브랜드}_{캠페인}_carousel-v{N}_slide{i}.png` (i = 01~NN)
  - 예: `07_carousel/2026-05-25_mybrand-summer-launch/mybrand_summer-launch_carousel-v1_slide01.png` ~ `slide05.png`
- 랜딩페이지: `08_landing/{YYYY-MM-DD}_{토픽-슬러그}/index-v{N}.html` + `images/{slot}.png`
  - 토픽 슬러그: 영소문자 + 하이픈. 예: `08_landing/2026-05-25_mybrand-tester/index-v1.html`
  - 이미지 슬롯: `hero` / `content-1` / `content-2` ...
- 수정 요청 시 v 증가 (덮어쓰기 ❌). v2~ 는 **같은 서브폴더 안** (날짜는 v1 생성일 그대로 유지 — 캠페인 일관성)
- 며칠 뒤 새 시안 재시작이면 새 날짜 서브폴더 생성

## 언어

- 응답·문서·주석 → **한국어**
- 변수명·함수명·파일명 → 영어

## MCP 의존성

`.mcp.json` 에 설정:
- **NanoBanana** — 이미지 생성 (필수, 05 이미지 스킬)
- **Higgsfield Skills 팩 (OAuth)** — 영상 생성 (필수, 05 영상 스킬). `npm install -g @higgsfield/cli` → `higgsfield auth login` (브라우저 5초) → `npx skills add higgsfield-ai/skills` 로 `/higgsfield:generate` 슬래시 활성화. cloud API key 방식(HF_API_KEY)은 자체 모델(DoP·Soul)만 노출되므로 외부 모델(Kling/Veo/Seedance) 비교에는 OAuth 경로 사용
- **analytics-mcp** — GA4 공식 패키지 (09 트래킹 셋업). `pipx run analytics-mcp` 로 실행. gcloud ADC + `GOOGLE_PROJECT_ID` env 필요
- **clarity** — Microsoft Clarity 공식 npm 패키지 `@microsoft/clarity-mcp-server` (09 트래킹 셋업). `npx -y` 로 실행. `CLARITY_API_TOKEN` + `CLARITY_PROJECT_ID` env 필요. 일 10회 호출 한도 주의
- (옵션) GPT Image — 사용자가 명시 요청 시

**MCP 가 아닌 외부 도구** (Bash 도구로 Python 스크립트 호출):
- **Meta Marketing API (SDK 트랙, 보안 우선 디폴트)** — Python `facebook-business` SDK 를 `_shared/scripts/lib/meta_client.py` 헬퍼로 래핑. 자격증명은 `09_tracking/.env` 의 4개 변수 (`META_APP_ID·META_APP_SECRET·META_ACCESS_TOKEN·META_AD_ACCOUNT_ID`). 토큰은 Business Manager 에서 발급한 **System User Access Token** (`ads_read` 단일 스코프, 만료 Never, 특정 광고 계정만 자산 할당) — read-only + 자산 격리 + 영구. Claude Code 자연어 쿼리 + cron 자동 리포트 (10·11·12) 양쪽 모두 이 한 트랙으로 통일. CLI OAuth 트랙 (`meta ads ...`) 은 SETUP_GUIDE § 4.8 부록으로 강등 — BM Admin 권한 없는 1인 운영자의 일회성 탐색 전용, 보안 가드 5개 의무 (ads_read 만·계정 선택·읽기 명령만 화이트리스트·토큰 위치 확인·패키지 publisher 검증).

---

*이 워크스페이스는 클로드코드 강의 "심플한 퍼포먼스 마케팅 OS" 의 샘플입니다. 자세한 사용법은 `README.md` 참고.*

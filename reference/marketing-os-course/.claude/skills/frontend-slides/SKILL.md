---
name: frontend-slides
description: 애니메이션이 풍부한 HTML 프레젠테이션을 처음부터 만들거나 PPT를 웹으로 변환합니다. 사용자가 발표 자료·피치덱·강의 슬라이드·내부 보고서 슬라이드를 만들고 싶을 때, 또는 .pptx 파일을 웹 형태로 변환하고 싶을 때 사용합니다. 디자인 비전공자가 추상적인 선택지 대신 시각 미리보기를 통해 자기 취향을 발견하도록 도와줍니다.
allowed-tools: Read, Write, Edit, Bash, Glob, AskUserQuestion, WebFetch
model: opus
---

# Frontend Slides — HTML 프레젠테이션 빌더

zero-dependency, 애니메이션 풍부한 HTML 프레젠테이션을 만듭니다. npm·빌드 도구 없이 단일 HTML 파일로 브라우저에서 바로 실행됩니다.

> 🇰🇷 **이 스킬은 한국어 응답을 기본으로 합니다.** 사용자와의 모든 커뮤니케이션·코드 주석·내부 메모는 한국어. 폰트는 한글 가독성을 고려해 Pretendard / Gmarket Sans / IBM Plex Sans KR / 나눔스퀘어 네오 등을 우선 검토합니다.

## 워크스페이스 브랜드 연동 (선택)

이 워크스페이스에는 자사 브랜드 컨텍스트가 정의되어 있습니다. 사용자가 **"우리 브랜드 톤으로"** 또는 **"자사 컬러로"** 같이 요청하면:

1. `_context/brand/04_visual-context.md` Read → 컬러 팔레트·폰트·금지 컬러 추출
2. `_context/brand/03_tone-context.md` Read → 카피 톤·금지 표현 추출
3. STYLE_PRESETS.md 12종 외에 **"브랜드 시그니처"** 라는 13번째 프리셋으로 사용
4. Phase 2 미리보기 3개 중 1개는 반드시 브랜드 시그니처 포함

브랜드 컨텍스트 파일이 없거나 사용자가 브랜드와 무관한 자료(외부 강연·고객 미팅 등)를 요청하면 무시하고 일반 프리셋만 사용합니다.

---

## 핵심 원칙

1. **Zero Dependencies** — 단일 HTML 파일 + 인라인 CSS/JS. npm·빌드 도구 없음.
2. **Show, Don't Tell** — 추상적 선택지 대신 시각 미리보기 생성. 사람은 보면서 자기 취향을 발견합니다.
3. **Distinctive Design** — 일반적인 "AI slop" 금지. 모든 프레젠테이션은 맞춤 제작 느낌.
4. **Viewport Fitting (절대 규칙)** — 모든 슬라이드는 정확히 100vh 안에 맞아야 합니다. 슬라이드 내부 스크롤 절대 금지. 콘텐츠 넘치면 슬라이드 분할.

## 디자인 미감

기본값에 안주하면 "AI slop" 미감이 됩니다. 일반적인 출력으로 수렴하지 마세요. 창의적·독특한 프론트엔드를 만드세요.

집중 포인트:

- **타이포그래피**: 아름답고 독특하고 흥미로운 폰트 선택. Arial·Inter 같은 일반 폰트는 피하고 미감을 끌어올리는 폰트 선택. **한글 슬라이드는 Pretendard / Gmarket Sans / IBM Plex Sans KR / 나눔스퀘어 네오** 우선 검토.
- **컬러 & 테마**: 일관된 미감에 commit. CSS 변수로 일관성 확보. 우세 컬러 + 날카로운 액센트 > 균등하게 흩어진 팔레트. IDE 테마·문화권 미감에서 영감.
- **모션**: 효과·마이크로 인터랙션에 애니메이션 사용. HTML은 CSS-only 솔루션 우선. 한 번의 잘 안무된 페이지 로드(staggered animation-delay)가 흩뿌려진 마이크로 인터랙션보다 강합니다.
- **배경**: 단색 기본값 대신 분위기·깊이를 만드세요. CSS 그라데이션 레이어, 기하학 패턴, 컨텍스트 효과.

피해야 할 일반적 AI 미감:

- 과사용 폰트 (Inter, Roboto, Arial, system fonts)
- 진부한 컬러 스킴 (특히 흰 배경 위 보라 그라데이션)
- 예측 가능한 레이아웃·컴포넌트 패턴
- 컨텍스트 없는 쿠키커터 디자인

창의적으로 해석하고 컨텍스트에 맞는 의외의 선택을 하세요. Light/Dark, 다양한 폰트·미감을 오갑니다. Space Grotesk 같은 흔한 선택으로 수렴하지 마세요.

## Viewport Fitting 규칙

**모든** 프레젠테이션의 **모든** 슬라이드에 적용:

- 모든 `.slide`는 `height: 100vh; height: 100dvh; overflow: hidden;` 필수
- **모든** 폰트 사이즈·간격은 `clamp(min, preferred, max)` 사용 — fixed px/rem 금지
- 콘텐츠 컨테이너는 `max-height` 제약 필요
- 이미지: `max-height: min(50vh, 400px)`
- 높이 브레이크포인트 필수: 700px, 600px, 500px
- `prefers-reduced-motion` 지원 포함
- CSS 함수 직접 음수화 금지 (`-clamp()`, `-min()`, `-max()` 는 무시됨) — `calc(-1 * clamp(...))` 사용

**생성 시 `viewport-base.css`를 Read 하고 전체 내용을 모든 프레젠테이션에 포함하세요.**

### 슬라이드별 콘텐츠 밀도 한계

| 슬라이드 유형      | 최대 콘텐츠                                          |
| ------------ | ------------------------------------------------ |
| 타이틀          | 헤딩 1 + 서브타이틀 1 + (선택) 태그라인                       |
| 콘텐츠          | 헤딩 1 + 불릿 4-6개 OR 헤딩 1 + 단락 2개                   |
| Feature 그리드  | 헤딩 1 + 카드 최대 6개 (2x3 또는 3x2)                     |
| 코드           | 헤딩 1 + 코드 8-10줄                                  |
| 인용           | 인용 1개 (최대 3줄) + 출처                               |
| 이미지          | 헤딩 1 + 이미지 1 (최대 60vh 높이)                        |

**한계 초과 시 무조건 슬라이드 분할. 절대 욱여넣지 말고 절대 스크롤 금지.**

---

## Phase 0: Mode 판별

사용자 의도 파악:

- **Mode A: 신규 프레젠테이션** — 처음부터 생성. Phase 1로.
- **Mode B: PPT → HTML 변환** — .pptx 파일을 HTML로 변환. Phase 4로.
- **Mode C: 기존 슬라이드 개선** — 기존 HTML 프레젠테이션 개선. Read → 이해 → 개선. **아래 Mode C 수정 규칙 준수.**
- **Mode D: HTML → PPT 변환** — 기존 HTML을 .pptx로 export. Phase 6C로 직행 (`scripts/export-pptx.py`).

### Mode C: 수정 규칙

기존 프레젠테이션 개선 시 viewport fitting이 가장 큰 리스크:

1. **콘텐츠 추가 전:** 기존 요소 카운트 → 밀도 한계와 대조
2. **이미지 추가:** `max-height: min(50vh, 400px)` 필수. 슬라이드가 이미 가득 차 있으면 슬라이드 분할
3. **텍스트 추가:** 슬라이드당 4-6 불릿 최대. 초과 시 후속 슬라이드로 분할
4. **수정 후 반드시 검증:** `.slide`에 `overflow: hidden`, 신규 요소가 `clamp()` 사용, 이미지에 viewport-relative max-height, 1280x720에서 콘텐츠 fit
5. **선제적 재구성:** 수정으로 오버플로 발생할 것 같으면 자동 분할하고 사용자에게 알림. 요청 기다리지 말 것

**기존 슬라이드에 이미지 추가:** 다른 콘텐츠 줄이거나 이미지를 새 슬라이드로. 기존 콘텐츠가 viewport를 채우는지 확인 없이 이미지 추가 금지.

---

## Phase 1: 콘텐츠 디스커버리 (신규 프레젠테이션)

**모든 질문을 단일 AskUserQuestion 호출로** 묶어서 한 번에 받습니다:

**Q1 — 목적** (header: "목적"):
이 프레젠테이션의 용도는? 옵션: 피치덱 / 강의·튜토리얼 / 컨퍼런스 발표 / 사내 보고

**Q2 — 분량** (header: "분량"):
대략 몇 슬라이드? 옵션: 짧게 5-10 / 중간 10-20 / 길게 20+

**Q3 — 콘텐츠** (header: "콘텐츠"):
콘텐츠가 준비되어 있나요? 옵션: 전체 준비됨 / 거친 메모 / 주제만

**Q4 — 인라인 편집** (header: "편집"):
생성 후 브라우저에서 텍스트 직접 수정 필요? 옵션:

- "예 (권장)" — 브라우저에서 텍스트 편집, localStorage 자동저장, 파일 export
- "아니오" — 발표 전용, 파일 사이즈 작게 유지

**사용자의 편집 선택을 기억** — Phase 3에서 편집 코드 포함 여부 결정.

콘텐츠가 있으면 공유 요청.

### Step 1.2: 이미지 평가 (이미지 제공 시)

사용자가 "이미지 없음" 선택 → Phase 2로.

이미지 폴더 제공 시:

1. **스캔** — 이미지 파일 리스트 (.png, .jpg, .svg, .webp 등)
2. **각 이미지 보기** — Read 도구 사용 (Claude는 멀티모달)
3. **평가** — 각각: 무엇을 담고 있는지, USABLE / NOT USABLE (이유 포함), 어떤 컨셉, 주요 컬러
4. **아웃라인 공동 설계** — 큐레이션된 이미지가 텍스트와 함께 슬라이드 구조에 영향. "슬라이드 짠 다음 이미지 끼워넣기"가 아니라 처음부터 둘 다 같이 (예: 스크린샷 3장 → 3개 feature 슬라이드, 로고 1개 → 타이틀·클로징)
5. **AskUserQuestion 으로 확인** (header: "아웃라인"): "이 슬라이드 아웃라인과 이미지 선택이 맞나요?" 옵션: 좋음 / 이미지 조정 / 아웃라인 조정

**미리보기에 로고 사용:** 사용 가능한 로고가 있으면 base64로 임베드해서 Phase 2 각 스타일 미리보기에 — 사용자는 자기 브랜드가 세 가지 다른 스타일로 어떻게 보이는지 봅니다.

---

## Phase 2: 스타일 디스커버리

**이게 "show, don't tell" 단계입니다.** 대부분의 사람은 디자인 선호를 말로 표현 못 합니다.

### Step 2.0: 스타일 경로

선택 방식 질문 (header: "스타일"):

- "옵션 보여줘" (권장) — 무드 기반 미리보기 3종 생성
- "내가 알아서" — 프리셋 직접 선택

**직접 선택 시:** 프리셋 피커 보여주고 Phase 3로. 사용 가능한 프리셋은 [STYLE_PRESETS.md](STYLE_PRESETS.md)에 정의.

### Step 2.1: 무드 선택 (가이드 디스커버리)

질문 (header: "느낌", multiSelect: true, max 2):
청중에게 어떤 느낌? 옵션:

- 인상적/자신감 — 프로페셔널, 신뢰감
- 흥분/활력 — 혁신적, 대담
- 차분/집중 — 명료, 사려깊음
- 영감/감동 — 감성적, 기억에 남음

### Step 2.2: 미리보기 3종 생성

무드 기반으로 타이포그래피·컬러·애니메이션·전반 미감을 보여주는 3개의 단일 슬라이드 HTML 미리보기 생성. 사용 가능한 프리셋·스펙은 [STYLE_PRESETS.md](STYLE_PRESETS.md) Read.

| 무드          | 추천 프리셋                                      |
| ----------- | ------------------------------------------- |
| 인상적/자신감     | Bold Signal, Electric Studio, Dark Botanical |
| 흥분/활력       | Creative Voltage, Neon Cyber, Split Pastel  |
| 차분/집중       | Notebook Tabs, Paper & Ink, Swiss Modern    |
| 영감/감동       | Dark Botanical, Vintage Editorial, Pastel Geometry |

**워크스페이스 브랜드 컨텍스트가 있고 사용자가 "우리 브랜드"를 언급하면**: 3개 중 1개는 반드시 `_context/brand/04_visual-context.md` 컬러·폰트로 합성된 "브랜드 시그니처" 프리셋.

미리보기를 `.claude-design/slide-previews/`에 저장 (style-a.html, style-b.html, style-c.html). 각각 self-contained, ~50-100줄, 애니메이티드 타이틀 슬라이드 1장.

각 미리보기를 자동 open.

### Step 2.3: 사용자 픽

질문 (header: "스타일"):
어느 미리보기가 더 좋으신가요? 옵션: Style A: [이름] / Style B: [이름] / Style C: [이름] / 요소 믹스

"믹스" 시 구체 사항 추가 질문.

---

## Phase 3: 프레젠테이션 생성

Phase 1의 콘텐츠 (텍스트 또는 텍스트 + 큐레이션 이미지) + Phase 2의 스타일로 전체 프레젠테이션 생성.

이미지가 제공됐으면 슬라이드 아웃라인은 이미 Step 1.2에서 반영됨. 없으면 CSS 생성 비주얼 (그라데이션·셰이프·패턴)이 시각적 흥미 제공 — 완전히 지원되는 first-class 경로.

**생성 전 반드시 Read:**

- [html-template.md](html-template.md) — HTML 아키텍처·JS 기능
- [viewport-base.css](viewport-base.css) — 필수 CSS (전체 포함)
- [animation-patterns.md](animation-patterns.md) — 선택된 느낌에 맞는 애니메이션 레퍼런스

**핵심 요건:**

- 단일 self-contained HTML 파일, 모든 CSS/JS 인라인
- viewport-base.css **전체 내용**을 `<style>` 블록에 포함
- 폰트는 Fontshare / Google Fonts에서 — system fonts 금지
- 한글 슬라이드면 Pretendard / Gmarket Sans / IBM Plex Sans KR / 나눔스퀘어 네오 우선
- 각 섹션 설명 주석 추가
- 모든 섹션 시작에 `/* === SECTION NAME === */` 주석 블록

**저장 위치 (워크스페이스 룰):** 결과물은 `presentations/` 폴더에. 파일명은 `{topic}_{type}_{YYYY-MM-DD}.html`.

---

## Phase 4: PPT 변환

PowerPoint 파일 변환:

1. **콘텐츠 추출** — `python scripts/extract-pptx.py <input.pptx> <output_dir>` 실행 (필요 시 `pip install python-pptx`)
2. **사용자 확인** — 추출된 슬라이드 타이틀·콘텐츠 요약·이미지 카운트 제시
3. **스타일 선택** — Phase 2로
4. **HTML 생성** — 선택된 스타일로 변환, 모든 텍스트·이미지(assets/에서)·슬라이드 순서·발표자 노트(HTML 주석으로) 보존

---

## Phase 5: 전달

1. **정리** — `.claude-design/slide-previews/` 있으면 삭제
2. **열기** — `open [filename].html` 로 브라우저 실행
3. **요약 알림** — 사용자에게:
   - 파일 위치, 스타일명, 슬라이드 수
   - 네비게이션: 화살표 키, 스페이스, 스크롤/스와이프, 네비 닷 클릭
   - 커스터마이즈: `:root` CSS 변수로 컬러, 폰트 링크로 타이포그래피, `.reveal` 클래스로 애니메이션
   - 인라인 편집 활성화 시: 좌상단 hover 또는 E 키로 편집 모드, 텍스트 클릭해 편집, Ctrl+S 저장

---

## Phase 6: 공유 & 내보내기 (선택)

전달 후 **사용자에게 질문:** _"이 프레젠테이션 공유하실래요? 라이브 URL로 배포하거나 (모바일 포함 모든 디바이스 작동) PDF로 내보낼 수 있어요."_

옵션:

- **URL 배포** — 모든 디바이스에서 작동하는 공유 링크
- **PDF 내보내기** — 이메일·슬랙·인쇄용 범용 파일
- **둘 다**
- **괜찮음**

거절하면 종료. 선택하면 아래 진행.

### 6A: 라이브 URL 배포 (Vercel)

Vercel — 무료 호스팅 — 에 배포. 링크는 모든 디바이스에서 작동, 사용자가 내릴 때까지 라이브.

**처음 배포하는 사용자라면 단계별 가이드:**

1. **Vercel CLI 설치 확인** — `npx vercel --version`. 없으면 Node.js 먼저 (`brew install node` on macOS, 또는 https://nodejs.org).

2. **로그인 확인** — `npx vercel whoami`.
   - 미로그인이면 설명: _"Vercel은 무료 호스팅이에요. 배포하려면 계정이 필요해요. 단계별로 안내드릴게요:"_
     - 1: 브라우저로 https://vercel.com/signup
     - 2: GitHub·Google·이메일 — 편한 거로 가입
     - 3: 가입 후 `vercel login` 실행, 프롬프트 따라가기 (브라우저에서 인증 창 열림)
     - 4: `vercel whoami` 로 로그인 확인
   - 로그인 확인까지 사용자 응답 기다림.

3. **배포** — 스크립트 실행:

   ```bash
   bash scripts/deploy.sh <path-to-presentation>
   ```

   폴더 (index.html 포함) 또는 단일 HTML 파일 모두 가능.

4. **URL 공유** — 사용자에게:
   - 라이브 URL (스크립트 출력)
   - 모든 디바이스에서 작동 — 문자·슬랙·이메일 OK
   - 내릴 때: https://vercel.com/dashboard 방문 후 프로젝트 삭제
   - Vercel 무료 티어는 넉넉함 — 과금 없음

**⚠ 배포 주의사항:**

- **로컬 이미지·비디오는 HTML과 함께 가야 합니다.** 배포 스크립트가 HTML의 `src="..."` 참조 파일을 자동 감지·번들. 단, CSS `background-image` 또는 변칙 경로면 누락될 수 있음. **배포 전 확인:** 배포된 URL 열어서 모든 이미지 로드 체크. 깨지면 가장 안전한 방법은 HTML과 모든 자산을 단일 폴더에 넣고 폴더 통째로 배포.
- **자산 많을 때는 폴더 배포 권장.** 프레젠테이션이 폴더 안에 이미지와 함께 있으면 (예: `my-deck/index.html` + `my-deck/logo.png`), 폴더 직접 배포: `bash scripts/deploy.sh ./my-deck/`. 단일 HTML보다 안정적 — 폴더 전체가 그대로 업로드.
- **공백 포함 파일명 작동하지만 이슈 가능.** 스크립트는 처리하지만 Vercel URL은 공백을 `%20`로 인코딩. 가능하면 이미지 파일명 공백 회피. 사용자 이미지에 공백 있으면 스크립트가 처리하지만 이미지 깨지면 하이픈으로 변경이 fix.
- **재배포 시 동일 URL.** 같은 프레젠테이션에 스크립트 다시 실행하면 이전 배포 덮어씀. URL 그대로 — 새 링크 공유 불필요.

### 6B: PDF 내보내기

각 슬라이드를 스크린샷으로 캡처해 PDF로 합칩니다. 이메일 첨부·문서 임베드·인쇄에 적합.

**참고:** 애니메이션·인터랙션 보존 안 됨 — PDF는 정적 스냅샷. 정상이고 의도된 동작; 사용자에게 미리 알려주세요.

1. **스크립트 실행:**

   ```bash
   bash scripts/export-pdf.sh <path-to-html> [output.pdf]
   ```

   output 미지정 시 HTML 파일 옆에 저장.

2. **내부 동작** (사용자에게 간략 설명):
   - 헤드리스 브라우저가 1920×1080 (표준 와이드스크린)에서 프레젠테이션 오픈
   - 각 슬라이드 한 장씩 스크린샷
   - 모든 스크린샷을 단일 PDF로 합침
   - 스크립트는 Playwright (브라우저 자동화 도구) 필요 — 없으면 자동 설치

3. **Playwright 설치 실패 시:**
   - 가장 흔한 이슈는 Chromium 다운로드 실패: `npx playwright install chromium`
   - 그것도 실패하면 네트워크/방화벽 이슈 — 다른 네트워크에서 시도 요청

4. **PDF 전달** — 스크립트 자동 open. 사용자에게:
   - 파일 위치·사이즈
   - 어디서나 작동 — 이메일·슬랙·노션·구글 닥스·인쇄
   - 애니메이션은 최종 비주얼 상태로 대체 (여전히 멋지고, 정적일 뿐)

**⚠ PDF 내보내기 주의사항:**

- **첫 실행은 느림.** 스크립트가 Playwright 설치 + Chromium (~150MB) 다운로드. 실행당 1회. 첫 실행 30-60초 안내; 같은 세션 내 후속 실행은 빠름.
- **슬라이드는 `class="slide"` 필수.** 스크립트는 `.slide` 쿼리로 슬라이드 탐색. 다른 클래스명이면 "0 slides found"로 실패. 이 스킬 생성 결과물은 모두 `.slide` 사용 — 외부 HTML에만 해당.
- **로컬 이미지는 HTTP 로드 가능해야.** 스크립트는 로컬 서버 띄우고 HTML을 통해 로드 (구글 폰트·상대 경로 작동). 절대 파일시스템 경로 (예: `src="/Users/name/photo.png"`) 대신 상대 경로 (예: `src="photo.png"`) 필수. 생성 결과물은 항상 상대 경로 사용; 변환·사용자 제공 덱은 체크 후 fix.
- **로컬 이미지 PDF에 포함됨** — HTML과 같은 디렉토리 (또는 상대 경로) 내. 스크립트는 HTML 부모 디렉토리를 HTTP로 서비스 → `src="photo.png"` 같은 상대 경로 정상 동작 (공백 포함 파일명도 OK). 안 보이면 체크: (1) 이미지 파일이 참조 경로에 실재, (2) 절대 경로 (`/Users/name/photo.png`) 아닌 상대 경로.
- **큰 프레젠테이션은 큰 PDF.** 각 슬라이드는 풀 1920×1080 PNG 스크린샷. 18장 덱이 ~20MB PDF. 10MB 초과 시 사용자에게 _"PDF가 [size]에요. 압축할까요? 약간 덜 선명하지만 파일이 훨씬 작아져요."_ 응답 yes면 `--compact` 플래그로 재실행:
  ```bash
  bash scripts/export-pdf.sh <path-to-html> [output.pdf] --compact
  ```
  1920×1080 대신 1280×720 렌더 — 보통 50-70% 사이즈 절감, 시각적 차이 미미.

### 6C: PowerPoint(.pptx) 내보내기

각 슬라이드를 1920×1080 스크린샷으로 캡처해 16:9 .pptx에 풀블리드 이미지로 임베드합니다. 클라이언트가 .pptx를 요구하거나 PowerPoint·Keynote에서 발표해야 할 때 사용.

**참고:**
- 애니메이션·인터랙션·텍스트 편집 보존 안 됨 — 각 슬라이드는 단일 이미지. 시각 충실도 우선.
- 텍스트를 PowerPoint에서 편집해야 한다면 이 export 대신 `mckinsey-deck` 스킬 사용 검토.

1. **스크립트 실행:**

   ```bash
   python3 scripts/export-pptx.py <path-to-html> [output.pptx]
   ```

   output 미지정 시 HTML 파일과 같은 위치에 같은 이름 + `.pptx`로 저장.

2. **내부 동작:**
   - 로컬 HTTP 서버로 HTML 서빙 (폰트·이미지 정상 로딩)
   - Playwright Chromium이 1920×1080 (device_scale_factor=2)로 각 `.slide` 캡처
   - python-pptx로 16:9 (13.333"×7.5") 빈 레이아웃 슬라이드에 PNG 풀블리드 임베드
   - 임시 파일 자동 정리

3. **사이즈가 클 때:** `--compact` 플래그로 1280×720 캡처 (50-70% 사이즈 절감)
   ```bash
   python3 scripts/export-pptx.py <path-to-html> [output.pptx] --compact
   ```

**⚠ PPT 내보내기 주의사항:**

- **PDF export와 같은 슬라이드 탐색 규칙.** `.slide` 클래스 필수 — `extract-pptx`/`export-pdf`와 동일.
- **첫 실행은 Playwright + Chromium 다운로드.** PDF export와 캐시 공유 — 한 번 설치하면 둘 다 빠름.
- **텍스트가 이미지로 박힘.** PowerPoint에서 텍스트 클릭·편집 불가. 발표 후 텍스트 수정 가능성 있으면 사용자에게 사전 안내.
- **파일 사이즈 큼.** 11장 ~14MB, 18장 ~22MB 정도. 이메일 25MB 첨부 한도 넘기면 `--compact` 권장.

---

## 지원 파일

| 파일                                                  | 용도                                         | 읽는 시점                  |
| --------------------------------------------------- | ------------------------------------------ | ---------------------- |
| [STYLE_PRESETS.md](STYLE_PRESETS.md)                | 12종 큐레이션 비주얼 프리셋 (컬러·폰트·시그니처 요소)            | Phase 2 (스타일 선택)        |
| [viewport-base.css](viewport-base.css)              | 필수 반응형 CSS — 모든 프레젠테이션에 그대로 복사             | Phase 3 (생성)            |
| [html-template.md](html-template.md)                | HTML 구조·JS 기능·코드 품질 표준                     | Phase 3 (생성)            |
| [animation-patterns.md](animation-patterns.md)      | CSS/JS 애니메이션 스니펫 + 효과↔느낌 가이드               | Phase 3 (생성)            |
| [scripts/extract-pptx.py](scripts/extract-pptx.py)  | PPT 콘텐츠 추출 Python 스크립트                     | Phase 4 (변환)            |
| [scripts/deploy.sh](scripts/deploy.sh)              | Vercel 배포로 즉시 공유                           | Phase 6 (공유)            |
| [scripts/export-pdf.sh](scripts/export-pdf.sh)      | PDF 내보내기                                   | Phase 6 (공유)            |
| [scripts/export-pptx.py](scripts/export-pptx.py)    | PowerPoint(.pptx) 내보내기 (이미지 기반)             | Phase 6 (공유)            |

---

## 워크스페이스 통합 메모

- 산출물 저장: `presentations/` 폴더 (워크스페이스 CLAUDE.md 룰)
- 파일명: `{topic}_{type}_{YYYY-MM-DD}.html`
- 한국어 응답 기본, 슬라이드 텍스트도 한국어 기본 (영문 요청 시 명시 필요)
- `_context/brand/04_visual-context.md` 의 **Never Use** 컬러·폰트는 자동 회피
- `_context/brand/03_tone-context.md` 의 **Never** 카피 표현은 슬라이드 헤딩·CTA에 적용 금지
- `mckinsey-deck` 스킬과의 차이: 이 스킬은 **HTML 기반 인터랙티브** (애니메이션·라이브 URL·PDF·PPT export 가능, PPT는 이미지 기반·편집 불가). `mckinsey-deck`은 처음부터 .pptx로 빌드하는 정적·편집 가능 컨설팅 톤 덱. PowerPoint에서 텍스트 편집이 필요하면 `mckinsey-deck`, 비주얼 자유도가 필요하면 이 스킬.

---

*Adapted from [zarazhangrui/frontend-slides](https://github.com/zarazhangrui/frontend-slides) (MIT License). 한국어 워크스페이스용 어댑테이션.*

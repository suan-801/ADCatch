# 4강 단원 1 — 데이터 트래킹 시스템 셋업 가이드

이 문서는 4강 퍼포먼스팀의 모든 단원에서 공통으로 사용할 **GA4 / Microsoft Clarity / Meta Marketing API** 3개 데이터 소스를 Claude Code와 연결하는 통합 셋업 가이드다.

> **목표**: 30분 안에 3개 소스를 모두 연결하고, 클로드 코드에서 자연어로 데이터를 질의할 수 있는 상태 만들기.

---

> ## 📌 Claudecode_MarketingOS_student 환경 적용 노트
>
> 본 OS(`Claudecode_MarketingOS_student`) 의 트래킹 셋업 경로·도구는 아래와 같다.
>
> | 항목 | 본 OS 경로/도구 |
> |---|---|
> | 작업 디렉토리 | `Claudecode_MarketingOS_student/` |
> | `.mcp.json` 위치 | `Claudecode_MarketingOS_student/.mcp.json` (프로젝트 루트) |
> | Meta `.env` 위치 | `Claudecode_MarketingOS_student/09_tracking/.env` |
> | Clarity MCP 서버 | **공식 npm `@microsoft/clarity-mcp-server`** (별도 빌드 ❌, § 3.4 참조). 아래 박스 그대로 사용 |
>
> **Clarity 공식 패키지 `.mcp.json` 항목** (자체빌드 대신 이걸 사용):
>
> ```json
> "clarity": {
>   "command": "npx",
>   "args": ["-y", "@microsoft/clarity-mcp-server"],
>   "env": {
>     "CLARITY_API_TOKEN": "YOUR_CLARITY_TOKEN",
>     "CLARITY_PROJECT_ID": "YOUR_CLARITY_PROJECT_ID"
>   }
> }
> ```
>
> **Meta 검증**: 본 OS 는 **MCP 트랙 (★ 1순위, Claude Code OAuth 1클릭, 토큰 Keychain 자동) + User Access Token 트랙 (2순위, Python SDK 호출용, 60일 long-lived, `ads_read` only) 병행** 을 디폴트로 사용한다. 상세 트랙·발급 절차는 [09_tracking/MetaAds_연결_가이드.md](09_tracking/MetaAds_연결_가이드.md) 가 진실의 단일 출처. § 4 본문은 SDK + System User 흐름을 기술하지만, 본 OS 적용 시엔 가이드의 **4트랙 우선순위** 를 따른다: ★ **MCP** (가이드 § 11 부록 C — `https://mcp.facebook.com/ads`, `.mcp.json` 등록 + OAuth 1클릭, Higgsfield 같은 UX) → ① **User Token** (가이드 § 1~8, 5분 발급, `ads_read` 만, Python SDK 호출용) → ② **Meta 공식 CLI** (가이드 § 9 부록 A — [공식 시작하기 문서](https://developers.facebook.com/documentation/ads-commerce/ads-ai-connectors/ads-cli/setup/get-started), 패키지 [`meta-ads`](https://pypi.org/project/meta-ads/), 권한 7개 trade-off, 보안 가드 5개 의무) → ③ **System User Token** (가이드 § 10 부록 B, 참고용, cron 무인 운영시만. BM Admin + 2024 정책상 다른 Admin 2차 승인 가능성). 검증은 MCP 트랙 = 자연어 쿼리 ("메타 어제 ROAS" → `mcp__meta-ads__*` 도구 자동 호출), User Token 트랙 = Python SDK 1줄 스크립트 (`facebook-business` + `09_tracking/.env` 로드). Claude Code 의 자연어 쿼리는 MCP 가 가용 시 MCP 도구 우선, 없으면 Claude 가 SDK 헬퍼 (`_shared/scripts/lib/meta_client.py`) 를 import 한 Python 스크립트를 Bash 로 실행.

---

## 목차

1. [개요와 사전 준비](#1-개요와-사전-준비) — [1.5 키 보관 위치 정리 (.env vs .mcp.json)](#15-키-보관-위치-정리--env-vs-mcpjson)
2. [GA4 연결](#2-ga4-연결) — 옵션 A(서비스 계정, 보안 우선) 디폴트 / [2.8 옵션 B OAuth ADC 부록](#28-부록-a--옵션-b-oauth--gcloud-adc-트랙-편의용) / [2.9 GA4 역할·분석 항목](#29-ga4의-역할과-자주-분석하는-항목) / [2.10 비용·할당량](#210-비용-및-할당량)
3. [Microsoft Clarity 연결](#3-microsoft-clarity-연결) — [3.6 Clarity 역할·분석 항목](#36-clarity의-역할과-자주-분석하는-항목)
4. [Meta Marketing API 연결](#4-meta-marketing-api-연결) — SDK + System User Token (보안 우선) / [4.6 미지원 기능](#46-미지원-기능) / [4.7 API 제약사항](#47-api-제약사항) / [4.8 CLI 트랙 부록 (편의용)](#48-부록-a--cli-트랙-편의실험용-보안-가드-필수)
5. [통합 검증](#5-통합-검증)
6. [트러블슈팅](#6-트러블슈팅)
7. [부록: 보조 문서](#7-부록-보조-문서)
8. (이전 부록 A — 서비스 계정 방식 — 은 § 2 메인 본문으로 승격됨, 라벨만 옵션 A 로 변경)
9. [부록 C — MCP 서버 선택 체크리스트](#부록-c-mcp-서버-선택-체크리스트)

---

## 1. 개요와 사전 준비

### 왜 3개 소스인가

| 소스 | 측정 영역 | 강의에서의 역할 |
|------|-----------|-----------------|
| **GA4** | 유입 (채널/세션/전환/매출) | 단원 3 일일 슬랙, 단원 4 대시보드, 단원 5 캠페인 리포트 |
| **Clarity** | 행동 (rage click, dead click, 세션 녹화) | 광고비를 쓴 트래픽이 LP에서 어떻게 막히는지 진단 |
| **Meta API** | 광고 (캠페인/광고세트/광고 단위 실적) | 일일 모니터링과 캠페인 사후 분석의 1차 데이터 |

세 소스는 **퍼널의 각기 다른 구간**을 책임진다. 어느 하나만으로는 "왜 전환이 떨어졌나"를 설명할 수 없기 때문에 통합이 필요하다.

### 필수 요구사항

이 가이드는 **Windows / macOS 모두**에서 따라할 수 있다. 다만 명령어가 OS별로 일부 다르므로 각 단계의 OS 표시를 확인할 것.

| 항목 | 최소 버전 / 조건 |
|------|------|
| OS | Windows 10/11 또는 macOS 12+ |
| Node.js | v18 이상 |
| Python | 3.10 이상 |
| Git | 최신 |
| Claude Code CLI | 설치 + 로그인 완료 |
| 서비스 계정 | Google(GA4) / Microsoft(Clarity) / Facebook(Meta) |

### 1.1 터미널 열기

| OS | 방법 |
|----|------|
| **Windows** | `Win` 키 → "PowerShell" 검색 → Enter (또는 Windows Terminal) |
| **macOS** | `Cmd + Space` → "터미널" 검색 → Enter |

이후 가이드의 모든 명령어는 이 터미널 창에 입력한다.

### 1.2 환경 점검

각 줄을 입력해 버전이 출력되면 통과, `command not found` 면 미설치.

| 항목 | Windows 명령 | macOS 명령 | 통과 기준 |
|------|------|------|------|
| Node.js | `node --version` | `node --version` | v18.x 이상 |
| npm | `npm --version` | `npm --version` | v9 이상 |
| Python | `python --version` | `python3 --version` | 3.10 이상 |
| pip | `pip --version` | `pip3 --version` | 출력 OK |
| Git | `git --version` | `git --version` | 출력 OK |
| Claude Code | `claude --version` | `claude --version` | 설치 확인 |

> **Python 명령어 주의**: macOS는 `python3`/`pip3`, Windows는 `python`/`pip` (또는 `py`)가 일반적. 이후 가이드는 OS별로 명시된 명령을 사용한다. 가이드의 명령을 그대로 복붙하면 Windows에서 `python3: 인식되지 않습니다` 에러가 나니 OS 표시를 꼭 확인.

### 1.3 누락 항목 설치

위 6개 중 통과 못한 것만 설치. 전부 통과면 1.4로.

#### Windows

| 항목 | 설치 방법 | 주의 |
|------|------|------|
| Node.js | [nodejs.org](https://nodejs.org/ko) LTS (.msi) 다운로드 → 실행 | "Add to PATH" 체크 (기본 ON) |
| Python | [python.org/downloads/windows](https://www.python.org/downloads/windows/) (.exe) | **반드시 "Add Python to PATH" 체크** — 안 하면 거의 모든 후속 단계가 막힘 |
| Git | [git-scm.com/download/win](https://git-scm.com/download/win) | 기본값으로 진행 OK |
| Claude Code | `npm install -g @anthropic-ai/claude-code` | npm 먼저 설치 |

설치 후엔 **PowerShell 완전히 닫고 새로 열기** (PATH 갱신용). 회사 노트북이면 EDR/VPN이 npm 다운로드를 막을 수 있으니 IT 협의 또는 개인 장비 권장.

#### macOS

| 항목 | 설치 방법 (Homebrew) | Homebrew 없으면 |
|------|------|------|
| Homebrew (선행) | — | [brew.sh](https://brew.sh/index_ko) 의 한 줄 명령 복붙 |
| Node.js | `brew install node` | [nodejs.org](https://nodejs.org/ko) LTS |
| Python | `brew install python` | [python.org](https://www.python.org/downloads/) |
| Git | `brew install git` | Xcode CLT 설치 시 자동 동봉 |
| Claude Code | `npm install -g @anthropic-ai/claude-code` | npm 먼저 설치 |

### 1.4 작업 디렉토리 + 공통 의존성

강의 자료를 clone한 위치로 이동:

**Windows (PowerShell)**:
```powershell
cd C:\Users\<사용자명>\Desktop\ClaudeCode_MarketingOS\Claudecode_MarketingOS_student
```

**macOS (Terminal)**:
```bash
cd /Users/<사용자명>/Desktop/ClaudeCode_MarketingOS/Claudecode_MarketingOS_student
```

> **Clarity MCP**: 본 OS 는 공식 npm 패키지 (`@microsoft/clarity-mcp-server`) 를 `npx` 로 실행하므로 별도 빌드 단계 없음. § 3.4 참조.

Python 의존성 설치:

| OS | 명령 |
|---|---|
| Windows | `pip install facebook-business python-dotenv pyyaml requests` |
| macOS | `pip3 install facebook-business python-dotenv pyyaml requests` |

> GA4는 공식 패키지(`analytics-mcp`)를 pipx로 실행 — 섹션 2에서 안내. 폴더 안의 커스텀 `ga4-mcp-server/` 는 사용하지 않음 (참고용으로만 보존).

> **한글/공백 폴더명 주의**: `Desktop/마케팅 강의/` 처럼 한글이나 공백이 섞이면 npm/pip가 깨지는 경우가 있다. 영문 경로(`Desktop/clcomktg/`) 권장.

### 1.5 키 보관 위치 정리 — `.env` vs `.mcp.json`

이 OS 는 외부 API 키를 두 파일 중 하나(또는 둘 다)에 보관한다. 어디에 넣어야 할지 헷갈리지 않게 기준을 먼저 정리한다.

#### 핵심 규칙 — "누가 그 키를 쓰는가?"

| 키의 소비자 | 어디에 넣어야 하나 | 이유 |
|---|---|---|
| **Python 스크립트** (직접 REST API 호출) | `09_tracking/.env` | 스크립트가 자체적으로 `.env` 파싱 → `os.environ` 에 주입 |
| **MCP 서버** (Claude Code 가 백그라운드로 spawn) | `.mcp.json` 의 `env` 필드 | MCP 프로세스는 별개 — 부모의 `.env` 를 모름 |
| **둘 다 사용** | 양쪽에 동일하게 | 한 키, 두 소비자 |

#### 모든 키의 보관 위치 한눈에

| API 키 | 누가 쓰나 | `.env`? | `.mcp.json`? |
|---|---|:---:|:---:|
| `META_ACCESS_TOKEN` 외 4개 (System User Token, `ads_read` 만) | Python SDK (10·11·12 cron 리포트 + Claude Code 자연어 쿼리 양쪽 공통) | ✅ | — |
| (부록 § 4.8) Meta OAuth 토큰 (`meta auth login` 자동 저장) | Meta Ads CLI (BM 권한 없을 때 일회성 탐색용) | — | — *(CLI 가 OS 키체인/`~/.config/meta-ads/` 자동 관리)* |
| `APIFY_TOKEN` | Python (02 경쟁사 크롤) | ✅ | — |
| `GEMINI_API_KEY` | Python (02 영상 분석) **+** NanoBanana MCP (06/08/09 이미지 생성) | ✅ | ✅ |
| `PERPLEXITY_API_KEY` | Perplexity MCP (자연어 리서치) | ✅* | ✅ |
| `CLARITY_API_TOKEN` + `CLARITY_PROJECT_ID` | Clarity MCP | — | ✅ |
| `GOOGLE_PROJECT_ID` | analytics-mcp (GA4) | — | ✅ |
| `GOOGLE_APPLICATION_CREDENTIALS` (절대경로 → `09_tracking/ga4-credentials.json`) | analytics-mcp (GA4 서비스 계정 트랙, 디폴트) | — | ✅ |
| GA4 서비스 계정 JSON 키 자체 (`09_tracking/ga4-credentials.json`) | analytics-mcp 가 `GOOGLE_APPLICATION_CREDENTIALS` 경로로 로드 | — *(파일 자체)* | — |
| (부록 § 2.8) gcloud ADC 자격증명 (`~/.config/gcloud/application_default_credentials.json`) | analytics-mcp (GA4 OAuth 트랙, BM 권한 없을 때 부록) | — | — *(gcloud 가 자동 발견)* |

*Perplexity 는 사실상 MCP 만 쓰지만, `.env` 를 **단일 보관소(single source of truth)** 로 유지하기 위해 양쪽에 둔다.

#### 왜 중복이 자연스러운가

```
Python 스크립트 (Bash 로 실행)
       ↓ 자체적으로 .env 읽어서 os.environ 에 주입
       ✅ .env 만 필요

MCP 서버 (Claude Code 가 spawn — 별개 프로세스)
       ↓ Claude Code 가 .mcp.json 의 env 필드를 그 서브프로세스에 직접 주입
       ❌ .env 모름 (다른 경로에 있을 수도 있고, 자동 읽지 않음)
       ✅ .mcp.json 만 필요
```

두 종류의 "소비자" 가 서로 다른 메커니즘으로 키를 받기 때문에 같은 키라도 두 곳에 적어야 함.

#### 운영 원칙 — 통합 보관소 정책

**`.env` 가 마스터 (모든 키의 원본 기록)**:

1. 키를 발급/갱신할 때 → **먼저 `.env` 에 기록**
2. MCP 서버도 그 키를 쓰면 → `.mcp.json` 의 `env:` 에도 **같은 값 복사**
3. Claude Code 재시작 → 모든 키 활성화

> 헷갈리면 양쪽에 다 넣어두면 안전. 안 쓰는 쪽이 있어도 무해.

#### 스킬별 가이드

| 스킬 | 필요한 곳 |
|---|---|
| `/02-competitor-from-adlib` (Python 만) | `.env` 만 |
| `/03-pain-from-reviews` (Perplexity MCP) | `.env` + `.mcp.json` |
| `/05-ad-image-nanobanana` / `/07-carousel-nanobanana` / `/08-landing-page` (NanoBanana MCP) | `.env` + `.mcp.json` |
| `/09-tracking-setup` (analytics-mcp + clarity MCP) | `.mcp.json` 만 |
| `/10-daily-slack` · `/11-monitor` · `/12-period-report` (Meta SDK · cron) | `.env` 만 |
| Claude Code 세션에서 "메타 광고 어제 ROAS" 같은 자연어 쿼리 (디폴트 SDK 트랙) | `.env` 만 |
| (부록 § 4.8) CLI 트랙 — BM 권한 없는 일회성 탐색 | 둘 다 불필요 *(CLI 가 OS 키체인 자동 관리)* |

이 가이드 본문은 § 2 GA4 (`.mcp.json`), § 3 Clarity (`.mcp.json`), § 4 Meta (SDK + Developer App + System User Token + `.env` — 보안 우선 디폴트) 순서로 진행된다. 각 섹션에서 키가 어디로 가는지 확인하며 따라가면 된다.

---

## 2. GA4 연결

GA4는 **Google 공식 MCP 서버** [`analytics-mcp`](https://github.com/googleanalytics/google-analytics-mcp) 를 사용한다 (PyPI 패키지 `analytics-mcp`, `googleanalytics` 조직 공식 레포).

> **MCP 서버 선택 원칙**: 패키지 이름이 비슷해도 공식 vs 서드파티는 다르다. PyPI에 `google-analytics-mcp`(개인 개발자 `surendranb`) 라는 비슷한 이름의 서드파티 패키지가 있는데, **공식은 `analytics-mcp`** 다. GitHub org가 서비스 회사(`googleanalytics`)인지 확인하는 게 가장 확실. 자세한 선택 체크리스트는 [부록 C](#부록-c-mcp-서버-선택-체크리스트) 참조.

인증 방식 비교:

| | 옵션 A: 서비스 계정 (★ 디폴트) | 옵션 B: OAuth ADC (부록) |
|---|---|---|
| GA4 admin 권한 필요? | 필요 (속성에 서비스 계정 추가용) | **불필요** |
| 어떤 속성 보임? | 서비스 계정을 추가한 속성만 (자산 격리) | 본인 Google 계정의 **모든 속성** |
| 셋업 | JSON 키 다운로드 + 속성마다 권한 부여 (15~20분) | gcloud CLI 1회 로그인 (5~10분) |
| 만료 | 없음 (키 revoke 전까지) | 수개월 후 refresh token 만료 가능 |
| cron 자동화 | ✅ 적합 | ❌ 만료 시 무인 운영 중단 |
| 적합한 경우 | 본인 소유 GA4 + 무인 자동화 + 클라이언트 분석 (admin 권한 있을 때) | BM 권한 없는 1인 운영자가 다계정 GA 빠르게 접근 |

> **본 OS 디폴트 = 옵션 A (서비스 계정)**. 1인 마케터·에이전시·클라이언트 광고 자산 분석 환경에서 본인 구글 계정 전체를 OAuth 위임하는 건 (a) 직장·개인 계정의 다른 GA4 자동 노출, (b) 사고 시 영향 범위 통제 불가, (c) cron 만료 부담 — Meta SDK 트랙과 동일한 보안 정책. 옵션 B 는 [§ 2.8 부록 A](#28-부록-a--옵션-b-oauth--gcloud-adc-트랙-편의용) 참조.

### 2.1 사전 준비 — pipx 설치

`pipx` 는 Python CLI 를 격리 환경에서 실행하는 도구. 한 번만 설치하면 이후 모든 Google MCP 서버가 재사용.

**Windows (PowerShell)**:
```powershell
python -m pip install --user pipx
python -m pipx ensurepath
```
끝나면 **PowerShell 완전히 닫고 새로 열기** (PATH 인식).

**macOS (Terminal)**:
```bash
brew install pipx
pipx ensurepath
```

**설치 확인**:
```bash
pipx --version
```

> **gcloud CLI 는 디폴트 트랙에서 불필요** — 서비스 계정은 브라우저 OAuth flow 없이 JSON 키 파일만 직접 사용. (gcloud 는 § 2.8 부록 OAuth 트랙에서만 필요)

### 2.2 Google Cloud 프로젝트 생성

본인이 소유한 GCP 프로젝트가 필요 (GA4 데이터 소유권과 무관, API 호출 quota 통로 역할).

1. [console.cloud.google.com](https://console.cloud.google.com/) → GA4 권한이 있는 본인 계정으로 로그인
2. 상단 **프로젝트 드롭다운 → 새 프로젝트** → 이름 입력 (예: `ga4-{브랜드}`) → **만들기**
3. 드롭다운에서 새 프로젝트가 선택돼 있는지 확인 → **프로젝트 ID** 메모 (예: `ga4-{브랜드}-471312`)

### 2.3 필요 API 활성화

해당 프로젝트가 선택된 상태에서:
- [Analytics Admin API 활성화](https://console.cloud.google.com/apis/library/analyticsadmin.googleapis.com) → **사용 설정**
- [Analytics Data API 활성화](https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com) → **사용 설정**

### 2.4 서비스 계정 생성 + JSON 키 발급

§ 2.2 에서 만든 프로젝트가 선택된 상태에서:

1. 좌측 **IAM 및 관리자 → 서비스 계정** → **+ 서비스 계정 만들기**
2. 이름 `ga4-mcp-reader`, 설명 `GA4 read-only for Claude Code` → **만들고 계속**
3. 역할 부여는 **건너뛰기** (GCP 리소스 권한 불필요 — GA4 쪽에서 직접 부여)
4. **완료**

생성된 서비스 계정 행 클릭 → 상단 **키** 탭 → **키 추가 → 새 키 만들기 → JSON** → 다운로드.

다운로드 파일을 워크스페이스로 이동:

```bash
mv ~/Downloads/ga4-*.json ~/Desktop/Claudecode_MarketingOS_student/09_tracking/ga4-credentials.json
```

`.gitignore` 확인 (★ 의무):

```bash
cd ~/Desktop/Claudecode_MarketingOS_student
grep "09_tracking/ga4-credentials.json\|09_tracking/\*.json" .gitignore || echo "09_tracking/ga4-credentials.json" >> .gitignore
```

> 파일 내부 `private_key` 가 들어있으니 **절대 git 커밋 금지**.

### 2.5 GA4 속성에 서비스 계정 권한 부여 (★ 보안 핵심)

이걸 빼먹으면 백날 연결해도 데이터는 안 보임 — 가장 흔한 실수.

서비스 계정 이메일 확보:
```bash
grep client_email ~/Desktop/Claudecode_MarketingOS_student/09_tracking/ga4-credentials.json
```
예: `ga4-mcp-reader@ga4-{브랜드}-471312.iam.gserviceaccount.com`

GA4 콘솔에서 추가:

1. [analytics.google.com](https://analytics.google.com) → 좌측 하단 **관리(⚙️)**
2. **속성 → 속성 액세스 관리** 클릭
3. 우측 상단 **+** → **사용자 추가**
4. 이메일에 위 `client_email` 붙여넣기
5. 역할 → **뷰어(Viewer)** ★ (편집자·관리자 ❌ — 최소권한)
6. 추가

여러 속성을 같이 보려면 각 속성마다 반복. 자산 격리가 약해지는 게 싫으면 속성 단위가 정석.

### 2.6 `.mcp.json` 등록

워크스페이스 루트 `.mcp.json` 의 `analytics-mcp` 항목을 다음과 같이 채움:

```json
"analytics-mcp": {
  "command": "pipx",
  "args": ["run", "analytics-mcp"],
  "env": {
    "GOOGLE_PROJECT_ID": "ga4-{브랜드}-471312",
    "GOOGLE_APPLICATION_CREDENTIALS": "/Users/hyeongtaekim/Desktop/Claudecode_MarketingOS_student/09_tracking/ga4-credentials.json"
  }
}
```

두 값을 본인 환경으로 교체:
- `GOOGLE_PROJECT_ID` — § 2.2 의 GCP 프로젝트 ID
- `GOOGLE_APPLICATION_CREDENTIALS` — § 2.4 의 JSON 파일 **절대경로** (홈 디렉토리 `~` ❌)

> `GOOGLE_APPLICATION_CREDENTIALS` 가 지정되면 gcloud ADC 보다 우선 적용 → 본인이 이전에 OAuth 로그인한 적이 있어도 서비스 계정 모드로 강제 동작.

### 2.7 검증

Claude Code 완전 종료 후 재시작.

```
내 GA4 속성 목록을 가져올 수 있어?
```

응답이 오면 연결 성공. **§ 2.5 에서 권한 부여한 속성만** 응답에 보이는 게 정상 (OAuth 모드와 달리 본인 계정 전체 GA4 가 안 보임 = 자산 격리 정상).

추가로 실시간 쿼리 1건:
```
지난 7일간 채널별 세션과 전환수를 보여줘
```

표 응답이 오면 OK.

### 2.8 부록 A — 옵션 B: OAuth + gcloud ADC 트랙 (편의용)

> **언제 쓰나**
> - 분석할 GA4 속성에 **사용자 추가 권한이 없을 때** (클라이언트 GA4 를 본인 계정으로만 볼 수 있는 경우)
> - 본인 구글 계정이 권한 가진 **모든 GA4 속성**을 한 번에 접근하고 싶을 때 (편의 우선)
> - § 2.1~2.7 서비스 계정 트랙이 디폴트 — OAuth 는 명시적 trade-off 후 사용
>
> **OAuth 트랙 한계 (재확인)**:
> - 본인 구글 계정의 모든 GA4 (직장·개인) 자동 노출 — 자산 격리 불가
> - 토큰이 `~/.config/gcloud/` 에 묻혀 있어 revoke 번거로움
> - Refresh token 만료 가능 → cron 부적합
> - 10·11·12 cron 스킬은 반드시 서비스 계정 트랙 사용

**B.1 gcloud CLI 설치** (서비스 계정 트랙과 달리 필수):

```bash
brew install --cask google-cloud-sdk   # macOS
gcloud --version
```

**B.2 OAuth 동의 화면 + Desktop Client 발급**:

§ 2.2 의 GCP 프로젝트에서 좌측 **API 및 서비스 → OAuth 동의 화면** → User Type 외부 → 앱 이름 `Claude Code GA4` → 테스트 사용자에 본인 이메일 추가 → 저장. 좌측 **사용자 인증 정보 → + 사용자 인증 정보 만들기 → OAuth 클라이언트 ID → 데스크톱 앱** → JSON 다운로드 → `09_tracking/oauth-client.json` 으로 이동.

**B.3 ADC 로그인**:

```bash
gcloud auth application-default login \
  --client-id-file=/Users/hyeongtaekim/Desktop/Claudecode_MarketingOS_student/09_tracking/oauth-client.json \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform

gcloud auth application-default set-quota-project ga4-{브랜드}
```

본 워크스페이스의 `09_tracking/adc-login.sh` 가 위 명령을 스크립트화한 헬퍼.

**B.4 `.mcp.json` 등록 (OAuth 모드)**:

서비스 계정과 달리 `GOOGLE_APPLICATION_CREDENTIALS` 를 **빼고** `GOOGLE_PROJECT_ID` 만 지정:

```json
"analytics-mcp": {
  "command": "pipx",
  "args": ["run", "analytics-mcp"],
  "env": {
    "GOOGLE_PROJECT_ID": "ga4-{브랜드}-471312"
  }
}
```

> `GOOGLE_APPLICATION_CREDENTIALS` 가 있으면 서비스 계정 모드 우선 → OAuth 모드는 반드시 env 에서 이 변수 제거.

**B.5 토큰 만료 시 (수개월 후)**: `09_tracking/adc-login.sh` 재실행.

상세는 [09_tracking/GA4_연결_가이드.md § 9 부록 A](./09_tracking/GA4_연결_가이드.md) 참고.

### 2.9 GA4의 역할과 자주 분석하는 항목

> **본 워크스페이스의 데이터 분담 원칙**
> - **GA4** → utm별 유입 경로 + 트래픽 볼륨 + 신규/재방문 비율 (+ 보조로 행동·퍼널)
> - **Meta** → ROAS·매출 (Meta 픽셀 매출 × Meta spend, Ads Manager 안에서 완결)
> - **Clarity** → 행동 디테일 (rage click, dead click, 세션 녹화)
>
> GA4 매출과 Meta spend를 결합한 ROAS 계산은 **하지 않는다**. 어트리뷰션 윈도우·중복 카운트 차이로 수치 신뢰가 떨어지기 때문.

#### 1) 유입 경로 (utm별) — 어디서 들어오나 [핵심]

- 채널 그룹별 세션·사용자 (Organic / Paid Search / Paid Social / Direct / Referral / Email)
- 소스·매체별 (`google / cpc`, `naver / organic`, `instagram / paid_social`)
- utm_campaign × utm_content 별 유입량
- 랜딩 페이지별 유입·이탈률
- 디바이스(모바일/데스크톱/태블릿) 분포

> 예시 질의: "지난 7일 utm_source/medium별 세션 표로", "utm_campaign별 세션·신규 사용자 TOP 20"

#### 2) 트래픽 볼륨 — 총 몇 명이 들어오나 [핵심]

- 일간/주간 총 세션·총 사용자(`totalUsers`)·페이지뷰
- 시간대·요일별 트래픽 분포
- 광고 런칭·이벤트일 트래픽 변화 추적
- 채널별 볼륨 추이(증감)

> 예시 질의: "최근 30일 일별 세션·총 사용자 추이", "어제 시간대별 세션 분포"

#### 3) 신규 vs 재방문 — 누가 들어오나 [핵심]

- `newUsers` vs `returningUsers` 비율
- 채널·utm별 신규/재방문 비중 (광고 채널은 신규 위주, organic은 재방문 비중 ↑가 일반적)
- 신규 사용자 코호트 주차별 재방문율 (광고 비용 효율의 장기 지표)
- 디바이스별 신규/재방문 차이

> 예시 질의: "지난 7일 채널별 신규/재방문 비율", "지난 4주 신규 사용자 코호트 W4 재방문율"

#### 4) (보조) 행동·퍼널·이벤트

- 페이지별 참여 시간·이탈률 (콘텐츠 점검)
- 퍼널 단계 이탈 (`view_item` → `add_to_cart` → `begin_checkout` → `purchase`)
- 내부 검색어(`view_search_results`)
- 이벤트 발생 빈도

> 예시 질의: "지난 30일 평균 참여 시간 긴 페이지 TOP 20", "어제 카트→결제 이탈률"

#### 5) (보조) 실시간

- 현재 활성 사용자 (캠페인 런칭 직후 트래픽 진입 확인)
- 장애 발생 시 트래픽 급감 감지

> 예시 질의: "지금 활성 사용자 소스별로"

#### 분석 영역별 도구 매핑

| 무엇을 알고 싶나 | 도구 | 이유 |
|---|---|---|
| 어디서 들어왔나 (utm/채널) | **GA4** | utm 파라미터 표준 추적 |
| 몇 명이 들어왔나 | **GA4** | 사이트 단위 통합 측정 |
| 신규 vs 재방문 | **GA4** | 사용자 식별·쿠키 기반 |
| ROAS·캠페인 매출 | **Meta** | 픽셀 매출 × spend, 어트리뷰션 일관성 |
| LP에서 어떻게 막히나 | **Clarity** | 세션 녹화·rage click |
| 퍼널 어디서 떨어지나 | **GA4** (보조) / **Clarity** (보완) | GA4는 단계 수, Clarity는 원인 |

#### 다음 단원에서 확장

| 분석 영역 | 단원 |
|---|---|
| 유입·신규/재방문 KPI 정의 | 4-2 KPI/임계값 |
| 일간 채널·utm 모니터링 + Meta ROAS | 4-3 일일 리포트 |
| 통합 대시보드 (GA4 유입 + Meta ROAS + Clarity 행동) | 4-4 마케팅 대시보드 |
| 캠페인 사후 분석 (Meta ROAS + GA4 신규/재방문 효율) | 4-5 캠페인 리포트 |

### 2.10 비용 및 할당량

**GA4 Data API는 무료**다. 다만 **토큰 기반 할당량(quota)** 으로 사용량이 제한된다. 표준 GA4 속성 기준 주요 한도(Core 카테고리):

| 항목 | 한도 |
|------|------|
| 속성당 / 일 | 200,000 토큰 |
| 속성당 / 시간 | 40,000 토큰 |
| 프로젝트당-속성당 / 시간 | 14,000 토큰 |
| 동시 요청 | 10개 |
| 시간당 서버 오류 | 50회 |

> GA4 360 유료 속성은 약 5배 한도. BigQuery export를 쓰면 GCP 쿼리 비용이 별도 발생하지만 본 가이드 범위 외.

**쿼리당 토큰 소모 감 잡기**

| 쿼리 유형 | 예시 | 대략 토큰 |
|---|---|---|
| 가벼움 | 1 메트릭, 디멘션 0, 1일 | 10 이하 |
| 중간 | 2~3 디멘션, 5 메트릭, 30일 | 수백 |
| 무거움 | 고카디널리티 디멘션, 필터, 90일+ | 수천~1만+ |

**실제 작업량 예시 (일일 200,000토큰 기준)**

- 가벼운 일일 KPI 조회: 하루 **수천 번** 가능
- 중간 복잡도 리포트: 하루 **수백 번**
- 복잡한 분석 쿼리: 하루 **수십 번**

평소 마케팅 분석·일일 리포트 용도로는 한도에 거의 닿지 않는다. 다만 루프로 대량 백필하거나 고카디널리티 디멘션(예: `pagePath × eventName × deviceCategory`)을 긴 기간 돌리면 빠르게 소진된다.

**남은 할당량 확인**

`run_report` 호출 시 `return_property_quota=true` 를 넣으면 응답에 남은 할당량이 함께 반환된다. 강의 시연·대량 작업 전 확인 권장.

> 정확한 최신 수치는 [GA4 Data API quotas 공식 문서](https://developers.google.com/analytics/devguides/reporting/data/v1/quotas) 확인. Google이 한도를 변경할 수 있다.

---

## 3. Microsoft Clarity 연결

Clarity는 **API 토큰 1개**로 연결되어 가장 단순하다.

### 3.1 Clarity 프로젝트 준비

1. [clarity.microsoft.com](https://clarity.microsoft.com/) 접속
2. 프로젝트가 이미 있고 데이터가 수집되고 있는지 확인 (없으면 신규 생성 후 사이트에 트래킹 코드 설치)

### 3.2 API 토큰 발급

1. Clarity 프로젝트 대시보드 접속
2. **Settings → Data Export** 탭
3. **Generate new API token** 클릭
4. 토큰 이름 입력 (예: `claude-mcp-token`)
5. 생성된 JWT 토큰 복사 → 안전하게 저장

> **주의**: 토큰은 한 번만 표시된다. 분실 시 재발급.

### 3.3 Project ID 확인

대시보드 URL에서 추출:
```
https://clarity.microsoft.com/projects/view/{YOUR_CLARITY_PROJECT_ID}/dashboard
                                        ^^^^^^^^^^
                                        Project ID
```

### 3.4 MCP 서버 등록

프로젝트 루트 `.mcp.json` 의 `mcpServers` 객체에 추가 (GA4와 같은 파일). **본 OS 는 공식 npm 패키지** `@microsoft/clarity-mcp-server` 를 `npx` 로 실행한다 — 별도 빌드 불필요:

```json
{
  "mcpServers": {
    "clarity": {
      "command": "npx",
      "args": ["-y", "@microsoft/clarity-mcp-server"],
      "env": {
        "CLARITY_PROJECT_ID": "{YOUR_CLARITY_PROJECT_ID}",
        "CLARITY_API_TOKEN": "eyJhbGciOiJSUzI1NiIs..."
      }
    }
  }
}
```

> `CLARITY_PROJECT_ID` 는 § 3.3 에서 확인한 본인 프로젝트 ID, `CLARITY_API_TOKEN` 은 § 3.2 에서 발급한 JWT 로 교체.
>
> (참고) 자체빌드 버전을 쓰고 싶다면 `command: "node"` + `args: ["/절대경로/clarity-mcp-server/build/index.js"]` 로 대체 가능 — 부록 참조.

### 3.5 검증

```
Clarity에서 어제 rage click이 가장 많이 발생한 페이지 TOP 3 알려줘
```

> **API 호출 한도**: Clarity Data Export API는 **프로젝트당 일 10회 제한**. 강의 시연 전에 한도가 남아있는지 확인.

### 3.6 Clarity의 역할과 자주 분석하는 항목

> **⚠️ Clarity Data Export API 제약사항 (분석 전 반드시 확인)**
>
> | 제약 | 한도 | 실무 영향 |
> |---|---|---|
> | **일일 API 호출** | **프로젝트당 10회/일** (UTC 자정 리셋) | 한 질문이 1회 차감. 세션 녹화·대시보드 모두 합산. 시행착오 포함 |
> | **데이터 조회 기간** | **최근 1~3일만 가능** | 7일·30일·월간 비교는 API로 불가 → Clarity 웹 대시보드에서 직접 확인 |
> | **세션 녹화 조회 수** | 요청당 최대 **250개** | 250개 넘으면 필터를 더 좁히거나 정렬 변경 |
> | **차원(Dimension)** | 요청당 최대 **3개** | URL × Device × Browser 동시 요청 가능. 그 이상은 분리 호출 |
> | **세션 녹화 보존** | 30일 (Clarity 기본) | API는 1~3일이지만 웹 대시보드는 30일까지 재생 가능 |
>
> **호출 절약 팁**
> - 같은 질문을 다시 묻지 말 것 — 한 번 받은 결과는 캐시처럼 재사용
> - 차원을 묶어서 한 번에 (예: "URL별·Device별 Rage Click TOP 10" → 1회로 2차원 동시 확인)
> - 빈 결과가 나오면 **필터를 좁히기 전에 넓혀서 검증** (트래킹 누락인지 데이터 부재인지 판단)
> - 강의 시연 직전엔 한도 확인. 한도 초과 시 다음 UTC 자정까지 대기

> **본 워크스페이스의 데이터 분담 원칙 (재확인)**
> - **GA4** → utm 유입 + 트래픽 볼륨 + 신규/재방문
> - **Meta** → ROAS·매출 (Ads Manager 안에서 완결)
> - **Clarity** → **행동 디테일** (왜 이탈했나·어디서 막혔나, 세션 녹화로 직접 관찰)
>
> Clarity는 "숫자가 아니라 행동"을 본다. GA4가 "이탈률 40%"를 보여주면, Clarity는 "왜 이탈했는지" 화면 녹화로 보여준다. 광고비를 쓴 트래픽이 LP에서 어떻게 막히는지 진단하는 데 필수.

#### 1) Rage Click — 사용자가 짜증냈는지 [핵심]

같은 위치를 짧은 시간에 연속 클릭하는 행동. 버튼이 안 눌리거나 응답이 없을 때 사용자가 보이는 신호.

- 페이지별 Rage Click 발생률·횟수
- Rage Click이 자주 나는 요소(버튼/링크/이미지) 식별
- 디바이스별 Rage Click 차이 (모바일에서 폭발 빈번)
- Rage Click 발생 직후 이탈 여부

> 예시 질의: "최근 3일 Rage Click TOP 5 페이지", "주문서에서 Rage Click이 발생하는 요소를 찾아줘", "Rage Click 발생 세션 녹화 5개"

#### 2) Dead Click — 작동 안 하는 요소 [핵심]

클릭했는데 아무 반응이 없는 요소. 깨진 링크·비활성 버튼·잘못된 이미지 컨테이너.

- 페이지별 Dead Click 비율
- Dead Click 발생 요소 (CTA·쿠폰 적용·주소 검색 등)
- 결제·주문서처럼 전환 직전 페이지의 Dead Click (매출 직격)
- 모바일/PC별 Dead Click 차이

> 예시 질의: "Dead Click 비율 높은 페이지 TOP 5", "주문서 페이지에서 Dead Click 나는 버튼", "장바구니 Dead Click이 있는 세션 녹화"

#### 3) 세션 녹화 (Session Recording) — 실제 행동 관찰 [핵심]

집계 숫자로는 보이지 않는 사용자 여정을 영상으로 직접 본다. Clarity의 가장 큰 차별점.

- 특정 페이지(주문서·장바구니·LP) 방문 세션 녹화
- 특정 채널(Meta 광고/네이버) 유입 세션 녹화
- 이탈 세션 vs 전환 세션 비교 관찰
- 특정 행동(쿠폰 클릭·할인 적용·검색) 발생 세션 추출

> 예시 질의: "주문서까지 갔다가 이탈한 세션 녹화 10개", "Meta 광고로 유입돼서 3분 이상 체류한 세션", "구매 완료한 사용자의 전체 여정"

#### 4) Quick Back — 첫인상 실패 페이지

페이지에 들어왔다가 매우 짧은 시간에 뒤로가기로 이탈. 광고 LP의 메시지 미스매치 신호.

- LP·랜딩 페이지별 Quick Back 비율
- 채널·캠페인별 Quick Back (광고-LP 일관성 점검)
- 디바이스별 Quick Back 차이
- 광고 후킹과 LP 헤드라인 정합성 진단

> 예시 질의: "Quick Back 비율 TOP 5 페이지", "Meta 광고 유입 LP의 Quick Back 비율", "캠페인별 Quick Back 비교"

#### 5) Scroll Depth — 콘텐츠 어디까지 봤나

페이지를 어디까지 스크롤했는지. 헤드라인·CTA·후기 노출 여부 진단.

- 페이지별 평균 스크롤 깊이
- 핵심 CTA·후기 영역 도달률
- 디바이스별 스크롤 패턴 차이 (모바일은 더 짧게 끊김)
- 스크롤이 멈추는 지점 (히트맵)

> 예시 질의: "메인 LP 평균 스크롤 깊이", "스크롤 깊이가 가장 낮은 페이지 5개", "모바일에서 50% 이상 스크롤한 비율"

#### 6) (보조) JavaScript 오류 · 성능 문제

전환을 막는 기술적 이슈를 마케터가 1차로 잡아내는 용도. 개발팀에 전달할 근거 데이터.

- Script Error 발생 페이지·비율
- 모바일/특정 브라우저(Safari 등)에서 집중 발생하는 오류
- LCP / CLS가 나쁜 페이지 (광고 LP 우선)
- 로딩 시간이 긴 페이지 (광고비 낭비 직결)

> 예시 질의: "Script Error TOP 5 페이지", "모바일에서 JS 오류 많은 페이지", "LCP 나쁜 LP"

#### 7) (보조) 디바이스 · 채널 교차 분석

GA4 유입 데이터와 결합해 "어디서 들어온 누가 어떻게 막히는지" 진단.

- 모바일 vs PC의 행동 이슈 차이
- Meta 광고 유입 사용자의 Dead Click·Rage Click 발생률
- 캠페인별 세션 시간·참여도

> 예시 질의: "Meta 광고 유입 사용자의 Dead Click 발생률", "모바일 사용자가 주문서에서 막히는 이유"

#### 분석 영역별 도구 매핑 (Clarity 관점)

| 무엇을 알고 싶나 | 도구 | 이유 |
|---|---|---|
| 사용자가 어디서 화났나 | **Clarity** (Rage Click) | 좌절 신호 직접 측정 |
| 어떤 요소가 안 작동하나 | **Clarity** (Dead Click) | 클릭 vs 반응 매칭 |
| 실제로 어떻게 행동했나 | **Clarity** (세션 녹화) | 영상 재생, 유일 |
| 광고-LP 메시지 정합성 | **Clarity** (Quick Back) | 첫인상 실패 신호 |
| 콘텐츠 어디까지 봤나 | **Clarity** (Scroll Depth) | 히트맵 단위 |
| 이탈률 수치 | **GA4** | 사이트 단위 통합 |
| 퍼널 단계 수치 | **GA4** (보조) / **Clarity** (원인) | GA4=수, Clarity=왜 |
| ROAS·매출 | **Meta** | 픽셀 매출 × spend |

#### 광고 트래픽 진단 시나리오 (Clarity 우선 적용)

| 상황 | 1차 도구 | 후속 |
|---|---|---|
| Meta CTR은 높은데 전환 없음 | **Clarity** Quick Back · 세션 녹화 | LP 헤드라인·후킹 점검 |
| 장바구니 도달했는데 결제 이탈 | **Clarity** Dead Click · 결제 단계 녹화 | 결제 UI / PG 점검 |
| 모바일만 전환률 급락 | **Clarity** 모바일 세션 녹화 · JS 오류 | 모바일 UI 회귀 확인 |
| 신규 LP 런칭 직후 진단 | **Clarity** Scroll Depth · Rage Click | 카피·CTA 위치 조정 |

#### 다음 단원에서 확장

| 분석 영역 | 단원 |
|---|---|
| Clarity 행동 KPI 정의 (Rage/Dead Click 임계값) | 4-2 KPI/임계값 |
| 일일 모니터링 시 Clarity 이상 감지 | 4-3 일일 리포트 |
| 통합 대시보드 (GA4 유입 + Meta ROAS + Clarity 행동) | 4-4 마케팅 대시보드 |
| 캠페인 사후 분석 (LP 진단 보고서) | 4-5 캠페인 리포트 |

> **연관 문서**: 더 많은 자연어 질의 예시는 [`CLARITY_MCP_FAQ_FOR_MARKETERS.md`](./CLARITY_MCP_FAQ_FOR_MARKETERS.md) 참고. 본 절은 마케터가 "무엇을 봐야 하는가"의 항목 정리에 집중.

---

## 4. Meta Marketing API 연결

Meta 는 **Developer App + System User Access Token (만료 없음)** 방식으로 연결한다. 권한은 **`ads_read` 단일 스코프 (read-only)**. 토큰은 `09_tracking/.env` 한 파일에 격리 관리. 본 트랙은 cron 자동 리포트 (10·11·12) + Claude Code 자연어 쿼리 양쪽 모두 공통 진입점.

**SDK 트랙을 디폴트로 채택한 이유** (CLI OAuth 트랙 대비, 본 OS 사용자 페르소나가 1인 마케터·에이전시·클라이언트 광고 계정 분석이라 보안이 결정적):
- **권한 정밀 통제** — System User 토큰 발급 시 `ads_read` 만 부여 → 토큰 자체가 물리적 read-only. 실수로 캠페인 수정·삭제 불가
- **자산 범위 제한** — System User 에 특정 광고 계정만 사전 할당. 다른 클라이언트 계정 누설 불가
- **명령 실행 범위** — Claude 는 Python 스크립트만 실행 (코드 리뷰 가능). CLI 처럼 임의 명령 합성 불가
- **격리·감사** — 자격증명이 `.env` 한 파일에 명시. Business Manager 에서 1클릭 revoke 가능
- **만료 없음** — System User Token 은 영구 → cron 무인 운영 안정. CLI OAuth 는 만료 시 사용자 개입 필요

> ⚠️ **사전 요구**: **Business Manager Admin 권한 필요** (App 생성·System User 발급에 필수). 권한이 없는 1인 운영자는 § 4.5 트러블슈팅의 "Graph API Explorer 60일 long-lived" 우회 또는 § 4.8 CLI 부록 검토.

### 4.1 Developer App 생성

[Meta for Developers](https://developers.facebook.com/) → My Apps → Create App:

1. 사용 케이스: **Other** → 앱 유형 **Business** → 다음
2. 앱 이름: `Claude Code Ads OS` (식별 가능한 이름. Meta 정책상 "Facebook·Meta·Instagram·WhatsApp" 단독 단어 금지)
3. 비즈니스 계정 연결: 본인 Business Manager 선택 → 생성
4. **앱 설정 → 기본 설정** 진입:
   - **App ID** (15~16자리 숫자) 복사 → `.env` 의 `META_APP_ID`
   - **App Secret** (Show 클릭 + 비밀번호 재입력 필요) 복사 → `.env` 의 `META_APP_SECRET`
5. 좌측 메뉴 → **제품 추가 → Marketing API → 설정** (이 단계 누락 시 호출 실패)

### 4.2 System User + Token 발급 (★ 보안 핵심)

[business.facebook.com](https://business.facebook.com/) → 좌측 하단 ⚙️ **Settings**:

1. **Users → System Users → Add**
   - 이름: `claudecode-ads-readonly` (권한 의도가 보이는 이름)
   - 역할: **Employee** (Admin ❌ — 최소권한 원칙)
2. **Add Assets → Ad Accounts**
   - 분석할 광고 계정만 체크 (다른 클라이언트 계정 체크 ❌)
   - 권한: **View performance** (Manage campaigns ❌)
3. **Generate New Token**:
   - 앱 선택: § 4.1 의 `Claude Code Ads OS`
   - 만료: **Never** ★
   - 권한 스코프: **`ads_read` 단일 체크** ★ (`ads_management` · `business_management` 절대 체크 ❌)
4. 토큰 표시 화면에서 즉시 복사 (한 번만 노출됨) → `.env` 의 `META_ACCESS_TOKEN`

> ⚠️ 이 단계가 OS 보안의 핵심. 토큰이 유출되더라도 (a) **할당한 계정만** 접근, (b) **읽기 권한만** 행사. 다계정 에이전시는 클라이언트마다 별도 System User 권장.

### 4.3 `.env` 작성 + 권한

`09_tracking/.env.example` 을 `.env` 로 복사하고 4개 값 채움:

```bash
META_APP_ID=000000000000000              # § 4.1
META_APP_SECRET=abcdef1234567890...      # § 4.1
META_ACCESS_TOKEN=EAAxxxxxxxxxxxxx...    # § 4.2
META_AD_ACCOUNT_ID=act_XXXXXXXXXXXXXXX   # Ads Manager URL ?act= 값 + act_ 접두사
# META_API_VERSION=v21.0                 # 선택, 기본 v21.0
```

`.gitignore` 확인:
```bash
grep "09_tracking/.env" .gitignore || echo "09_tracking/.env" >> .gitignore
```

### 4.4 동작 검증

Python SDK 설치 + 1줄 검증:

```bash
pip3 install facebook-business python-dotenv pyyaml requests

python3 -c "
import os
from dotenv import load_dotenv
load_dotenv('09_tracking/.env')
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

FacebookAdsApi.init(
    app_id=os.environ['META_APP_ID'],
    app_secret=os.environ['META_APP_SECRET'],
    access_token=os.environ['META_ACCESS_TOKEN'],
    api_version='v21.0'
)
acct = AdAccount(os.environ['META_AD_ACCOUNT_ID'])
for row in acct.get_insights(
    fields=['spend','impressions','clicks','ctr','cpc'],
    params={'date_preset':'yesterday'}
):
    print(row)
"
```

어제 광고비·노출·클릭·CTR·CPC 한 줄이 찍히면 OK. Claude Code 세션 안에서 "메타 어제 ROAS 표로" 같은 자연어 쿼리는 Claude 가 `_shared/scripts/lib/meta_client.py` 헬퍼를 import 한 Python 스크립트를 Bash 로 실행하는 패턴 (코드가 출력되므로 사용자 사전 검토 가능 → 안전).

### 4.5 트러블슈팅

| 증상 | 처방 |
|---|---|
| `OAuthException: (#190) Invalid OAuth access token` | 토큰 무효 → § 4.2 재발급 |
| `(#100) Tried accessing nonexisting field` | 필드명 오타 (예: `ctr_unique` → `ctr`) |
| `(#10) Application does not have permission` | Marketing API 제품 미추가 (§ 4.1 단계 5) |
| `(#3) Application not authorized` | System User 에 광고 계정 미할당 (§ 4.2 단계 2) |
| `(#17) User request limit reached` | BUC rate limit → 300초 대기, § 4.7 참고 |
| 어제 ROAS 비어있음 | (1) 광고 미집행 또는 (2) Meta 어트리뷰션 윈도우 미확정 — 09:00 이후 재조회 |
| BM Admin 권한 없음 | Graph API Explorer 의 60일 long-lived 토큰 우회 (Tools → Access Token Tool → Extend) — 60일마다 수동 갱신. 또는 § 4.8 CLI 부록 (단점 인지 후) |
| 토큰 노출 사고 | developers.facebook.com → 앱 → **App Secret 재설정** + Business Manager → System User → **Revoke Token** + git 히스토리 점검 |

상세는 [09_tracking/MetaAds_연결_가이드.md § 8 트러블슈팅](./09_tracking/MetaAds_연결_가이드.md) 참고.

### 4.6 미지원 기능

| 기능 | SDK 트랙 (ads_read) | 본 OS 영향 |
|---|---|---|
| 캠페인 인사이트 (spend·ROAS·CTR·CPM·전환) | ✅ | — |
| 캠페인 read-only 메타데이터 (이름·예산·objective·상태) | ✅ | — |
| 카탈로그·데이터셋·진단·Lead Ads (목록·읽기) | ✅ | — |
| **캠페인 생성·수정·삭제** | ❌ (`ads_read` 만 부여, 의도적 제외) | 본 OS 는 read-only 분석 |
| **Advantage+ 자동 최적화·입찰 알고리즘·잠재고객 확장** | ❌ | 안 씀 |

→ 본 OS 의 10·11·12 리포트와 04/05/07/08 콘텐츠 스킬에 필요한 데이터는 모두 지원 범위.

### 4.7 API 제약사항

운영 중 가장 자주 부딪히는 한도 — SDK 든 CLI 든 동일하게 적용 (둘 다 Meta Marketing API 의 같은 엔드포인트 호출). 일일 리포트가 갑자기 침묵하면 대부분 아래 항목과 연관된다.

#### 4.7.1 호출 한도 — Business Use Case (BUC) Rate Limit

Meta는 분당 호출수 모델 대신 **5분 단위 점수 누적** 방식을 쓴다.

| 항목 | Development Tier | Standard Tier |
|---|---|---|
| 누적 점수 | 60점 / 300초 | 9,000점 / 300초 |
| 점수 소모 | 읽기 1점, 쓰기 3점 | 동일 |
| 초과 시 차단 | 300초 | 60초 |
| 광고세트 예산 변경 | 4회/시간 (티어 무관) | 동일 |

- 신규 앱은 Dev tier에서 시작. **Standard tier 승급**은 Meta App Review 통과 + 일정 운영 이력 필요.
- 일일 리포트(읽기) 한 번 실행 시 약 **5점** (계정·캠페인·광고·전일·주간 5개 호출). 광고 100개↑ 라 페이지네이션이 필요하면 점수 증가.
- 응답 헤더 `X-Business-Use-Case-Usage` 로 잔여 점수 실시간 확인.
- 공식: [Rate Limiting](https://developers.facebook.com/docs/marketing-api/overview/rate-limiting)

> **🧑‍🏫 쉽게 풀어보면 — "하루에 몇 번 부를 수 있나?"**
>
> 처음 보면 "60점"이 헷갈리는데, **시간 단위가 5분**이라는 점이 핵심이다.
>
> | 단위 | 가능 횟수 | 의미 |
> |---|---:|---|
> | 5분 안에 | **약 12번** | 60점 ÷ 1회당 5점 |
> | 1시간 안에 | 약 144번 | 5분마다 점수가 다시 회복되니까 |
> | 하루 | 사실상 **수천 번 가능** | |
>
> **운영 시나리오별 한도 사용량**
>
> | 패턴 | 한도 대비 | 막힐까? |
> |---|---|---|
> | 하루 1회 cron (08:30) | 1/12 사용 | ❌ 전혀 |
> | 시간당 1번 (24회/일) | 1/12 사용 | ❌ 전혀 |
> | 5분마다 자동 새로고침 | 딱 한도 | ⚠️ 빠듯 |
> | 한꺼번에 13번 연속 클릭 | 한도 초과 | ✅ 5분 대기 |
>
> **한 줄 결론**: Dev tier 60점은 *"5분에 12번 부르지 마라"* 라는 뜻. 하루 1회 cron은 한도의 **8% 정도만** 쓰는 셈이라 신경 안 써도 된다. 막히는 시점은 디버깅 하느라 짧은 시간에 같은 호출을 반복할 때, 또는 여러 광고 계정을 batch로 돌릴 때 정도.

#### 4.7.2 어트리뷰션 — iOS14.5 이후 변화

| 옵션 | 비고 |
|---|---|
| **7-day click + 1-day view** | 기본값·Meta 권장 |
| 1-day click | iOS 사용자는 사실상 이 값에 수렴 |
| 28-day click | 2021년 이후 사라짐 |

- iOS14.5 이후 어트리뷰션 정확도 **40~60% 하락** 추정 (업계 분석 기준).
- 보완책: **Conversions API (CAPI)** 서버 이벤트 + 픽셀 동시 송신 → dedup.
- `purchase_roas` 는 어트리뷰션 윈도우에 따라 값이 달라지므로 비교 시 동일 윈도우인지 확인.

#### 4.7.3 토큰 만료 (SDK 트랙 한정)

| 종류 | 유효기간 | 용도 |
|---|---|---|
| Short-lived User Token | 1~2시간 | 발급 직후 즉시 변환 |
| Long-lived User Token | 약 60일 | 개인 테스트용 (자동화 부적합) |
| **System User Token** | **만료 없음** | 자동화·cron 권장 |

- 60일 토큰은 cron이 한 번 침묵한 뒤로 무한 실패 — 운영 전에 System User 토큰 교체 필수.
- System User 토큰도 권한 변경·앱 비밀번호 재설정 시 무효화 → `.env` 갱신 절차 마련.

#### 4.7.4 데이터 freshness · 보관

- **실시간 지표** (spend, impressions, clicks): 발생 후 1~3시간 지연.
- **전환 지표** (purchases, ROAS): 어트리뷰션 윈도우 만료 후 안정화 — 7d click 사용 시 **최소 7일 후 확정값**. 당일·익일 ROAS는 잠정값.
- **Insights 보관**: **37개월** (≈3년 1개월). 이전 데이터는 API 조회 불가 → BigQuery·Sheets 등으로 별도 백업 필요.

#### 4.7.5 동기 vs 비동기 조회

| 케이스 | 권장 방식 |
|---|---|
| time_range ≤ 7일, level=account/campaign | 동기 `get_insights` |
| time_range > 90일 | **비동기 필수** |
| level=ad + breakdowns 2개 이상 | **비동기 필수** |
| 광고 100개↑ 계정의 ad 단위 조회 | **비동기 필수** |

- 비동기: `report_run_id` 발급 → status 폴링 (간격 30초 권장) → 최대 24시간 안에 완료 → `insights` edge로 결과 fetch.

#### 4.7.6 단일 호출 한도

| 제약 | 값 |
|---|---|
| 페이지당 row | 25,000 (cursor 페이지네이션) |
| breakdowns 조합 | 대부분 1~2개 (`age+gender` ✅, `age+placement` ❌) |
| insights fields | 권장 25개 이내 (소프트 한도) |
| 동시 비동기 작업 | 계정당 5~10개 |
| 광고 계정당 활성 광고/캠페인 | 각각 5,000개 |

- breakdowns 호환성 표: [Meta 공식](https://developers.facebook.com/docs/marketing-api/insights/breakdowns).

#### 4.7.7 운영 권장 패턴

1. **일일 리포트** — 어제 1일 동기 호출 + 광고 30개 이내. Dev tier OK.
2. **주간 분석** — 7일 동기 호출, level=ad, breakdowns 1개. 2~3분.
3. **월간 캠페인 리포트** — 비동기 + 30초 폴링.
4. **재시도** — 오류 코드 17 / 4 / 80004 발생 시 **지수 백오프** (60s → 300s → 900s). 즉시 재시도 금지.

### 4.8 부록 A — CLI 트랙 (편의·실험용, 보안 가드 필수)

> **언제 쓰나**
> - **Business Manager Admin 권한이 없고** Graph API Explorer 60일 long-lived 토큰 갱신도 부담스러울 때
> - 일회성 탐색·실험 (실제 클라이언트 자산 미접근)
> - § 4.1~4.6 SDK 트랙이 디폴트 — CLI 는 명시적 trade-off (자산 격리 불가·자율성 위험) 인지 후 사용
>
> **본 부록의 보안 가드를 모두 지키지 않으면 사용 금지.** 10·11·12 cron 스킬은 반드시 SDK 트랙 사용 (OAuth 만료 시 무인 운영 끊김).

**보안 가드 (의무)**:

1. **OAuth 스코프 최소화** — `meta auth login` 권한 화면에서 **`ads_read` 만** 체크. `ads_management` · `business_management` 절대 체크 ❌
2. **광고 계정 선택** — OAuth 흐름에서 분석 대상만 체크 (모든 계정 선택 ❌)
3. **Bash 화이트리스트는 읽기 명령만** —
   - ✅ `meta ads * list`, `meta ads insights *`, `meta auth whoami`
   - ❌ `meta ads * create`, `meta ads * update`, `meta ads * delete`, `meta ads * pause`
4. **토큰 저장 위치 확인** — 셋업 직후 `ls -la ~/.config/meta-ads/` (또는 macOS Keychain)
5. **패키지 publisher 검증** — `pip show meta-ads-cli` 로 publisher · GitHub 레포 확인. 의심스러우면 [공식 블로그](https://developers.facebook.com/blog/post/2026/04/29/introducing-ads-cli) 의 정확한 패키지명 재확인 (typosquatting 방어)

**설치 + OAuth**:

```bash
python3 --version              # Python 3.12+ 확인
brew install pipx && pipx ensurepath
pipx install meta-ads-cli      # ★ 정확한 패키지명은 공식 블로그 재확인 (베타 단계)
meta auth login                # ★ ads_read 만 체크 + 분석 대상 계정만 체크
meta auth whoami
```

**동작 확인**:

```bash
meta ads campaign list --output table
meta ads insights get --date-preset yesterday --fields spend,impressions,clicks,ctr --output json
```

**CLI 한계 (재확인)**:

- 토큰이 사용자 홈에 저장 — 자산 격리 불가 (다계정 노출 위험)
- Claude 가 임의의 `meta ads ...` 합성 가능 → 자율성 ↑, 사고 위험 ↑
- OAuth 만료 시 사용자 개입 필요 → cron 부적합 (10·11·12 는 SDK 필수)
- 베타 단계 차단 사례 있음 → § 4.5 트러블슈팅 후에도 안 풀리면 SDK 트랙 전환

상세는 [09_tracking/MetaAds_연결_가이드.md § 9 부록 A](./09_tracking/MetaAds_연결_가이드.md) 참고.

---

## 5. 통합 검증

3개 소스 모두 연결됐는지 한 번에 확인.

### 5.1 체크리스트

```
□ GA4
  □ pipx + gcloud CLI 설치 (`pipx --version`, `gcloud --version` 확인)
  □ `pipx run analytics-mcp --help` 정상 출력
  □ GCP 프로젝트에 Analytics Admin/Data API 사용 설정
  □ `gcloud auth application-default login` 완료 + quota project 지정
  □ `.mcp.json` 에 `analytics-mcp` 등록, `GOOGLE_PROJECT_ID` 입력
  □ Claude에서 "GA4 지난 7일 세션" 질의 성공

□ Clarity
  □ API 토큰 발급 (한도 미초과)
  □ Project ID 정확
  □ Claude에서 "Clarity rage click" 질의 성공

□ Meta
  □ .env 파일 작성 (.gitignore 포함)
  □ 토큰 권한: ads_read, ads_management, pages_read_engagement
  □ test_meta_api.py 실행 성공
```

### 5.2 통합 시연 쿼리 (강의 영상용)

각 소스의 도구가 살아있음을 보여주는 짧은 시연:

```
1. GA4: "어제 채널별 세션·전환수를 표로 보여줘"
2. Clarity: "어제 rage click 발생 페이지 TOP 3"
3. Meta: "지난주 ROAS 하위 5개 캠페인을 일자별 추이와 함께"
```

세 응답이 모두 정상이면 4-2 KPI 정의 단원으로 진행 가능.

---

## 6. 트러블슈팅

### GA4

**`pipx: command not found` 또는 `gcloud: command not found` (또는 Windows의 `'pipx'은(는) 명령으로 인식되지 않습니다`)**
- macOS: `brew install pipx && pipx ensurepath` → 새 터미널.
- Windows: `python -m pip install --user pipx` + `python -m pipx ensurepath` → **PowerShell 완전히 닫고 새로 열기**.
- gcloud는 macOS는 `brew install --cask google-cloud-sdk`, Windows는 [공식 인스톨러](https://cloud.google.com/sdk/docs/install#windows) 사용.

**Windows: `python: 인식되지 않습니다`**
- Python 설치 시 "Add Python to PATH" 체크 누락. python.org에서 재설치하면서 체크박스 ON.
- 또는 `py --version` 으로 시도 (Windows Python Launcher).

**`pipx run analytics-mcp` 실행 시 패키지 다운로드 후 무반응**
- `--help` 옵션을 붙여 동작 확인: `pipx run analytics-mcp --help`. CLI 옵션 없이 실행하면 stdio MCP 서버 모드라 터미널에서는 출력이 없는 게 정상.

**`Could not automatically determine credentials` / `default credentials not found`**
- ADC가 설정되지 않음 → `gcloud auth application-default login` 다시 실행.
- 자격증명 파일 위치 확인: `ls ~/.config/gcloud/application_default_credentials.json`.

**`Your default credentials were not found` + quota project 관련 경고**
- `gcloud auth application-default set-quota-project YOUR_PROJECT_ID` 실행.
- `.mcp.json` 의 `GOOGLE_PROJECT_ID` 값과 quota project가 일치해야 함.

**`PERMISSION_DENIED: Request had insufficient authentication scopes`**
- ADC 로그인 시 `analytics.readonly` 스코프 누락. 2.4 명령어 그대로 다시 실행 (`--scopes=...` 포함).

**`This API method requires billing to be enabled`** 또는 API 호출 거부
- GCP 프로젝트에서 Analytics Admin/Data API가 활성화되지 않음 → 2.3 단계 재확인.

**"이 앱은 확인되지 않았습니다" 경고 (gcloud OAuth 화면)**
- gcloud 자체 OAuth 클라이언트라 정상. **고급 → 안전하지 않은 페이지로 이동** 클릭.

**ADC 토큰 갱신 / 다른 계정으로 재로그인**
- 기존 ADC 자격증명 폐기 후 다시 로그인:
  ```bash
  gcloud auth application-default revoke
  gcloud auth application-default login \
    --scopes='openid,https://www.googleapis.com/auth/userinfo.email,https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform'
  ```
  Claude Code 재시작.

### Clarity

**401 Unauthorized**
- 토큰 만료 or 복사 시 공백 포함. 재발급 후 재등록.

**429 Too Many Requests**
- 일 10회 한도 초과. 24시간 대기. 강의 시연 전 한도 확인 필수.

**MCP 서버 인식 안됨**
- 공식 패키지 사용 시: `.mcp.json` 의 `args` 가 `["-y", "@microsoft/clarity-mcp-server"]` 인지 확인. `npx -y @microsoft/clarity-mcp-server --help` 로 패키지 fetch 가능 여부 점검.
- (자체빌드 옵션 사용 시) `clarity-mcp-server/build/index.js` 파일 존재 확인 (`npm run build` 다시 실행).
- Claude Code 재시작 필수. 재시작 후에도 안 잡히면 `.mcp.json` JSON syntax (`jq . .mcp.json`) 검증.

### Meta

**오류 코드 190 (토큰 만료)**
- 단기 토큰을 장기 토큰으로 변환했는지 확인. System User 토큰 권장.

**오류 코드 100 (잘못된 파라미터)**
- `act_` 접두사 누락이 흔한 원인. `META_AD_ACCOUNT_ID=act_xxx` 형식 확인.

**오류 코드 17 / 4 / 80004 (호출 제한)**
- BUC 점수 한도 초과. 분당 호출수 모델이 아니라 5분 단위 점수 누적. 자세한 한도와 티어는 [4.5.1 BUC Rate Limit](#451-호출-한도--business-use-case-buc-rate-limit) 참조.
- 즉시 재시도 금지. 지수 백오프 (60s → 300s → 900s).
- 응답 헤더 `X-Business-Use-Case-Usage` 로 잔여 점수 확인.

**대용량 조회가 timeout / 빈 응답**
- time_range > 90일, level=ad + breakdowns 2개 이상은 동기 호출 한계. [4.5.5 비동기 조회](#455-동기-vs-비동기-조회) 패턴으로 전환.

**ROAS 값이 매일 바뀌는데 정상인지**
- 7-day click 어트리뷰션 윈도우 사용 시 **7일 뒤 확정**. 당일·익일 ROAS 는 잠정값. [4.5.4](#454-데이터-freshness--보관) 참조.

---

## 7. 부록: 보조 문서

이 가이드는 마스터 문서다. 더 깊이 파고들 때 참조할 보조 문서:

| 문서 | 용도 |
|------|------|
| `CLARITY_MCP_SETUP_GUIDE.md` | Microsoft 공식 패키지(`@microsoft/clarity-mcp-server`) 셋업 — 커스텀 빌드 대신 사용할 때 |
| `CLARITY_MCP_FAQ_FOR_MARKETERS.md` | Clarity 활용 FAQ (필터 사용법, 세션 녹화 분석 등) |
| `meta_api_campaign_setup.md` | Meta API로 캠페인을 **생성**하는 방법 (본 가이드는 데이터 **읽기**까지만 다룸) |
| `_shared/scripts/lib/meta_client.py` | Meta API 호출 SDK 헬퍼 (본 OS 는 자연어 쿼리 + 이 헬퍼 import Python 스크립트 사용) |

### MCP 서버 도구 빠른 레퍼런스

**GA4** (`analytics-mcp`, Google 공식 Python 패키지 — `googleanalytics` org):
- 속성 목록 조회, 표준 리포트 (세션·이벤트·전환·매출, 채널/페이지/디바이스별), 실시간 데이터 등 GA4 Data API + Admin API 지원
- 자세한 도구 목록: `pipx run analytics-mcp --help` 또는 [GitHub 레포](https://github.com/googleanalytics/google-analytics-mcp)

**Clarity MCP** (`clarity-mcp-server`):
- `get_metrics` — 기간·차원별 집계 지표
- `get_sessions` — 세션 녹화 목록 (필터링 가능)
- `get_heatmap` — 페이지별 클릭/스크롤 히트맵
- `get_insights` — rage-clicks, dead-clicks, JS 에러 등 자동 인사이트

**Meta** (Python SDK 기반, MCP 아님):
- `fetch_meta_ads.py` — 캠페인/광고세트/광고 단위 실적 fetch
- `analyze_performance.py` — 임계값 기반 저성과 탐지

---

## 다음 단원

3개 API가 연결됐다면, 단원 2 **`kpi-definer`** 로 이동해 **무엇을 보고 의사결정할 것인가**(KPI/임계값) 를 정의한다. 그 정의가 단원 3·4·5의 입력이 된다.

---

## 부록 A — (이전 위치) GA4 서비스 계정 방식

> 본 단원은 2026-05-27 보안 우선 개편으로 **§ 2 메인 본문 (§ 2.4~2.7) 으로 승격** 되었다. 트러블슈팅·세부 설정 모두 § 2 와 [09_tracking/GA4_연결_가이드.md](./09_tracking/GA4_연결_가이드.md) 에서 다룬다.
>
> 이전 가이드에서 "옵션 B (OAuth ADC)" 가 디폴트였던 정책은 GA4 admin 권한 없는 클라이언트 분석 환경의 편의를 우선했던 결과였으나, 1인 마케터·에이전시·다계정 운영의 보안 사고 위험을 더 무겁게 보는 쪽으로 정책 변경됨. OAuth ADC 트랙은 § 2.8 부록으로 강등 (BM 권한 없는 1인 운영자·일회성 다계정 접근 용도).
>
> Meta SDK 트랙 (§ 4) 과 동일한 보안 정책 패턴 — 명시적 자산 할당 + read-only + 만료 없음 + 격리된 자격증명 파일.

---

## 부록 C — MCP 서버 선택 체크리스트

MCP 서버 생태계는 빠르게 커지는 중이고, **이름이 비슷한 서드파티 패키지가 공식 패키지보다 검색 상위에 노출되는 경우**가 흔하다. 이 가이드의 GA4 섹션도 처음에는 서드파티 `google-analytics-mcp`(개인 개발자 `surendranb`)를 안내했다가, 공식 `analytics-mcp`(`googleanalytics` 조직)으로 정정한 이력이 있다. 강의에서 추천하든, 실무에 도입하든, MCP 서버는 다음 6가지를 통과한 것만 사용한다.

### 1. 공식 vs 서드파티

가장 먼저 확인. 패키지 이름이 비슷해도 **GitHub 조직(org)이 누구인지** 가 결정적.

| 신호 | 의미 |
|---|---|
| `github.com/googleanalytics/...`, `github.com/microsoft/...` | 서비스 회사가 직접 관리 (공식) |
| `github.com/<개인 ID>/...` | 서드파티. 코드 리뷰 필수 |

PyPI / npm 검색 결과만 보고 판단하지 말 것. 패키지 페이지의 **Repository / Homepage 링크를 클릭해 org를 확인**.

### 2. 메인테이너

- **조직** vs **개인**: 개인 메인테이너는 부재(번아웃·이직)에 취약. 강의처럼 6개월~1년 뒤에도 동작해야 한다면 조직 관리가 안전.
- **활동 빈도**: 마지막 commit이 6개월 이상 전이면 deprecated 가능성. 이슈가 누적되어 있는데 응답이 없으면 더 위험.

### 3. 별 수 · 이슈 응답

- **Stars**: 절대 기준은 없지만, 도메인이 활발한데 100개 미만이면 의심.
- **Issues / Discussions**: 사용자 질문에 메인테이너가 답하는가? 보안 관련 이슈가 방치되어 있는가? 활동 패턴이 신뢰의 1차 신호.

### 4. 권한 스코프

도구가 **읽기 전용**인지 **쓰기/관리자**까지 가능한지 확인.

- **Read-only** (`analytics.readonly`, `ads_read` 등): 비교적 안전. 사고가 나도 데이터 유출 수준.
- **Write/Admin** (`ads_management`, `cloud-platform` 풀권한 등): 잘못된 도구가 실수로 광고 캠페인을 수정하거나 GCP 리소스를 만들 수 있음. 반드시 필요한 만큼만 부여.

OAuth 동의 화면에서 요구하는 스코프를 끝까지 읽고, 강의에서도 **최소 권한**을 원칙으로 가르친다.

### 5. 자격증명 처리 방식

자격증명이 **어디에 저장되고, 어디로 전송되는가**.

- **로컬 보관 (좋음)**: gcloud ADC (`~/.config/gcloud/`), 환경변수, 로컬 JSON 파일.
- **외부 서버 경유 (위험)**: 메인테이너의 프록시 서버를 거쳐 인증한다면 토큰이 그 서버에 노출됨. README와 코드에서 확인.
- **README의 보안 섹션**: SECURITY.md 또는 보안 정책 페이지가 있는지. 없으면 보안 기준이 명문화되지 않은 프로젝트.

### 6. 최근 업데이트

- **MCP 스펙 자체**가 빠르게 진화하는 중. 마지막 릴리즈가 6개월 이상 전이면 호환성 깨졌을 가능성.
- **종속 API 버전**: GA4 Data API, Meta Marketing API 등 외부 API 버전 변경에 따라가는지 changelog 확인.

### 체크리스트 적용 예시

| 프로젝트 | 1.공식 | 2.메인 | 3.별/이슈 | 4.스코프 | 5.자격증명 | 6.최근업뎃 | 사용? |
|---|---|---|---|---|---|---|---|
| `analytics-mcp` (`googleanalytics`) | O | 조직 | O | readonly | 로컬 ADC | 활발 | **O** |
| `google-analytics-mcp` (`surendranb`) | X | 개인 | △ | readonly | 로컬 | △ | 검토용만 |
| 출처 불명 npm 패키지 | X | ? | X | ? | ? | ? | **X** |

> **요약**: MCP 서버는 "마케팅용 플러그인" 같은 가벼운 도구가 아니라, **자격증명을 통째로 위임하는 인증 클라이언트**다. 공식 패키지 우선, 서드파티는 코드 리뷰 후, 실험은 별도 GCP 프로젝트/광고 계정에서.

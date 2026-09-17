---
name: 09-tracking-setup
description: GA4 (OAuth ADC, 디폴트) + Microsoft Clarity + Meta Ads (User Access Token, 디폴트) 3개 데이터 소스를 Claudecode_MarketingOS_student 환경에 단계별로 연결하는 인터랙티브 안내자. 마스터 가이드 `SETUP_GUIDE.md` + 트랙별 상세 가이드 (`09_tracking/GA4_연결_가이드.md`·`09_tracking/MetaAds_연결_가이드.md` 등) 를 single source of truth 로 그때그때 읽고 한 단계씩 진행 (가이드 내용을 복붙하지 않음 — 가이드가 갱신되면 스킬도 자동으로 따라감). 사용자가 "셋업 도와줘", "트래킹 환경 만들어줘", "GA4 연결해줘", "Clarity 연결", "Meta 연결", "Meta API 연결", "데이터 소스 연결", "/09-tracking-setup" 등으로 요청하거나 셋업 도중 에러를 알릴 때 호출. 산출물은 `.mcp.json` 에 `analytics-mcp`·`clarity` 2개 항목 등록 (analytics-mcp env 에 `GOOGLE_PROJECT_ID` 만, `GOOGLE_APPLICATION_CREDENTIALS` 절대 추가 ❌) + `09_tracking/oauth-client.json` Desktop OAuth Client (chmod 600, .gitignore) + `~/.config/gcloud/application_default_credentials.json` ADC 토큰 (gcloud 자동 저장) + Meta Developer App + **User Access Token (60일 long-lived, `ads_read` only)** + `09_tracking/.env` 에 Meta SDK 환경변수 4개 작성 (chmod 600, .gitignore). 최초 1회 셋업이 끝나면 자연어로 GA4·Clarity·Meta 쿼리 가능. **GA4 트랙**: OAuth ADC 디폴트 (5분 셋업, 본인 구글 계정 권한 가진 모든 GA4 자동 노출, GA4 UI 의 사용자 추가 거부 케이스 회피). 서비스 계정 트랙은 cron 무인 운영·자산 격리 필요 시만 가이드 § 9 부록 A. **Meta 트랙**: User Token 단일 (5분 발급, BM Admin 권한 불필요, 60일 long-lived, `ads_read` 단일 스코프, Python SDK 호출).
---

# 09. 트래킹 셋업 — 데이터 소스 연결 안내자

3개 데이터 소스(GA4 / Microsoft Clarity / Meta Marketing API)를 클로드 코드와 연결하는 과정을 **한 단계씩** 진행시키는 인터랙티브 안내자.

가이드를 처음부터 끝까지 혼자 읽기 부담스러운 사용자를 위해, **읽고 → 실행 → 검증 → 다음 단계** 사이클로 진행시킨다. 가이드의 내용을 **복붙하지 말고**, 마스터 문서 [SETUP_GUIDE.md](../../../SETUP_GUIDE.md) 를 그때그때 읽고 그 단계만 진행시킨다.

## 원칙

1. **단일 진실 출처**: 모든 명령어·트러블슈팅·체크리스트는 [SETUP_GUIDE.md](../../../SETUP_GUIDE.md) 에서 가져온다. 스킬에 명령어를 하드코드하지 말 것 — 가이드가 바뀌면 스킬도 따라가야 함.
2. **한 단계씩**: 명령어 한 묶음을 보여주고 사용자가 실행할 때까지 기다린 뒤 검증한다. 한꺼번에 5개 명령어를 던지면 가이드와 다를 게 없다.
3. **검증 우선**: 각 단계 후 사용자에게 출력 결과를 물어보거나, 가능하면 직접 검증 명령(예: `pipx --version`, `pipx run analytics-mcp --help`, `grep client_email 09_tracking/ga4-credentials.json`)을 실행해 결과를 확인한다.
4. **에러는 가이드 매핑**: 사용자가 에러 메시지를 보내면 SETUP_GUIDE.md 섹션 6(트러블슈팅)에서 해당 패턴을 찾아 안내. 없으면 그제서야 외부 검색.
5. **사용자 기준**: 마케터 대상 OS 라 명령어를 처음 치는 사람도 있다. `cd` 같은 기본 동작도 친절하게.

## 워크플로우

### Step 0 — 진입점 분기

사용자가 호출하면 먼저 어떤 모드인지 파악:

- **"처음부터 셋업하고 싶어"** → 사전 준비 → GA4 → Clarity → Meta 순서로 진행
- **"GA4만/Clarity만/Meta만"** → 해당 섹션부터 진행
- **"이런 에러가 났어"** → SETUP_GUIDE.md 섹션 6에서 패턴 매칭 → 해결책 안내 → 재검증

대화 첫 응답에서 사용자에게 명시적으로 묻는다:
> 어떻게 도와드릴까요?
> 1. 3개 소스 처음부터 전체 셋업 (30분 정도)
> 2. 특정 소스만 (GA4 / Clarity / Meta 중 선택)
> 3. 진행 중 에러 해결 (어떤 단계에서 어떤 에러인지 알려주세요)

### Step 1 — 사전 준비 검증

전체 셋업 모드에서 먼저 SETUP_GUIDE.md 섹션 1.사전 체크리스트를 실행 가이드. 다만 명령어는 가이드를 직접 읽고 그 시점의 내용을 보여줄 것.

검증 포인트:
- `node --version` (≥ 18)
- `python3 --version` (≥ 3.10)
- 작업 디렉토리(`Claudecode_MarketingOS_student/`) 위치 확인

사용자가 출력을 붙여 넣으면 버전 비교 후 OK/조치 안내.

### Step 2 — GA4 (OAuth ADC 디폴트)

[09_tracking/GA4_연결_가이드.md](../../../09_tracking/GA4_연결_가이드.md) 를 따라 진행. GA4 는 **OAuth ADC 트랙 (A안, 디폴트)** — 본인 구글 계정으로 직접 인증. GA4 속성에 별도 권한 부여 단계 ❌, 본인 계정 권한 가진 모든 GA4 자동 노출. 가장 빠른 셋업 (10~15분).

**GA4 OAuth ADC 선택 이유** (사용자에게 처음 1회 안내):
- **셋업 5분** — GA4 속성에 사용자 추가하는 단계가 아예 없음 (본인 계정이 이미 admin)
- **GA4 UI 거부 회피** — 서비스 계정 트랙은 GA4 UI 의 "사용자 추가" 단계에서 "이메일이 Google 계정과 일치하지 않습니다" 같은 거부가 간헐 발생 (Workspace 조직 정책·신규 프로젝트 propagation 등이 원인). OAuth 는 본인 계정 사용이라 이 단계 자체 없음
- **1인 마케터·소상공인 적합** — 본인이 운영하는 GA4 모두 노출되는 게 오히려 자연스러움
- **trade-off 인지**: 본인 계정의 모든 GA4 자동 노출 (자산 격리 ❌), OAuth refresh token 수개월 후 만료 가능 (cron 무인 운영 부적합 → 그 경우만 § 2.8 서비스 계정 부록)

**사전 확인**: 사용자에게 "분석할 GA4 속성에 본인 계정으로 admin/editor/viewer 권한 있으세요? (Ads Manager 같은 GA4 메뉴 들어가지세요?)" 질문.
- ✅ Yes → 디폴트 OAuth ADC 트랙 진행 (아래 1~7 단계)
- ❌ No (다른 사람이 admin) → GA4 admin 에게 본인 계정 권한 추가 요청부터 (스킬 일시 중단)

1. **2.1 pipx + gcloud CLI 설치** — `brew install pipx && pipx ensurepath` + `brew install --cask google-cloud-sdk` → `gcloud --version` 확인. 둘 다 새 터미널에서 PATH 적용 필요
2. **2.2 GCP 프로젝트 생성** — [console.cloud.google.com](https://console.cloud.google.com/) → 새 프로젝트 → 이름 `ga4-{브랜드}` → 프로젝트 ID 메모
3. **2.3 API 활성화** — Analytics Admin API + Analytics Data API 두 개 모두 "사용 설정"
4. **2.4 OAuth 동의 화면 + Desktop Client 발급** — API 및 서비스 → OAuth 동의 화면 → User Type **외부** → 앱 이름 `claudecode-analytics` → **테스트 사용자 단계에서 본인 구글 이메일 추가 (★ 빼먹으면 로그인 차단)** → 저장. 이어서 사용자 인증 정보 → + 만들기 → OAuth 클라이언트 ID → 유형 **데스크톱 앱** → 이름 `claudecode-analytics-desktop` → 만들기 → JSON 다운로드 → `09_tracking/oauth-client.json` 으로 이동 → **`chmod 600`** + **`.gitignore` 등록 확인** (★ 의무)
5. **2.5 ADC 로그인** — `gcloud auth application-default login --client-id-file=/Users/hyeongtaekim/Desktop/Claudecode_MarketingOS_student/09_tracking/oauth-client.json --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform` → 브라우저에서 본인 계정 선택 → "고급" → "안전하지 않은 페이지로 이동" → 동의. 이어서 `gcloud auth application-default set-quota-project <PROJECT_ID>` 로 § 2.2 프로젝트 ID 지정
6. **2.6 .mcp.json 등록 (★ `GOOGLE_APPLICATION_CREDENTIALS` 절대 추가 ❌)** — 워크스페이스 루트 `.mcp.json` 의 `analytics-mcp` env 에 **`GOOGLE_PROJECT_ID` 만** 채움 (§ 2.2 의 프로젝트 ID). **`GOOGLE_APPLICATION_CREDENTIALS` 키가 있으면 서비스 계정 모드 우선 적용되어 ADC 가 무시됨 — OAuth ADC 트랙은 env 에 `GOOGLE_PROJECT_ID` 만 있어야 함**
7. **2.7 검증** — Claude Code 완전 종료 후 재시작 → "내 GA4 속성 목록" 자연어 쿼리 → 본인 계정 권한 가진 모든 GA4 속성 표로 응답되면 정상
8. **(부록) 2.8 서비스 계정 트랙** — cron 무인 운영 (`/10-daily-slack` 등) 또는 자산 격리 필요 시만. 가이드 § 9 부록 A 의 흐름: 서비스 계정 생성 + JSON 키 → `09_tracking/ga4-credentials.json` + chmod 600 → GA4 속성 액세스 관리에서 서비스 계정 이메일 Viewer 권한 부여 (★ 핵심) → `.mcp.json` 에 `GOOGLE_APPLICATION_CREDENTIALS` 추가. **GA4 UI 가 서비스 계정 이메일 거부 시 ("이메일이 Google 계정과 일치하지 않습니다") OAuth ADC 트랙으로 복귀**

> **OAuth 트랙 우월점 — GA4 UI 우회**: 서비스 계정 트랙은 GA4 UI 의 사용자 추가 단계에서 거부 (Workspace 조직 정책·다계정 환경) 가 간헐 발생. OAuth ADC 는 본인 계정 = 이미 GA4 admin 이라 이 단계 자체가 없음 → 가장 안정적

> **두 트랙 공존**: `.mcp.json` 에 `GOOGLE_APPLICATION_CREDENTIALS` 가 있으면 서비스 계정 모드, 없으면 OAuth ADC 모드. 모드 전환 시 Claude Code 재시작 필요

> **노출 사고**: (OAuth) `oauth-client.json` 노출 시 → GCP Console → 사용자 인증 정보 → OAuth 클라이언트 삭제 → `gcloud auth application-default revoke` → § 2.4 재발급 + § 2.5 재로그인. (서비스 계정) `ga4-credentials.json` 노출 시 → GCP Console → 서비스 계정 → 키 탭 → 노출된 키 삭제 → 새 키 발급 → 파일 교체 → `chmod 600` → git 히스토리 점검

### Step 3 — Clarity

SETUP_GUIDE.md 섹션 3 진행:

1. **3.1 프로젝트 확인** — clarity.microsoft.com 로그인 + 데이터 수집 중인 프로젝트 보유 확인
2. **3.2 토큰 발급** — 발급 즉시 안전한 곳에 저장하라고 강조 (한 번만 표시됨)
3. **3.3 Project ID** — URL에서 추출하는 법 안내, 사용자가 ID 알려주면 메모
4. **3.4 .mcp.json 등록 (공식 패키지)** — 본 OS 는 **공식 npm 패키지 `@microsoft/clarity-mcp-server`** 를 사용. `npx -y` 로 실행되므로 별도 빌드 단계 없음. `.mcp.json` 의 기존 `clarity` 항목 env 두 값(`CLARITY_API_TOKEN`, `CLARITY_PROJECT_ID`) 을 실제 값으로 교체.
5. **3.5 검증** — Claude Code 재시작 후 "Clarity 어제 rage click" 쿼리

> **API 한도 주의**: Clarity Data Export API 는 프로젝트당 일 10회. 한 질문이 1회 차감되며, 시행착오도 합산. 시연 직전엔 한도 남아 있는지 확인하라고 미리 알려주기.

### Step 4 — Meta (User Access Token, 디폴트)

[09_tracking/MetaAds_연결_가이드.md](../../../09_tracking/MetaAds_연결_가이드.md) 를 따라 진행. Meta 는 **User Access Token 단일 트랙** — 5분 발급, BM Admin 권한 불필요, 60일 long-lived, `ads_read` 단일 스코프.

**Meta 권한 보안 모델** (사용자에게 처음 1회 안내):
- **권한 정밀 통제** — `ads_read` 단일 스코프 (read-only). `ads_management`·`business_management` 등 쓰기 권한 부여 ❌
- **토큰 저장** — `09_tracking/.env` 의 환경변수 (chmod 600 + .gitignore 의무)
- **명령 실행 범위** — Python 스크립트만 (코드 리뷰 가능, Bash 도구로 사용자 사전 검토)
- **계정 격리** — `.env` 의 `META_AD_ACCOUNT_ID` 한 값으로 Python 스크립트가 1계정만 호출

> 다른 접근 방식 (MCP / CLI / System User Token) 은 가이드 부록의 **트랙 보안 복잡도 비교표** 만 참고. 본 OS 디폴트·강의 시연 모두 User Token 단일.

#### User Token 4단계

1. **4.1 Developer App 생성** — [Meta for Developers](https://developers.facebook.com/) → My Apps → Create App → 5단계 위저드. ① 앱 이름 `Claude Code Ads OS` ② **이용 사례 = 마케팅 API 로 광고 만들기 및 관리** ★ (Marketing API 자동 활성화) ③ 비즈니스 = 본인 BM ④ ⑤ 확인. 좌측 메뉴 가장 하단 **앱 설정 → 기본 설정** 에서 `App ID` + `App Secret` (Show 클릭) 복사
2. **4.2 콘솔 안 토큰 발급 화면 진입 + 권한 선택** — 앱 콘솔 → 좌측 메뉴 **이용 사례** → **광고 만들기 및 관리** → **맞춤 설정** → 우측 사이드바 **도구** → **액세스 토큰 받기** → **`ads_read` 만 체크** ★ (`ads_management`·`business_management`·`pages_*` 모두 ❌). `public_profile` 자동 포함은 무해
3. **4.3 토큰 발급** — **토큰 받기 (Get Token)** → Facebook 로그인 → 토큰 화면에 토큰 표시 → 즉시 복사 → `.env` 의 `META_ACCESS_TOKEN`. **콘솔 경로는 보통 처음부터 long-lived 토큰 (~60일) 발급**
4. **4.4 광고 계정 ID 확인 + .env 작성 + 권한** — Ads Manager URL 의 `?act=XXXXXXXXXXXXXXX` 16자리 → **`act_` 접두사** 붙여 저장. `09_tracking/.env.example` → `.env` 복사 → 4개 값 (`META_APP_ID` · `META_APP_SECRET` · `META_ACCESS_TOKEN` · `META_AD_ACCOUNT_ID`) 채움 → **`chmod 600 /Users/hyeongtaekim/Desktop/Claudecode_MarketingOS_student/09_tracking/.env`** + `grep "09_tracking/.env" .gitignore` 확인

#### 검증 + Claude Code 사용

5. **4.5 Claude Code 자연어 쿼리 검증** — 세션에서 "메타 광고 어제 광고비·ROAS 정리해줘" → Claude 가 `_shared/scripts/lib/meta_client.py` 헬퍼를 import 한 Python 스크립트를 Bash 로 실행 → 표 응답 (스크립트 코드가 출력되므로 사용자 사전 검토 가능)

> **60일 토큰 만료**: `OAuthException: (#190) The access token has expired` 발생 시 — [Access Token Debugger](https://developers.facebook.com/tools/debug/accesstoken/) → 만료 전이면 **Extend Access Token**, 만료 후면 § 4.2 재발급 → `.env` 의 `META_ACCESS_TOKEN` 교체

> **토큰 노출 사고 처리**: developers.facebook.com → 앱 → **App Secret 재설정** (모든 토큰 즉시 무효) + Facebook 비밀번호 변경 → § 4.2 재발급 → `.env` 갱신 → git 히스토리 점검 (`git filter-repo` 또는 새 레포)

### Step 5 — 통합 검증

SETUP_GUIDE.md 섹션 5 체크리스트를 그대로 사용자에게 보여주고 하나씩 체크. 마지막에 시연 쿼리 3개를 차례로 실행시켜 3개 소스 모두 살아있음을 확인:

- GA4: "내 GA4 속성 목록" / "지난 7일 채널별 세션"
- Clarity: "어제 rage click TOP 5 페이지"
- Meta: "메타 어제 광고비와 ROAS" (메모리 정책: ROAS 는 Meta 단독 계산, GA4·Meta 결합 ❌. Claude 가 Bash 도구로 Python SDK 스크립트 호출하는지 호출 로그로 확인 — `_shared/scripts/lib/meta_client.py` 헬퍼 import 패턴이 정석)

성공하면 본 OS 의 분석 스킬들(01~03) 과 콘텐츠 생성 스킬들(05·07·08) 의 인풋이 데이터로 보강된 상태가 된다.

## 에러 핸들링

사용자가 에러를 알리면:

1. **에러 메시지 복사** 받기 (스크린샷 ok, 텍스트 우선)
2. **SETUP_GUIDE.md 섹션 6** 을 `Read` 로 읽고 GA4 / Clarity / Meta 중 어느 도메인인지 판단 후 해당 서브섹션에서 패턴 매칭
3. **매칭되면**: 가이드의 해결책 그대로 안내. "가이드의 X 섹션과 동일한 케이스" 명시.
4. **매칭 안 되면**: WebSearch / Perplexity 로 검색하되, 해결되면 SETUP_GUIDE.md 에 케이스 추가하자고 사용자에게 제안.

## 상태 추적

긴 셋업이라 중간에 끊어질 수 있다. `TaskCreate` 로 다음과 같이 태스크를 만들어 진행 상황 추적:

- "사전 준비 검증"
- "GA4 — 본인 계정에 분석 대상 GA4 admin/editor/viewer 권한 있는지 확인"
- "GA4 — pipx + gcloud CLI 설치"
- "GA4 — GCP 프로젝트 생성 + Analytics API 2개 활성화"
- "GA4 — OAuth 동의 화면 + 테스트 사용자 추가 + Desktop OAuth Client JSON 다운로드 → 09_tracking/oauth-client.json + chmod 600 + .gitignore"
- "GA4 — gcloud auth application-default login → 브라우저 OAuth 동의 → set-quota-project"
- "GA4 — .mcp.json env 등록 (GOOGLE_PROJECT_ID 만, GOOGLE_APPLICATION_CREDENTIALS 절대 추가 ❌) + 검증"
- "(부록, cron 무인 운영·자산 격리 필요 시만) GA4 — 서비스 계정 트랙 (가이드 § 9 부록 A)"
- "Clarity — 토큰 발급"
- "Clarity — .mcp.json 등록 + 검증"
- "Meta — Developer App 생성 (App ID·App Secret + 이용 사례에서 Marketing API 자동 활성화)"
- "Meta — 콘솔 안 토큰 발급 화면에서 User Token 발급 (ads_read 단일)"
- "Meta — 광고 계정 ID 확인 (act_ 접두사) + .env 4개 변수 작성 + chmod 600 + .gitignore"
- "Meta — Claude Code 자연어 쿼리 검증"
- "통합 검증 (시연 쿼리 3개)"

각 단계 완료 시 `TaskUpdate` 로 마킹. 사용자가 "어디까지 했지?" 물으면 `TaskList` 보여주기.

## 산출물

이 스킬은 **새 파일을 만들지 않는다**. 결과물은:

**GA4** (OAuth ADC 트랙, 디폴트):
1. `Claudecode_MarketingOS_student/.mcp.json` 의 `analytics-mcp` env 에 **`GOOGLE_PROJECT_ID` 만** 채움 (★ `GOOGLE_APPLICATION_CREDENTIALS` 절대 추가 ❌ — 있으면 서비스 계정 모드 우선되어 ADC 무시됨)
2. `Claudecode_MarketingOS_student/09_tracking/oauth-client.json` Desktop OAuth Client (chmod 600, .gitignore 등록)
3. `~/.config/gcloud/application_default_credentials.json` ADC 토큰 (`gcloud auth application-default login` 이 자동 저장)
4. `gcloud auth application-default set-quota-project <PROJECT_ID>` 로 쿼터 프로젝트 지정 완료

**Clarity**:
5. `.mcp.json` 의 `clarity` env 의 `CLARITY_API_TOKEN` + `CLARITY_PROJECT_ID`

**Meta — User Token 트랙 (디폴트)**:
6. Meta Developer App 생성 완료 (App ID · App Secret · 이용 사례에서 Marketing API 자동 활성화)
7. 콘솔 안 토큰 발급 화면에서 User Access Token 발급 완료 (`ads_read` 단일 스코프, ~60일 long-lived)
8. `Claudecode_MarketingOS_student/09_tracking/.env` 에 Meta 환경변수 4개 (`META_APP_ID`·`META_APP_SECRET`·`META_ACCESS_TOKEN`·`META_AD_ACCOUNT_ID`) + chmod 600 + .gitignore
9. Python SDK 설치 완료 (`pip3 install facebook-business python-dotenv pyyaml requests`)

**부록 (필요 시만)**:
10. (GA4 서비스 계정 트랙, cron 무인 운영·자산 격리 필요 시만) `09_tracking/ga4-credentials.json` 서비스 계정 키 + chmod 600 + .gitignore + GA4 속성 액세스 관리에서 서비스 계정 이메일 Viewer 권한 부여 + `.mcp.json` env 에 `GOOGLE_APPLICATION_CREDENTIALS` 추가

산출물이 모두 들어간 상태에서 **클로드 코드 재시작 후 GA4·Clarity 자연어 쿼리 + Meta SDK Python 스크립트 호출이 동작**하면 셋업 완료. GA4 OAuth 토큰은 수개월 후 만료 시 `gcloud auth application-default login` 재실행, Meta 토큰은 60일마다 Access Token Debugger 에서 Extend.

## 다음 스킬과의 연결

이 스킬이 끝나면 본 OS 의 분석·콘텐츠 생성 스킬에서 실데이터를 활용할 수 있다. 또한 06 번 리포트 스킬(구축 예정)이 본 셋업을 전제로 한다. 사용자에게:

> 3개 소스 연결 끝났습니다. 이제 01~03 분석 스킬에서 실데이터 인용이 가능하고, 06 리포트 스킬(구축 예정)이 활성화되면 일일·주간 리포트 자동화로 이어집니다.

라고 안내.

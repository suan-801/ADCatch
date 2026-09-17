# 09_tracking — 데이터 트래킹 연결 가이드북

> **목적**: 이 워크스페이스(`Claudecode_MarketingOS_student`)를 새 PC·새 계정에서 다시 셋업할 때, 또는 다른 클라이언트 환경에 그대로 옮길 때 막힘없이 따라할 수 있게 만든 **실전 연결 가이드 3종 세트**.
>
> **기준 환경**: macOS 12+ / zsh / Node 18+ / Python 3.10+ / Claude Code CLI 설치 완료
> **기준일**: 2026-05-27 (보안 우선 트랙으로 전면 개편)

---

## 📚 3종 가이드 인덱스

| # | 가이드 | 디폴트 인증 방식 | 평균 소요 |
|---|---|---|---|
| 1 | [**GA4 연결 가이드**](./GA4_연결_가이드.md) | 서비스 계정 (read-only, 속성마다 명시적 권한) | 15~20분 |
| 2 | [**Clarity 연결 가이드**](./Clarity_연결_가이드.md) | API 토큰 (단일 프로젝트) | 5분 |
| 3 | [**Meta Ads 연결 가이드**](./MetaAds_연결_가이드.md) | Developer App + System User Token (`ads_read` only, 만료 없음) | 30~45분 |

3개를 모두 연결하면 클로드코드에서 **자연어로** "어제 메타 광고비랑 GA4 전환 비교해줘", "Clarity rage click 많은 페이지 뽑아줘" 같은 질의가 즉시 동작합니다.

---

## 🛡 본 OS 의 인증 정책 — 보안 우선

GA4·Meta 두 트랙 모두 **광범위한 OAuth 위임 대신, 명시적으로 자산·권한이 통제된 자격증명** 을 디폴트로 사용합니다. 1인 마케터·에이전시·클라이언트 광고 자산 분석 환경에서 OAuth 광범위 스코프는 사고 위험이 큽니다.

| 측면 | 디폴트 (옵션 A) | 부록 (옵션 B) |
|---|---|---|
| **GA4** | 서비스 계정 — 분석 대상 속성에만 Viewer 권한 명시 부여 | OAuth + gcloud ADC — 본인 구글 계정의 모든 GA4 위임 (BM 권한·다계정 접근 편의용) |
| **Meta** | Developer App + System User Token — `ads_read` only, 특정 광고 계정만 자산 할당, 만료 Never | Meta Ads CLI (OAuth) — BM 권한 없는 1인 운영자·일회성 탐색용 |
| **Clarity** | API 토큰 — 단일 프로젝트 한정 | (해당 없음, 토큰 방식만 지원) |

**디폴트 트랙의 공통 보안 우월점**:
- 자격증명이 워크스페이스 안 한 파일에 명시 (`09_tracking/ga4-credentials.json`, `09_tracking/.env`) → `.gitignore` 로 통제 가능
- 권한이 사전 정의된 범위로 명시 제한 → 토큰 유출 사고 시 영향 범위 통제됨
- 만료 없음 → cron 무인 운영에 안정
- revoke 1클릭 (GA4 속성 액세스 관리 / Meta BM)

---

## 🗂 폴더 안에 뭐가 있나

```
09_tracking/
├── README.md                    ← 이 파일 (인덱스)
├── GA4_연결_가이드.md            ← 옵션 A: 서비스 계정 (디폴트) / 옵션 B: OAuth ADC (부록)
├── Clarity_연결_가이드.md
├── MetaAds_연결_가이드.md        ← 옵션 A: SDK + System User Token (디폴트) / 옵션 B: CLI OAuth (부록)
│
├── .env.example                 ← 환경변수 템플릿 (커밋 가능)
├── .env                         ← Meta SDK 4개 변수 (★ 시크릿, .gitignore 필수)
│
├── ga4-credentials.json         ← GA4 서비스 계정 키 (★ 시크릿, .gitignore 필수)
├── oauth-client.json            ← (부록 § 9) GA4 OAuth Desktop Client — 옵션 B 트랙용
└── adc-login.sh                 ← (부록 § 9) gcloud ADC 재로그인 헬퍼 — 옵션 B 트랙용
```

> ⚠️ **절대 git 커밋 금지**: `.env` · `ga4-credentials.json` · `oauth-client.json`. 워크스페이스 루트 `.gitignore` 에 등록 확인 (`grep "09_tracking" .gitignore`).

---

## ✅ 셋업 완료 검증 한 번에 (3개 동시)

3개 가이드를 다 끝낸 뒤, Claude Code 세션에서 다음을 그대로 던져보세요:

```
GA4 실시간 활성 사용자, Clarity 어제 세션 수, Meta 어제 광고비를 한 번에 정리해줘
```

세 줄짜리 표가 정상 응답으로 오면 셋업 성공. 하나라도 에러가 나면 해당 가이드의 § 트러블슈팅 으로 갑니다.

---

## 🔁 새 PC·새 클라이언트 환경 이전 체크리스트

1. 본 워크스페이스 폴더를 통째로 새 위치에 복사 (단, **`.env` / `ga4-credentials.json` 은 별도 안전 채널 전달** — Slack DM · 1Password 등, Git ❌)
2. `cd <새 경로>/Claudecode_MarketingOS_student`
3. [GA4 연결 가이드](./GA4_연결_가이드.md) § 6 의 `.mcp.json` 의 `GOOGLE_APPLICATION_CREDENTIALS` 절대경로를 새 환경에 맞게 갱신 (홈 디렉토리·사용자명 변경 반영)
4. [Clarity 연결 가이드](./Clarity_연결_가이드.md) § 2 토큰 유효성 확인
5. [Meta Ads 연결 가이드](./MetaAds_연결_가이드.md) § 11 의 1줄 Python 검증 스크립트 실행 → 어제 광고비 출력 확인
6. Claude Code 새로 실행 → `/mcp` 로 `analytics-mcp`·`clarity` 2개 서버 status `connected` 확인. Meta 는 SDK 트랙이라 `/mcp` 에는 안 나타남 — 자연어 쿼리 ("메타 어제 ROAS") 로 검증

---

## 📞 문제 생기면

각 가이드 마지막의 **§ 트러블슈팅** 표가 1차 처방. 그래도 안 풀리면 워크스페이스 루트의 `SETUP_GUIDE.md` (강의 원본) 가 풀스펙 참조 문서입니다.

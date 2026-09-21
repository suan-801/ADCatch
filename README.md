# ADCatcher (애드캐처)

Project 안에 등록한 브랜드들의 Meta Ad Library 라이브 소재를 매일 자동 수집해 신규/종료 감지, 생존 기간,
비주얼 패턴 분석 등 **Fact 기반 데이터**를 제공하는 광고 소재 인텔리전스 웹 서비스. 자세한 제품 요구사항은
[`PRD.MD`](./PRD.MD), 핵심 데이터 개념(Baseline/이벤트/수집 상태 등)은 [`docs/DATA_SEMANTICS.md`](./docs/DATA_SEMANTICS.md) 참고.

## 폴더 구조

```
ADCatch/
├── PRD.MD                 ← 제품 요구사항 (기준 문서)
├── .cursorrules           ← 디자인/개발 규칙 (Cursor AI 용)
├── apps/
│   ├── web/                ← 프론트엔드 (Next.js + Tailwind)
│   └── api/                ← 백엔드 (FastAPI + PostgreSQL)
├── docs/
│   └── mascot-style-reference.jpg   ← 마스코트 말풍선 연출 참고 이미지 (UI 톤은 참고 대상 아님)
└── reference/              ← 참고 전용 자료 (앱 코드가 import하지 않음, reference/README.md 참고)
    ├── marketing-os-course/    ← 광고 수집 코드 패턴을 가져온 원본 강의 워크스페이스
    └── adetect-reference/      ← 채택하지 않은 "ADetect" 컨셉 자료 (교차 참고용)
```

## 로컬 실행

### 1. 백엔드 (FastAPI)

```bash
cd apps/api
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # 값 채우기 (아래 "필요한 자격증명" 참고)
uvicorn app.main:app --reload
```

`http://localhost:8000/docs` 에서 Swagger UI로 API를 바로 테스트할 수 있습니다.

### 2. 프론트엔드 (Next.js)

```bash
cd apps/web
npm install
cp .env.example .env.local
npm run dev
```

`http://localhost:3000` 에서 대시보드 확인.

## 필요한 자격증명 (`apps/api/.env`)

| 변수 | 용도 | 발급처 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 연결 | Supabase 프로젝트 생성 후 Connection string |
| `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` | 썸네일 캐싱 Storage | Supabase 프로젝트 → API 설정 |
| `APIFY_TOKEN` | Meta Ad Library 수집 | https://console.apify.com/settings/integrations |
| `GEMINI_API_KEY` | 비주얼 태깅 (Vision AI) | https://aistudio.google.com/apikey |
| `TEAMS_WEBHOOK_URL` | 일일 수집 결과 알림 | Teams 채널 → 커넥터 → Incoming Webhook |

자격증명이 없어도 백엔드는 기동되고 프로젝트/경쟁사 등록까지는 가능합니다. 실제 수집(`/collect`)은 `APIFY_TOKEN`이 있어야 동작합니다.

## Viewer / Admin 권한

사이트 기본 방문자는 **Viewer**(읽기 전용)입니다. 우상단 자물쇠(🔒) 아이콘으로 관리자 비밀번호를 입력하면
**Admin**으로 전환되어 프로젝트/브랜드 생성·삭제, 자동 수집 설정, "지금 수집 실행" 등 데이터를 변경하거나
Apify/Gemini 비용이 발생하는 기능을 쓸 수 있습니다. 사용자 계정 시스템이 아니라 "공용 Viewer + 공용 Admin
비밀번호" 구조이며, Admin 세션은 8시간(기본값) 후 만료됩니다.

`apps/api/.env`에 아래 값을 설정해야 Admin 로그인이 활성화됩니다 (비어 있으면 누구도 Admin이 될 수 없는
안전한 기본값):

```bash
# 원본 비밀번호는 절대 .env에 넣지 않는다 — bcrypt hash만 저장
cd apps/api && python -m scripts.hash_admin_password
# → 출력된 hash를 ADMIN_PASSWORD_HASH에 붙여넣기

python -c "import secrets; print(secrets.token_hex(32))"
# → 출력된 값을 ADMIN_SESSION_SECRET에 붙여넣기
```

Vercel 등으로 프론트엔드/백엔드를 **서로 다른 도메인**에 배포하는 경우:
- `ADMIN_PASSWORD_HASH` / `ADMIN_SESSION_SECRET`는 반드시 백엔드 호스팅의 **Server Environment
  Variables**에 넣습니다 (Vercel의 `NEXT_PUBLIC_*`에는 절대 넣지 않습니다 — 클라이언트 번들에 그대로
  노출됩니다).
- `ADMIN_COOKIE_SAMESITE=none`, `ADMIN_COOKIE_SECURE=true`로 바꿔야 크로스 도메인 쿠키가 정상 전송됩니다.
- `CORS_ALLOWED_ORIGINS`에 프론트엔드의 정확한 origin(예: `https://your-app.vercel.app`)을 등록해야 합니다.

## 데이터 수집 방식

Meta Ad Library 스크래핑은 Apify의 `curious_coder/facebook-ads-library-scraper` 액터를 사용합니다
(`apps/api/app/services/ad_library_collector.py`). 이 호출 패턴은 `reference/marketing-os-course/`에서
검증된 코드를 이식한 것이며, 신규/종료(NEW/ACTIVE/INACTIVE) 상태 추적 로직은 ADCatcher에서 새로 구현했습니다
(`apps/api/app/services/ad_sync.py`).

## 스케줄러

Celery/Redis 대신 `apps/api/scripts/run_daily_collection.py` 스크립트를 매일 1회 실행하는 방식을
기본값으로 채택했습니다. `.github/workflows/daily-collect.yml`에 GitHub Actions cron 예시가 있습니다
(GitHub repo secrets에 위 자격증명을 등록하면 바로 동작). 이 스크립트는 마지막 단계로 Gemini
PENDING 재분석 배치도 함께 실행합니다.

## Gemini PENDING 재분석 수동 실행

신규 소재의 Gemini 비전 분석이 quota/일시 오류로 `PENDING`에 머무는 경우, Daily Scheduler를
기다리지 않고 즉시 재시도하고 싶다면:

```bash
cd apps/api
python -m scripts.process_pending_analysis            # 기본 배치 크기(GEMINI_PENDING_BATCH_SIZE)만큼 처리
python -m scripts.process_pending_analysis --limit 50  # 이번 실행만 50건으로 제한
```

배치 크기/재시도 임계값은 `apps/api/app/config.py`의 `gemini_pending_batch_size` /
`gemini_analysis_max_retries`(환경변수로도 override 가능)로 조정합니다. 자세한 lifecycle은
[`docs/DATA_SEMANTICS.md`](./docs/DATA_SEMANTICS.md) §8 참고.

## DB 스키마 변경 시 주의

`apps/api/app/main.py`는 기동 시 `Base.metadata.create_all()`을 실행하지만, 이는 **존재하지 않는
테이블만 생성**하며 이미 존재하는 테이블에 새 column을 추가해주지 않습니다. 이미 배포된(Supabase 등)
DB에 스키마 변경을 반영하려면 `apps/api/db/migrations/`의 additive migration을 직접 실행하세요:

```bash
psql "$DATABASE_URL" -f apps/api/db/migrations/001_product_stabilization.sql
```

신규 마이그레이션을 추가할 때도 `ADD COLUMN IF NOT EXISTS` 등 기존 데이터를 보존하는 additive 방식만
사용하고, `apps/api/db/schema.sql`(신규 DB 기준 최신 스키마)도 함께 갱신하세요.

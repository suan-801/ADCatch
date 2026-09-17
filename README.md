# AdCatch (애드캐치)

경쟁사의 Meta Ad Library 라이브 소재를 매일 자동 수집해 신규/종료 감지, 생존 기간, 비주얼 패턴 분석 등
**Fact 기반 데이터**를 제공하는 경쟁사 인텔리전스 웹 서비스. 자세한 제품 요구사항은 [`PRD.MD`](./PRD.MD) 참고.

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

## 데이터 수집 방식

Meta Ad Library 스크래핑은 Apify의 `curious_coder/facebook-ads-library-scraper` 액터를 사용합니다
(`apps/api/app/services/ad_library_collector.py`). 이 호출 패턴은 `reference/marketing-os-course/`에서
검증된 코드를 이식한 것이며, 신규/종료(NEW/ACTIVE/INACTIVE) 상태 추적 로직은 AdCatch에서 새로 구현했습니다
(`apps/api/app/services/ad_sync.py`).

## 스케줄러

Celery/Redis 대신 `apps/api/scripts/run_daily_collection.py` 스크립트를 매일 1회 실행하는 방식을
기본값으로 채택했습니다. `.github/workflows/daily-collect.yml`에 GitHub Actions cron 예시가 있습니다
(GitHub repo secrets에 위 자격증명을 등록하면 바로 동작).

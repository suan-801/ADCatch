# PRD.md: 광고 소재 트래커 (ADCatcher)

> 핵심 데이터 개념(Brand/Baseline/이벤트/수집 상태 등)의 상세 정의는
> [`docs/DATA_SEMANTICS.md`](./docs/DATA_SEMANTICS.md)를 기준 문서로 삼는다. 이 PRD와 어긋나면
> `docs/DATA_SEMANTICS.md` 쪽이 더 최신/정확하다.

## 1. 프로젝트 개요
* **프로젝트명:** ADCatcher (애드캐처)
* **한 줄 설명:** Project 안에 등록한 브랜드들의 Meta Ad Library 라이브 소재를 매일 자동 수집하여 신규/종료 감지, 생존 기간, 비주얼 패턴 분석 등 **Fact 기반 데이터**를 제공하고 업무 프로세스를 안내하는 광고 소재 인텔리전스 웹 서비스
* **프로젝트 유형:** Web Application (MVP: 계정 인증 생략 사내 전용 툴 → 추후 B2B SaaS 확장)
* **개발 난이도:** MVP 기준 ★★★☆☆

---

## 2. 사용자 시나리오 및 페르소나
* **Target User:** 퍼포먼스 마케터, 대행사 AE, 마케팅 전략가
* **주요 사용 시나리오:**
  1. **데일리 모니터링:** 출근 직후 접속하여 프로젝트를 선택하고, 어제 대비 신규 투입(New) 및 집행 중단(Inactive)된 소재 수치와 주요 비주얼 변동을 확인.
  2. **라이브 소재 갤러리 분석:** 현재 집행 중인 브랜드의 라이브 소재를 생존일수 순으로 모아보며, 장기간 유지되는 소재의 Hook 및 비주얼 포맷을 분석하여 신규 소재 기획 아이디어 발상.
  3. **픽셀 비서 안내 활용:** 우측 하단에 상주하는 도트 비서 캐릭터("캐쳐")의 툴팁 안내를 받으며 초기 수집 등록, 필터링, 데이터 익스포트 기능을 손쉽게 활용.

---

## 3. 워크스페이스 및 데이터/운영 정책

### 3.1 프로젝트(워크스페이스) 단위 분리
* **Project = 브랜드 N개:** 관련 광고를 함께 추적하고 싶은 브랜드 N개를 하나의 **'프로젝트(Workspace)'**로 묶어 관리한다. Project 안에 등록되는 모든 대상은 동일한 **"브랜드"**다 — "자사"와 "경쟁사"를 구분하지 않으며, Dashboard/Gallery/Daily Changes/Freshness/자동 수집 모두 모든 브랜드를 동등하게 처리한다(상세: `docs/DATA_SEMANTICS.md` §1).
* **프로젝트 스위처:** 사이드바 드롭다운을 통해 프로젝트를 전환하며, 선택된 프로젝트에 맞춰 대시보드 내 모든 metrics, 갤러리, 수집 스케줄이 동적으로 필터링됨.

### 3.2 MVP 계정 정책 및 14일 자동 수집 중단 (Auto-Pause)
* **계정 인증 미적용 (MVP):** 로그인 시스템을 생략하고 DB 내 `default_admin` 계정을 고정 사용하여 개발 속도를 최우선 확보.
* **접속 기록 추적:** 누군가 웹사이트에 접속하거나 화면을 조작할 때마다 DB 내 `users.last_accessed_at` 필드 자동 갱신.
* **스케줄러 자동 정지:** 
  * 매일 새벽 수집 실행 시 `NOW() - last_accessed_at > 14일` 여부 검증.
  * 14일간 접속 기록이 없으면 해당 프로젝트 상태를 `PAUSED`로 전환하여 크롤링 리소스 절약.
  * 다시 사이트에 접속하는 즉시 `ACTIVE` 상태로 복구되어 다음날 수집 재개.

### 3.3 데이터 보관 및 Pruning
* **Database (PostgreSQL / Supabase):** 광고 ID, 카피, 최초/최종 노출일, 누적 생존일수, 비주얼 태그 보관.
* **Storage (AWS S3 / Cloud Storage):** Meta CDN 링크 만료에 대비해 썸네일 이미지를 사내 클라우드 스토리지에 캐싱.
* **14일 추적 종료 규칙:** `INACTIVE` 전환 후 14일 연속 재노출되지 않는 광고 ID는 수집 대상 스케줄러에서 아카이빙 처리.

---

## 4. 핵심 기능 명세

| 구분 | 기능 명칭 | 상세 설명 |
| :--- | :--- | :--- |
| **수집 엔진** | **Daily Meta Ad Collector** | 매일 정해진 시각 프로젝트별 등록된 Meta Ad Library URL/페이지 ID 기반 광고 데이터 수집 |
| **라이브 관리** | **Active/Inactive & 수명 계산** | 라이브러리 발견 시 `Active`(생존일수 +1), 미발견 시 `Inactive` 처리. 14일 연속 미노출 시 아카이빙 |
| **온보딩** | **Initial Baseline + Daily Catch Opt-in** | 브랜드 등록 후 첫 완전한 성공 수집이 Baseline이 되며(`docs/DATA_SEMANTICS.md` §3), Baseline 완료 시에만 "매일 변화 CATCH하기" opt-in CTA를 노출 |
| **변화 추적** | **Daily Ad Change History** | 날짜 × 브랜드 기준으로 그 날 켠(STARTED/REACTIVATED)/끈(STOPPED) 광고와 비주얼 패턴을 조회 |
| **신뢰도 표시** | **Collection Freshness** | 프로젝트의 브랜드별 최신 수집 상태(정상/부분 수집/실패)를 헤더 근처에서 바로 보여줌 |
| **비주얼 분석** | **Vision AI Tagging** | Gemini Vision API를 이용해 이미지 내 인물 포함 여부, 텍스트 중심 여부, 제품 중심 여부 자동 태깅. 신규 소재는 수집 즉시 1차 분석하고, quota/일시 오류로 `PENDING`으로 남은 소재는 Daily Scheduler 마지막 단계(`process_pending_analysis`)가 별도로 재시도한다 — Gemini 실패는 Core Collection의 성공 여부와 완전히 독립적이다. `SUCCESS`로 확정된 소재는 다시 분석하지 않는다. |
| **대시보드** | **Fact Metrics & 갤러리** | 신규/종료/유지 개수 카드, 비주얼 포맷 비율 차트, 카드형 라이브 광고 갤러리(생존기간 순 정렬) 제공. 갤러리에는 Brand 외에 Status/Format/Visual/카피 검색 필터가 있고, 카드를 클릭하면 Ad Detail Drawer(집행/추적 일수, 변화 이력, Meta 원본 링크 등)가 열린다. |
| **알림** | **Teams Webhook Alert** | 수집 완료 후 Microsoft Teams 채널로 당일 신규(STARTED 기준)/종료 소재 수치 및 최고 장수 소재 요약 알림 전송 |
| **온보딩/안내** | **Pixel Assistant Guide** | 우측 하단 상주 도트 비서 캐릭터("캐쳐")가 의미 있는 순간(온보딩/Baseline 완료/신규 변화/수집 완료·실패)에만 말풍선을 열어 안내 |

---

## 5. UI/UX 및 디자인 가이드

### 5.1 레이아웃 톤앤매너
* **Landing Page**(별도 톤, 이 PRD 작업 범위에서 수정하지 않음): Orange 중심, 큰 3D 캐쳐, 큰 타이포그래피/그래픽, 짧은 브랜드 스토리텔링.
* **Product 화면**(Dashboard/Daily Changes 등): 70% 전문 업무 툴 + 30% ADCatcher personality. White/warm-white 배경, Orange accent, Dark navy 타이포. 광고 소재 이미지를 최우선으로 보여주고 여백/위계를 우선한다. 제네릭 AI 그라데이션, 과도한 둥근 카드, 글래스모피즘은 지양한다.
* **컬러 시스템:**
  * Background: White / Warm White (`#F8FAFC`)
  * Border: Thin 1px Line (`#E2E8F0`)
  * Status Badges: Muted Blue (`New`), Muted Green (`Active`), Muted Gray (`Inactive`)
* **Asset 정책:** 로고/아이콘은 (진짜 vector인 경우에만) SVG, 3D 렌더 캐쳐·아트워크는 WebP/AVIF를 사용한다. 상세 규칙은 `docs/ASSET_GUIDE.md` 참고.
* 상세 규칙은 `.cursorrules` 참고.

### 5.2 픽셀 도트 비서 캐릭터 (캐쳐)
* **비주얼 컨셉:** 16x16 레트로 픽셀 아트 스타일의 캐릭터.
* **위치 & 동작:**
  * 화면 우측 하단 floating 영역 상주.
  * CSS `image-rendering: pixelated;` 속성 적용.
  * 온보딩, 수집 상태, 당일 수집 결과 요약을 말풍선 툴팁(`Bubble Tooltip`)으로 전달.

---

## 6. 기술 스택

* **Frontend:** Next.js (App Router) + Tailwind CSS
* **Backend:** Python (FastAPI)
* **Database:** PostgreSQL / Supabase
* **Object Storage:** AWS S3 or Local Cloud Storage
* **AI Engine:** Google Gemini Vision API (비주얼 태깅)
* **Scheduler:** Celery + Redis 또는 GitHub Actions / Cloud Scheduler
* **Alert:** Microsoft Teams Incoming Webhook

---

## 7. Future / Deployment

현재 MVP의 수집 트리거(`POST /competitors/{id}/ads/collect`)는 **동기(synchronous) HTTP
요청** 하나 안에서 Apify 호출 → DB 동기화 → Storage 캐싱 → Gemini 태깅까지 전부 끝낸다.
로컬/사내 배포 단계에서는 문제가 없지만, serverless/cloud 환경에 배포하면 요청 timeout 위험이
있다. 이번 정리에서는 이 아키텍처를 바꾸지 않았고(job queue/background worker/polling으로의
전환은 범위 밖), 향후 다음 방향으로 전환하는 것을 권장한다:

```
POST /collect
  ↓ collection_run_id를 즉시 반환
  ↓ durable worker(GitHub Actions / Supabase Edge / Queue 등, 배포 시점에 선택)가 실제 수집 실행
  ↓ Frontend는 GET /collection-runs/{id}를 폴링 (RUNNING/SUCCESS/PARTIAL/FAILED)
```

fire-and-forget 백그라운드 스레드에 의존하지 않고, 상태를 항상 DB(`collection_runs`)에서
조회 가능한 형태로 유지하는 것이 핵심이다.

같은 맥락에서, Project 전체 추적 광고 수가 커지면(예: 약 200개 이상) 대규모 추적에 대한
안내/과금 정책이 필요해질 수 있다 — 다만 특정 개수에서 수집을 차단하는 hard limit은 아직
만들지 않는다.
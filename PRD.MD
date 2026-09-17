# PRD.md: 경쟁사 메타 소재 트래커 (AdCatch)

## 1. 프로젝트 개요
* **프로젝트명:** AdCatch (애드캐치)
* **한 줄 설명:** 경쟁사의 Meta Ad Library 라이브 소재를 매일 자동 수집하여 신규/종료 감지, 생존 기간, 비주얼 패턴 분석 등 **Fact 기반 데이터**를 제공하고 업무 프로세스를 안내하는 경쟁사 인텔리전스 웹 서비스
* **프로젝트 유형:** Web Application (MVP: 계정 인증 생략 사내 전용 툴 → 추후 B2B SaaS 확장)
* **개발 난이도:** MVP 기준 ★★★☆☆

---

## 2. 사용자 시나리오 및 페르소나
* **Target User:** 퍼포먼스 마케터, 대행사 AE, 마케팅 전략가
* **주요 사용 시나리오:**
  1. **데일리 모니터링:** 출근 직후 접속하여 프로젝트(브랜드)를 선택하고, 어제 대비 신규 투입(New) 및 집행 중단(Inactive)된 소재 수치와 주요 비주얼 변동을 확인.
  2. **라이브 소재 갤러리 분석:** 현재 집행 중인 경쟁사 라이브 소재를 생존일수 순으로 모아보며, 장기간 유지되는 소재의 Hook 및 비주얼 포맷을 분석하여 신규 소재 기획 아이디어 발상.
  3. **픽셀 비서 안내 활용:** 우측 하단에 상주하는 도트 비서 캐릭터("캐쳐")의 툴팁 안내를 받으며 초기 수집 등록, 필터링, 데이터 익스포트 기능을 손쉽게 활용.

---

## 3. 워크스페이스 및 데이터/운영 정책

### 3.1 프로젝트(워크스페이스) 단위 분리
* **다중 브랜드 구조:** 자사 1곳 + 경쟁사 N곳을 하나의 **'프로젝트(Workspace)'**로 묶어 관리.
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
| **비주얼 분석** | **Vision AI Tagging** | Gemini Vision API를 이용해 이미지 내 인물 포함 여부, 텍스트 중심 여부, 제품 중심 여부 자동 태깅 |
| **대시보드** | **Fact Metrics & 갤러리** | 신규/종료/유지 개수 카드, 비주얼 포맷 비율 차트, 카드형 라이브 광고 갤러리(생존기간 순 정렬) 제공 |
| **알림** | **Teams Webhook Alert** | 수집 완료 후 Microsoft Teams 채널로 당일 신규/종료 소재 수치 및 최고 장수 소재 요약 알림 전송 |
| **온보딩/안내** | **Pixel Assistant Guide** | 우측 하단 상주 도트 비서 캐릭터("캐쳐")가 온보딩, 수집 상태, 주요 비주얼 변동 패치를 툴팁으로 안내 |

---

## 5. UI/UX 및 디자인 가이드

### 5.1 레이아웃 톤앤매너
* **스타일:** Linear / Vercel 스타일의 극도로 깔끔하고 미니멀한 B2B SaaS 대시보드.
* **컬러 시스템:** 
  * Background: Slate White / Muted Gray (`#F8FAFC`, `#0F172A`)
  * Border: Thin 1px Line (`#E2E8F0`)
  * Status Badges: Muted Blue (`New`), Muted Green (`Active`), Muted Gray (`Inactive`)

### 5.2 픽셀 도트 비서 캐릭터 (캐쳐)
* **비주얼 컨셉:** 16x16 레트로 픽셀 아트 스타일의 캐릭터.
* **위치 & 동작:**
  * 화면 우측 하단 floating 영역 상주.
  * CSS `image-rendering: pixelated;` 속성 적용.
  * 온보딩, 수집 상태, 당일 수집 결과 요약을 말풍선 툴팁(`Bubble Tooltip`)으로 전달.

---

## 6. 기술 스택

* **Frontend:** Streamlit (초기 초고속 구축) 또는 Next.js (`shadcn/ui` + Tailwind CSS)
* **Backend:** Python (FastAPI)
* **Database:** PostgreSQL / Supabase
* **Object Storage:** AWS S3 or Local Cloud Storage
* **AI Engine:** Google Gemini Vision API (비주얼 태깅)
* **Scheduler:** Celery + Redis 또는 GitHub Actions / Cloud Scheduler
* **Alert:** Microsoft Teams Incoming Webhook
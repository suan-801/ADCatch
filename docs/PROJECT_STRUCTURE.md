# ADCatcher Repository Structure

새 개발자나 AI coding agent가 "어디를 수정해야 하는지" 빠르게 찾기 위한 지도다. 데이터
의미(Brand/Baseline/이벤트/수집 상태)의 기준 문서는 이 파일이 아니라
[`docs/DATA_SEMANTICS.md`](./DATA_SEMANTICS.md)다.

## apps/web

| 디렉터리 | 역할 |
|---|---|
| `app/` | Next.js App Router 페이지. `app/dashboard/[projectId]/` 아래 현재 현황(`page.tsx`)과 날짜별 변화(`changes/page.tsx`)가 공용 `layout.tsx`(사이드바+헤더)를 공유한다. |
| `components/gallery/` | Live Ad Gallery 전용: `ad-gallery.tsx`(카드 그리드), `gallery-filters.tsx`(Status/Format/Visual/카피 검색), `ad-detail-drawer.tsx`(카드 클릭 시 상세 패널). |
| `components/daily-changes/` | 날짜별 변화 화면 전용 컴포넌트(`changed-ad-card.tsx`, `date-nav.tsx`, `competitor-filter.tsx` 등). |
| `components/landing/` | Landing Page 전용 섹션들 — Product 화면과 톤이 다르다(`.cursorrules` §2 참고). |
| `components/ui/` | `Modal` 등 여러 화면이 공유하는 범용 UI 프리미티브. |
| `components/*.tsx` (루트) | 위 하위 폴더로 아직 옮기지 않은 기존 공용 컴포넌트(`project-sidebar.tsx`, `competitor-panel.tsx`, `mascot-widget.tsx`, `project-create-wizard.tsx` 등). 여기 있는 파일을 옮기려면 import를 전부 갱신해야 하므로, 새 파일만 의미 단위 폴더에 넣고 기존 파일은 강제로 이동시키지 않는다. |
| `lib/api.ts` | 백엔드 REST 호출 wrapper 전부. |
| `lib/types.ts` | 백엔드 `app/schemas.py`와 1:1로 맞춰야 하는 TypeScript 타입 + 날짜/생존일수 계산 유틸. |
| `lib/validation.ts` | 클라이언트 입력 검증(현재: Meta Ad Library URL). |
| `public/` | 아래 **Public Assets** 참고. |

## apps/api

| 디렉터리 | 역할 |
|---|---|
| `app/routers/` | FastAPI 엔드포인트. 파일당 하나의 리소스(`projects.py`, `competitors.py`, `ads.py`, `dashboard.py`, `ad_changes.py`). |
| `app/services/` | 비즈니스 로직. `ad_sync.py`(NEW/ACTIVE/INACTIVE 판정 핵심), `ad_library_collector.py`(Apify 호출), `media.py`/`vision_tagging.py`(썸네일 캐싱+Gemini 태깅), `pending_analysis.py`(PENDING Gemini 재시도, Part A), `collection_history.py`(Daily Ad Change History 조회/기록), `storage.py`(Supabase Storage), `autopause.py`(14일 미접속 정책), `timing.py`(stage별 실행시간 구조화 로그). |
| `app/models.py` | SQLAlchemy ORM 모델. |
| `app/schemas.py` | Pydantic 요청/응답 모델 — `lib/types.ts`와 항상 동기화한다. |
| `app/config.py` | 환경변수 기반 설정(`Settings`). 숫자 상수(재시도 횟수, 배치 크기 등)는 여기서만 관리한다. |
| `db/schema.sql`, `db/migrations/*.sql` | 신규 DB 기준 스키마 + 기존 DB에 적용할 additive migration. 컬럼 추가 시 둘 다 갱신한다(`Base.metadata.create_all()`은 기존 테이블에 컬럼을 추가해주지 않는다). |
| `scripts/` | 수동/스케줄 실행 진입점. `run_daily_collection.py`(Daily Scheduler — cron이 매일 1회 실행), `process_pending_analysis.py`(Gemini PENDING 재시도 수동 실행). |
| `tests/` | pytest. SQLite 인메모리 DB로 도는 유닛테스트(`conftest.py` fixture 참고) — Apify/Gemini 등 외부 네트워크는 항상 mock/직접 함수 호출로 우회한다. |

## public assets

| 폴더 | 용도 |
|---|---|
| `brand/` | 로고. 현재 진짜 vector 소스가 없어 `logo.png`(PNG)를 유지한다 — 유효한 벡터 로고가 생기면 `logo.svg`로 교체한다. |
| `mascot/` | 캐릭터 "캐쳐" 이미지. `catcher-hero.webp`(랜딩/온보딩의 3D 렌더, 큰 사이즈)와 `catcher.png`/`catcher-happy.png`(Product 화면 우측 하단 상주 위젯, 작은 아이콘)는 스타일과 역할이 다르다 — 혼용하지 않는다. |
| `landing/gallery/` | Landing "What it does" 섹션의 명화 재해석 아트워크(WebP). |
| `icons/` | 커스텀 아이콘용(현재 비어있음 — 실제 파일이 생기기 전에는 폴더를 만들지 않는다). |

세부 규칙은 [`ASSET_GUIDE.md`](./ASSET_GUIDE.md) 참고.

## Important files

- [`PRD.MD`](../PRD.MD) — 제품 개요/기능 명세.
- [`docs/DATA_SEMANTICS.md`](./DATA_SEMANTICS.md) — Brand/Baseline/이벤트/수집 상태의 기준 정의.
- [`docs/UX_ONBOARDING.md`](./UX_ONBOARDING.md) — 온보딩 플로우.
- [`docs/ASSET_GUIDE.md`](./ASSET_GUIDE.md) — public asset 형식/네이밍 규칙.
- [`.cursorrules`](../.cursorrules) — AI coding agent용 개발/디자인 규칙.

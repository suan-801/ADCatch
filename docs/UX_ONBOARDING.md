# UX / Onboarding — 2026-09 Update

이 문서는 이번 업데이트(Focused UX / Landing / Project Onboarding)에서 **추가·변경된 것만** 다룬다.
기존 Baseline / Brand / Daily Changes semantics는 [`DATA_SEMANTICS.md`](./DATA_SEMANTICS.md)가
source of truth이며 이 문서는 그 내용을 다시 쓰지 않는다 — 온보딩 위저드가 그 규칙을 어떻게
"그대로 재사용"하는지만 설명한다.

## 1. New Project Onboarding — Brand-first 생성

과거: `Project 생성 → 빈 Dashboard → 화면 하단에서 Brand 추가`.
현재: `apps/web/components/project-create-wizard.tsx`의 `ProjectCreateWizard`가 Project(Step1) →
Brand(Step2, 최소 1개) → Initial Collection(Step3~4)을 하나의 짧은 흐름으로 묶는다.

- Landing(`landing/project-select-section.tsx`)과 Product Sidebar(`project-sidebar.tsx`)의
  "새 프로젝트"는 이 컴포넌트 하나를 공유한다 — 두 위치가 서로 다른 생성 로직을 갖지 않는다.
- 플레이스홀더는 어디서나 "프로젝트명을 입력해주세요" / "브랜드명을 입력해주세요" /
  "Meta Ad Library URL을 입력해주세요"로 통일한다.
- 새 API 계약을 만들지 않는다 — 기존 `POST /projects`, `POST /projects/{id}/competitors`,
  `POST /competitors/{id}/ads/collect`를 그대로 호출한다. Baseline 판정은 전적으로
  `app.services.ad_sync.synchronize_ad_status`(`SyncResult.is_baseline` /
  `snapshot_complete`)에 위임하고, 위저드는 그 결과를 화면에 표시만 한다.
- 브랜드 2개 이상을 동시에 첫 수집할 때는 무제한 `Promise.all`이 아니라 bounded concurrency(기본
  2, `runWithConcurrency` 유틸)로 순회한다 — Apify + enrichment가 이미 무거운 작업이기 때문.
- PARTIAL/FAILED로 끝난 브랜드는 완료 화면 집계(`N개 브랜드에서 M개 저장`)에서 제외되고,
  FAILED는 개별 "다시 시도" 버튼으로 그 브랜드의 첫 수집만 재실행한다.
- 완료 화면의 "매일 변화 CATCH하기" / "나중에" CTA는 `PATCH /projects/{id}
  {auto_collect_enabled}`를 그대로 재사용한다(`baseline-cta.tsx`와 동일한 API, 문구만 다중 브랜드
  집계에 맞게 조정).

기존 프로젝트에 브랜드를 추가하는 흐름(`dashboard/[projectId]/page.tsx`의
`handleCreateCompetitor`)도 브랜드 생성 직후 동일한 첫 수집(`handleCollect`)을 자동으로 트리거하도록
바뀌었다 — 새 로직을 만들지 않고 기존 수동 수집 핸들러를 재사용한다. `CompetitorPanel`(브랜드
등록 UI)의 위치도 페이지 최하단에서 "라이브 소재 갤러리" 바로 위로 옮겼다(§ Part F).

## 2. Project 삭제

- `DELETE /projects/{project_id}` (`app/routers/projects.py::delete_project`) — 소유자 확인 후
  204. 존재하지 않거나 소유자가 아니면 404.
- Cascade: `Competitor`/`Ad`는 기존 ORM relationship(`cascade="all, delete-orphan"`)을 그대로
  쓴다. `CollectionRun`/`AdObservation`/`AdStatusEvent`는 Competitor에 매핑된 relationship이
  없고 DB `ON DELETE CASCADE`도 SQLite 등에서는 보장되지 않으므로, 라우터에서 프로젝트 소속
  `competitor_id` 기준으로 명시적으로 먼저 지운다 — 어떤 DB 백엔드에서도 동일하게 동작한다.
- Supabase Storage 캐시 썸네일은 `app/services/storage.py::cleanup_prefix`가
  best-effort로 정리한다(`{competitor_id}/` 아래 object를 list → 삭제). 실패해도 이미 commit된
  DB 삭제를 되돌리지 않고 로그만 남긴다.
- 프론트: Project Header의 "⋯" 메뉴 → 확인 다이얼로그(destructive, 되돌릴 수 없음 문구) →
  삭제 후 남은 프로젝트가 있으면 그중 하나로, 없으면 Landing(`/`)으로 이동한다.

## 3. Landing — Monitoring Section 비주얼

`components/landing/what-it-does-section.tsx`: 단순 8색 rectangle 대신, 4개의 "저화질 광고
화면" 카드가 각기 다른 delay로 crossfade하고(`tailwind.config.ts`의 `screen-fade` keyframe,
"프리즘" 저화질 표현은 scanline 오버레이로만 구현 — 캐쳐 자체는 Hero와 동일한 clean 3D 유지),
`catcher-monitoring.png`(신규 asset, 3/4 후면 뷰)가 섹션의 약 35~40% 비중으로 화면들을 관찰하는
구도로 배치된다. 애니메이션은 전부 `motion-safe:` prefix로 `prefers-reduced-motion`을 지원한다.
카피는 변경하지 않았다.

## 4. Product Catcher(MascotWidget) 권장 크기

`components/mascot-widget.tsx`: 기존 64×64px 고정 → 모바일 70px / 데스크톱 84px(`sm:` 기준),
은은한 오렌지 ring + 진한 shadow로 주목도를 높였다. 말풍선 default-closed / 의미 있는 순간에만
자동 오픈되는 기존 로직(`openSignal`)은 그대로 두고, 그 signal이 바뀔 때만 캐릭터 이미지에 짧은
pop-in(`motion-safe:animate-pop-in`)을 재생한다 — 상시 애니메이션은 아니다.

## 5. Collection Performance 측정 정책

`app/services/timing.py`의 `stage_timer` 컨텍스트 매니저가 다음 stage들을 `adcatcher.collection_timing`
로거(INFO, `[timing] stage=... ms=... ...`형식)로 남긴다: `apify_actor_start` /
`apify_actor_wait` / `dataset_download` / `raw_ad_parse` (`ad_library_collector.py`),
`enrichment_concurrent_total` / `db_core_sync` / `db_final_commit` (`ad_sync.py`),
`thumbnail_download` / `storage_upload` / `gemini_visual_analysis`(신규 소재 1건당, `media.py`).

이 계측은 **순수 로깅 추가**이며 어떤 collection/baseline/enrichment 로직도 바꾸지 않는다.
최적화는 추측이 아니라 이 로그를 실측한 뒤에만 진행한다(§ 실측 결과는 완료 보고서 참고) — 기존
`media_enrichment_concurrency`(ThreadPoolExecutor 병렬 enrichment)와 `apify_max_ads=500`
(PARTIAL/STOPPED 신뢰도와 직결)은 실측 없이 임의로 줄이지 않는다.

# ADCatcher Data Semantics — Source of Truth

이 문서는 ADCatcher의 핵심 데이터 개념을 정의한다. 사람과 AI coding agent가 동시에 참고하는
기준 문서이며, 코드(backend `app/schemas.py`, `app/services/ad_sync.py`,
`app/services/collection_history.py`, frontend `lib/types.ts`)와 항상 일치해야 한다. 코드와 이
문서가 어긋나면 **코드가 실제로 하는 일을 이 문서에 맞게 고치거나, 이 문서를 코드에 맞게 갱신**한다
— 둘 중 하나가 항상 틀린 상태로 방치되면 안 된다.

## 1. Project / Brand

- **Project**: 관련 광고를 함께 추적하고 싶은 브랜드 N개를 묶은 워크스페이스.
- **Brand**(내부 구현상 테이블/라우트 이름은 하위호환을 위해 `Competitor`/`/competitors`로 남아있음):
  Project 안에 등록된 추적 대상 1개. **"자사" vs "경쟁사" 구분은 없다** — Project 안의 모든 브랜드는
  Dashboard, Live Gallery, Daily Changes, Visual Pattern, Collection Freshness, 자동 수집에서
  동등하게 처리된다.
  - `is_own_brand` column은 과거 자사/경쟁사 구분에 쓰였던 필드로, **deprecated** 상태다. DB에는
    하위호환을 위해 남아있지만 어떤 business logic도 이 값을 참조하지 않는다.
  - 향후 실제로 "우리 브랜드 vs 경쟁사 평균" 같은 비교 기능이 필요해지면, boolean
    `is_own_brand`를 다시 쓰지 않고 generic한 `brand_role`(예: PRIMARY/BENCHMARK/COMPETITOR/CLIENT)
    또는 `tags` 필드를 새로 설계한다.

## 2. Collection Run 상태

한 브랜드에 대한 수집 시도 1회(`collection_runs` 1 row)는 다음 중 하나의 상태를 가진다.

| 상태 | 의미 |
|---|---|
| `RUNNING` | 수집 진행 중 (fetch 시작~완료 사이의 일시적 상태) |
| `SUCCESS` | fetch 성공 + 전체 스냅샷을 신뢰할 수 있음(`max_ads` 상한 미도달) |
| `PARTIAL` | fetch는 성공했지만 `max_ads` 상한에 도달해 전체 스냅샷을 보장할 수 없음 |
| `FAILED` | fetch 자체가 실패(네트워크/Apify 오류 등) |

날짜(프로젝트/브랜드) 단위로 볼 때는 `NO_RECORD`(그 날짜에 수집 시도 자체가 없음)까지 포함해
4가지 상태(`CollectionStatus`)를 쓴다.

**프로젝트 단위 집계 규칙(P0-15)** — 브랜드가 여럿일 때, 상태를 하나로 뭉갤 때는 다음 우선순위를
따른다 (하나라도 SUCCESS라고 전체를 SUCCESS로 표시하지 않는다):

- 모든 브랜드 `SUCCESS` → 프로젝트 `SUCCESS`
- 모든 브랜드 `FAILED` → 프로젝트 `FAILED`
- 모든 브랜드 `NO_RECORD`(기록 없음) → 프로젝트 `NO_RECORD`
- 그 외 모든 혼합(SUCCESS+PARTIAL, SUCCESS+FAILED, SUCCESS+NO_RECORD, PARTIAL+FAILED 등)
  → 프로젝트 `PARTIAL`

API는 이 단일 값(`collection_status`) 외에 브랜드별 분포(`collection_summary: {success, partial,
failed, no_record}`)도 함께 제공해 "일부만 실패"가 감춰지지 않게 한다.

## 3. Baseline

**Baseline은 "이 브랜드의 첫 수집"이 아니라 "이 브랜드의 첫 COMPLETE SUCCESSFUL SNAPSHOT"이다.**

- `Competitor.baseline_completed_at`(TIMESTAMPTZ, NULL 가능)이 이 상태를 명시적으로 저장한다.
  - `NULL` → 아직 baseline이 확정되지 않음("baseline pending"). PARTIAL 수집만 있었거나, 수집
    이력이 아예 없는 상태.
  - `NOT NULL` → baseline이 확정된 시각. 이후부터 정상적으로 STARTED/STOPPED/REACTIVATED가 생성된다.
- baseline이 pending인 동안(=`baseline_completed_at IS NULL`)은:
  - 발견된 소재는 정상적으로 `ads`/`ad_observations`에 저장된다.
  - 이번 수집이 **PARTIAL**이면: 어떤 이벤트도(`BASELINE_DISCOVERED`조차) 생성하지 않는다. 중간
    관측치일 뿐 아직 "확정된 baseline"이 아니기 때문이다.
  - 이번 수집이 **완전한 SUCCESS**면: 이 수집이 baseline이 된다. 새로 발견된 소재는
    `BASELINE_DISCOVERED` 이벤트를 받고, `baseline_completed_at`이 확정 저장된다. 이 순간에는
    STOPPED 판정도 하지 않는다(비교 기준이 될 "직전의 확정 상태"가 아직 없으므로).
- baseline이 확정된 이후의 수집부터 STARTED/STOPPED/REACTIVATED가 정상적으로 생성된다.

예시:

```
Day 1: PARTIAL (500건 제한 도달)
  → 광고 row/observation 저장됨, 이벤트 0건, baseline_completed_at 여전히 NULL

Day 2: 첫 complete SUCCESS
  → 이 스냅샷 전체가 baseline. 새로 발견된 소재는 BASELINE_DISCOVERED.
  → baseline_completed_at 확정 저장.

Day 3부터: 정상적으로 STARTED / STOPPED / REACTIVATED 생성.
```

## 4. Ad 상태 & 이벤트

**상태(`Ad.status`)** — 현재 상태:

| 값 | 의미 |
|---|---|
| `NEW` | baseline 확정 이후 새로 시작된 소재(=이번이 첫 발견) |
| `ACTIVE` | 이번 수집에서도 발견됨(baseline 소재 포함) |
| `INACTIVE` | 이번(완전한) 수집에서 발견되지 않음 |

**이벤트(`AdStatusEvent.event_type`)** — 상태 "전환이 발생한 순간"에만 1건 생성(반복 기록 없음):

| 값 | 의미 |
|---|---|
| `BASELINE_DISCOVERED` | baseline 확정 시점에 함께 발견된 기존 집행 소재. "오늘 켠 광고"가 아니므로 Daily Changes의 켠/끈 카운트·visual pattern에서 제외된다. |
| `STARTED` | baseline 확정 이후 새로 발견된 소재 |
| `STOPPED` | 이전엔 있었는데(완전한 수집 기준) 이번엔 없음 |
| `REACTIVATED` | STOPPED(INACTIVE)였던 소재가 다시 발견됨 |

**중요**: baseline에서 발견된 소재는 `status=ACTIVE` + `event=BASELINE_DISCOVERED`로 생성된다.
`status=NEW`로 생성하지 않는다 — 그렇지 않으면 최초 수집 직후 Gallery가 전부 "NEW" 배지로 도배된다.

## 5. 날짜(생존/집행 일수)의 역사적 불변성

과거 이벤트 카드(예: "9/1 STOPPED 당시 24일")는 나중에 같은 소재가 REACTIVATED되어
`last_seen_at`이 앞으로 밀려도 숫자가 바뀌면 안 된다. `AdStatusEvent.survival_days_at_event`가
이벤트 발생 그 순간의 집행/추적 일수를 snapshot으로 고정 저장한다. 이 컬럼 도입 이전의 과거
이벤트는 `NULL`이며, 이 경우 fake backfill을 하지 않고 프론트가 현재 값 기준 라이브 계산으로
폴백한다.

## 6. 날짜 필드 구분

| 필드 | 의미 |
|---|---|
| `first_seen_at` | ADCatcher가 이 소재를 **처음 관측**한 시각 |
| `last_seen_at` | ADCatcher가 이 소재를 **마지막으로 관측**한 시각 |
| `source_started_at` | Meta 소재 메타데이터상의 **실제 집행 시작일**(모르면 NULL) |

UI 표시 규칙: `source_started_at`이 있으면 "집행 N일"(실제 집행 시작일 기준), 없으면 "추적
N일"(ADCatcher가 처음 관측한 시점 기준) — 둘을 같은 개념처럼 섞어서 보여주지 않는다.

## 7. `auto_collect_enabled` (Baseline + Daily Catch Opt-in)

- `Project.status`(ACTIVE/PAUSED, 14일 미접속 auto-pause와 연동)와
  `Project.auto_collect_enabled`(사용자가 명시적으로 "매일 변화 CATCH하기"에 동의했는지)는
  **서로 다른 개념**이다. 일일 수집 스케줄러는 반드시 `status=ACTIVE AND auto_collect_enabled=true`
  둘 다 확인한다.
- 새 프로젝트의 `auto_collect_enabled` 기본값은 `false`다(기존 프로젝트는 마이그레이션 대상 아님 —
  이 DEFAULT는 신규 INSERT에만 적용된다).
- Baseline CTA는 `SyncResult.is_baseline && SyncResult.snapshot_complete`일 때만 노출한다 —
  실패/부분 수집 결과는 절대 baseline 기준점으로 삼지 않는다.

## 8. `Ad.analysis_status` (Gemini Vision 분석 lifecycle)

| 값 | 의미 |
|---|---|
| `PENDING` | 아직 성공적으로 분석되지 않음 — 신규 소재의 최초 분석 실패(quota 초과 포함) 또는 아직 재시도 대상에 오르지 않은 상태. |
| `SUCCESS` | `visual_type`이 확정됨. **이후 어떤 경로로도 다시 Gemini를 호출하지 않는다**(`app.services.pending_analysis`의 쿼리 자체가 `PENDING`만 대상으로 함). |
| `FAILED` | `gemini_analysis_max_retries`(기본 3회)만큼 재시도했지만 계속 실패 — 더 이상 자동 재시도하지 않는다. |

- Core Collection(수집)과 완전히 분리된 상태다 — 이 값이 무엇이든 `Ad` row 자체의 생성/`status`
  (NEW/ACTIVE/INACTIVE) 판정에는 영향을 주지 않는다(P0-07).
- `analysis_status=PENDING`이어도 Gallery에는 정상 노출된다. 다만 Visual Pattern
  집계(`visual_type_ratio`, Daily Changes의 `visual_pattern`)에는 `visual_type`이 있는
  소재만 포함되므로 자연히 제외된다.
- 재시도는 신규 수집 흐름(`ad_sync.synchronize_ad_status`)이 아니라 별도 배치
  (`app.services.pending_analysis.process_pending_analysis`)가 담당하며, Daily
  Scheduler(`scripts/run_daily_collection.py`)가 매 회차 마지막 단계에서 호출한다. 이 배치가
  실패해도 그 회차의 Core Collection 결과(이미 commit됨)는 되돌리지 않는다.

## 9. Campaign Tag 자동 분류 (2026-09)

프로젝트마다 사용자가 직접 정의하는 캠페인 분류 태그(`campaign_tags` 테이블)와, `Ad`에 저장되는
현재 분류 상태로 구성된다. 시스템에 고정된 캠페인 카테고리는 없다 — 태그명/정의는 전적으로
사용자가 관리한다.

**`Ad.campaign_tag_assignment_source`("누가 지정했는가")와
`Ad.campaign_classification_status`("상태")는 서로 다른 축이다** — `NEEDS_REVIEW`는 상태이지
지정 주체가 아니므로 source enum에 섞지 않는다.

| `assignment_source` | 의미 |
|---|---|
| `NULL` | 아직 아무도 지정하지 않음(초기 상태, 또는 재분류로 리셋된 직후) |
| `AI` | Gemini가 분류를 시도함(성공이든 NEEDS_REVIEW든) |
| `USER` | 사용자가 Drawer에서 직접 지정/수정함 — 항상 AI 값보다 우선하며, 이후 자동 재분류
  배치가 절대 덮어쓰지 않는다(§`reclassify` 참고) |

| `classification_status` | 의미 |
|---|---|
| `PENDING` | 아직 분류 시도가 없거나(신규), 재분류로 리셋된 직후, 또는 다운로드/파싱 실패로
  재시도 대기 중 |
| `SUCCESS` | `campaign_tag_id`가 확정됨(confidence가 임계값 이상) |
| `NEEDS_REVIEW` | Gemini가 응답은 했지만 확신이 낮거나(`campaign_tag_confidence_threshold`
  미달) 태그를 확정하지 못함 — `campaign_tag_id`는 NULL, confidence/reason은 디버깅/화면 표시용으로
  유지 |
| `FAILED` | `campaign_classification_max_retries`(기본 3회)만큼 재시도했지만 계속 실패(이미지
  다운로드/응답 파싱 실패 등) — 더 이상 자동 재시도하지 않는다 |

**사용자가 태그를 수동 지정하면 `campaign_tag_confidence`/`campaign_tag_reason`을 항상 `NULL`로
클리어한다** — "사용자 지정 굿즈 / AI 신뢰도 87%" 같은 모순된 화면을 방지하기 위함.

**Gemini는 프로젝트의 활성(`is_active=true`) 태그 중에서만 선택할 수 있다.** 프롬프트에 각 태그의
`id`/`name`/`definition`을 그대로 넣고, 응답의 `campaign_tag_id`가 그 목록에 없으면(임의로
지어낸 값이거나 이미 비활성화된 태그) 서버가 무조건 버리고 `NEEDS_REVIEW`로 강등한다. 다른
프로젝트의 태그 id가 섞여 들어올 수는 없다(애초에 해당 프로젝트의 태그만 프롬프트에 실림).

**Core Collection과의 격리(P0-07과 동일한 원칙)**: 신규 소재의 캠페인 분류는 비주얼 분석과
완전히 독립된 별도 try/except로 실행된다 — 하나가 실패해도 다른 하나에 영향을 주지 않고, 둘 다
실패해도 `Ad` row 생성 자체는 항상 성공한다. 재시도는 별도 배치
(`app.services.pending_campaign_classification.process_pending_campaign_classification`)가
담당하며, `campaign_classification_status == 'PENDING'`인 소재만 조회한다 — **assignment_source는
전혀 확인하지 않는다.** `USER` 소재는 `classification_status`가 이미 `SUCCESS`로 고정돼 있어
이 쿼리 대상에서 자연히 제외된다.

**재분류(`POST /projects/{project_id}/campaign-tags/reclassify`)**: 태그 정의가 바뀌거나 새
태그가 추가됐을 때, 기존 소재를 새 기준으로 다시 분류하고 싶을 수 있다. 이 엔드포인트는 실제
Gemini 호출을 하지 않고, 대상 `Ad`의 `campaign_tag_id`/`assignment_source`/`confidence`/
`reason`/`retry_count`를 전부 초기화해 `classification_status=PENDING`으로 되돌리기만 한다 —
이후 pending 배치가 처리한다(대량 Gemini 호출이 이 요청 자체를 느리게 만들거나 core collection을
막으면 안 되므로). 기본값(`include_user_assigned=false`)에서는 `USER` 소스 소재가 쿼리에서부터
제외되어 절대 건드리지 않는다. `include_user_assigned=true`를 명시적으로 선택한 경우에만 `USER`
소재도 리셋 대상에 포함된다.

**중요 — 과거 기간 집계에 미치는 영향**: `campaign_tag_id`는 `Ad`에 저장되는 "현재 분류"다.
스냅샷이 아니므로, 소재를 재분류하면 그 소재가 걸린 과거 주차의 Campaign Mix 집계도 함께
바뀐다(새 분류 기준으로 재계산). 이는 의도된 동작이다 — "태그 체계를 고치면 기존 광고도 새 기준으로
재분류"와 일관되게 유지하기 위함. 특정 시점 보고서 숫자를 고정 보존해야 하는 요구가 생기면, 그때
별도의 `AdCampaignTagAssignmentHistory` 테이블(assignment 변경 이력) 도입을 검토한다 — 현재는
범위 밖이다.

## 10. VIDEO/CAROUSEL 미디어 메타데이터 (2026-09, 2026-09-22 재설계)

`Ad.image_url`은 포맷과 무관하게 계속 "대표 썸네일 1장"으로 쓰인다(기존 갤러리 동작 불변).
아래 필드들은 원본 미디어 구조를 additive로 보존해 VIDEO/CAROUSEL 상세 UI에 쓴다.

- `video_url`: **VIDEO 포맷 전용**(HD 우선, SD fallback). CAROUSEL/IMAGE는 항상 NULL — 카드
  내부에 영상이 섞여 있어도(아래 참고) 최상위 `video_url`에는 반영하지 않는다. **이 값은 영구
  캐시가 아니라 Meta의 signed CDN source URL이다** — format이 VIDEO인 동안은 fresh 수집마다
  최신 값으로 refresh된다(아래 backfill/교정 항목 참고). Supabase Storage에 영구 저장되는 것은
  이 URL로부터 추출한 keyframe 이미지뿐, mp4 원본 자체는 저장하지 않는다.
- `media_items`(JSON 배열, `[{type: "image"|"video", url, preview_url}]`): 원본 videos/cards/
  images 구조를 그대로 보존한다. video 항목의 `preview_url`은 `video_preview_image_url →
  original_image_url → resized_image_url` 우선순위로 채워져, 영상 URL은 있는데 poster가 없는
  케이스를 최대한 없앤다. 빈 URL은 담기지 않고 동일 URL은 중복 제거된다.
- `keyframe_urls`/`keyframe_status`/`keyframe_retry_count`/`keyframe_error`: VIDEO 소재의
  캐싱된 Key Visual — `analysis_status`(Gemini Vision)와 동일한 PENDING→SUCCESS/FAILED
  lifecycle을 따르되, **Core Collection의 동기 enrichment 경로에서는 절대 생성되지 않는다.**
  신규 VIDEO 소재는 생성 시 `keyframe_status=PENDING`만 세팅되고, 실제 추출(영상 stream
  다운로드+ffprobe+ffmpeg+Storage 업로드+임시 mp4 삭제)은 완전히 분리된 별도 배치
  (`app.services.pending_video_keyframes.process_pending_video_keyframes`)가 담당한다 — 무거운
  작업을 이미 여러 소재를 동시 처리하는 동기 enrichment 경로에 추가해 수집 자체를 느리게 만들지
  않기 위함이다. **`keyframe_urls`는 정확히 4장(`video_keyframe_count`) 추출+업로드가 모두
  성공해야 `SUCCESS`로 확정된다** — 1~3장만 성공한 경우는 SUCCESS로 취급하지 않고 재시도 가능한
  실패로 남긴다(`keyframe_retry_count` 증가 후 `video_keyframe_max_retries` 초과 시 `FAILED`).
  4개 지점은 8%/35%/65%/92%(마케팅 영상의 Hook·CTA를 포함하도록 배치), 해상도는 원본 그대로가
  아니라 최대 너비 `video_keyframe_max_width`(기본 720px)로 제한한다(비율 유지, upscale 없음 —
  ffmpeg scale filter로 추출 시점에 처리). 원본 mp4는 tempfile에 stream으로만 받고(전체를
  메모리에 올리지 않음, `video_keyframe_max_download_bytes` 상한 초과 시 즉시 중단), 성공/실패와
  무관하게 처리가 끝나면 항상 삭제한다 — Supabase에는 keyframe 이미지만 남는다.

**format 판별 규칙 (2026-09-22 재설계 — raw `display_format`을 우선 evidence로 사용)**:
재현 사례(`ad_archive_id=1411948807546506`)에서 Meta Ad Library는 VIDEO로 보여주는데 ADCatch는
"cards가 2개 이상이면 무조건 CAROUSEL"이라는 구조 전용 규칙 때문에 CAROUSEL로 저장하고 있었다.
이 규칙을 폐기하고 `app.services.ad_library_collector._classify_media()`를 아래 우선순위로
재설계했다:
1. `_raw_display_format()`(item 또는 snapshot의 `display_format`/`displayFormat`, 대소문자
   무시하고 정규화)이 명시적으로 `"VIDEO"`이고 `snapshot.videos[]`/`snapshot.cards[]` 어디에서든
   유효한 video URL을 하나 이상 찾을 수 있으면 → `VIDEO`. 카드가 몇 개든 상관없다 — 바로 이
   케이스가 1411948807546506류(영상 광고를 cards 배열로 감싸 내려주는 경우)다. 유효한 video
   URL을 못 찾으면(메타데이터 불일치) 아래 4번 구조 기반 fallback으로 내려간다.
2. `"DCO"`(Dynamic Creative Optimization)는 CAROUSEL과 동일시하지 않는다 — DCO의 `cards`는
   실제 슬라이드가 아니라 dynamic creative variant일 수 있다. video asset이 있으면 대표
   format=`VIDEO`(첫 유효 video asset을 대표 `video_url`로), 없으면 대표 format=`IMAGE`. 어느
   쪽이든 원본 variant 구조는 `media_items`에 그대로 보존한다.
3. `"CAROUSEL"`/`"MULTI_IMAGES"`/`"DPA"` 중 하나이고 실제로 `cards`가 2개 이상 있으면(=진짜
   여러 장 구조) → `CAROUSEL`로 유지. cards가 2개 미만이면(구조가 claim과 안 맞음) 4번으로.
4. display_format이 없거나 위 어느 값에도 해당하지 않으면(알 수 없는 값 포함) — 기존 구조 기반
   fallback: `snapshot.videos`에 유효 video URL이 있으면 `VIDEO`; `cards`가 정확히 1개이고
   video URL이 있으면 `VIDEO`(Apify가 단일 영상 광고를 카드 1개짜리 배열로 감싸는 케이스); 그 외
   cards가 있으면(2개 이상, 또는 1개인데 영상이 없으면 IMAGE) `CAROUSEL`; `images`만 있으면
   `IMAGE`.

카드/영상 노드의 대표 poster 이미지는 `video_preview_image_url → original_image_url →
resized_image_url` 우선순위로 찾는다(과거에는 카드 poster 후보에 `video_preview_image_url`이
아예 없어 영상 URL은 있는데 대표 `image_url`이 `None`이 되는 케이스가 있었다).

**여전히 검증되지 않은 부분**: 이 저장소에는 APIFY_TOKEN/.env가 없어(2026-09-22 재확인)
1411948807546506의 실제 raw item을 직접 조회하지 못했다. 위 `VIDEO`/`CAROUSEL`/`MULTI_IMAGES`/
`DPA`/`DCO` 값 집합은 이번 요청에서 사용자가 직접 지정한 분류 규칙이며, 실제 Apify 응답
필드명/값과 정확히 일치하는지는 아래 진단 로깅으로 재검증이 필요하다.

**진단 로깅(`app.services.ad_library_collector._log_media_classification`)**: 매 분류마다
`ad_archive_id`/`raw_display_format`(없으면 `"absent"`)/`videos_count`/`cards_count`/
`images_count`/`card_video_count`/`unique_video_url_count`/`classified_format`/
`classification_reason`을 structured log로 남긴다(URL 원문은 남기지 않음). `classification_reason`
값 목록: `display_format_video`/`dco_video_asset`/`dco_image_only`/`display_format_carousel`
(위 1~3번 규칙이 매치된 경우) / `videos_present`/`single_card_video`/`single_card_image`/
`single_card_empty`/`multi_cards_fallback`/`images_present`/`no_media`(4번 구조 기반 fallback).

**기존(이전 규칙으로 잘못 판정됐던, 또는 signed URL이 만료됐을 수 있는) 소재의 backfill/교정**:
별도 백필 스크립트를 두지 않는다. 다음 수집에서 그 소재가 다시 발견될 때
(`ad_sync.synchronize_ad_status`의 기존 소재 재발견 분기):
- **fresh raw evidence(`item.video_url` 또는 `item.media_items`가 비어있지 않음)가 명확하고
  `item.format != existing.format`이면 `existing.format`을 최신 판정으로 교정한다.** raw
  evidence가 비어있거나 불확실하면(빈 snapshot 등) 절대 덮어쓰지 않는다.
- `media_items`는 항상 fresh 값으로 refresh된다(ephemeral Meta CDN 메타데이터이므로 "한 번
  채워지면 끝"이 아니다).
- `video_url`은 format이 (교정 후 기준으로) `VIDEO`인 동안 fresh 수집마다 최신 signed URL로
  **항상 refresh**된다 — 예전에는 "한 번 채워지면 절대 덮어쓰지 않는다"였지만, signed URL은
  시간이 지나면 만료될 수 있으므로 이 가정을 폐기했다. format이 더 이상 VIDEO가 아니면 이
  필드는 건드리지 않는다(과거 값 보존, destructive clear 없음).
- keyframe 재활성화: format이 VIDEO이고 아직 성공적으로 캐싱된 keyframe이 없는 상태에서
  (a) 방금 VIDEO로 새로 교정됐거나, (b) 기존에 `PENDING`/`FAILED`였는데 signed `video_url`이
  실제로 달라졌으면(만료된 URL 때문에 반복 실패했을 가능성) → `keyframe_status=PENDING`,
  `keyframe_retry_count=0`, `keyframe_error=NULL`로 되돌려 최신 URL로 재시도 가능하게 만든다.
  **이미 `SUCCESS`이고 정상 `keyframe_urls`가 있으면 source URL 변경만으로 삭제/재생성하지
  않는다.**
- `VIDEO → CAROUSEL/IMAGE` 방향 교정도 동일 원칙으로 처리하되, 이미 Storage에 업로드된
  keyframe 파일을 지우는 destructive cleanup은 하지 않는다 — `keyframe_urls` 배열은 보존하고
  `keyframe_status`만 `NOT_APPLICABLE`로 되돌린다.
- `image_url`(대표 썸네일)은 기존에 비어 있었거나, 이번에 format이 실제로 교정된 경우에
  backfill/refresh된다. format이 안 바뀌었는데 이미 값이 있으면 덮어쓰지 않는다(Storage에 이미
  캐싱된 공개 URL이라 계속 유효하므로). Gemini 재태깅 없이 캐싱만 수행하는
  `media.cache_thumbnail_only()`를 쓴다(재발견마다 동기 Gemini 호출을 하면 Core Collection
  latency와 Gemini quota에 영향을 준다) — `app.services.ad_sync`가 이 캐싱을 신규 소재
  enrichment와 동일한 ThreadPoolExecutor 패턴으로 동시 처리한다.

## 11. 기간(주간) 조회 API의 `NO_RECORD` 해석 원칙 (2026-09)

`GET /projects/{project_id}/ad-changes/range`는 단일 날짜 API(`GET .../ad-changes`)와 달리
`collection_status`(단일 SUCCESS/PARTIAL/FAILED/NO_RECORD 값)를 반환하지 않는다. (경쟁사×날짜)
그리드를 채워 하나의 값으로 뭉개면, "자동수집을 켜지 않은 날"의 기록 없음이 "실패"처럼 보이는
위험이 있기 때문이다.

대신 `collection_run_summary`(범위 내 **실제 시도된** `CollectionRun`만 status별로 집계 — 시도
자체가 없던 날짜는 포함되지 않는다)와 `dates_with_collection`(실제 수집 시도가 있었던 날짜 목록)을
반환한다. 프론트는 이 값을 기존 `CollectionFreshness`(`GET .../dashboard/freshness`)와 함께
보여줘 데이터 신뢰도를 판단한다 — "시도 안 함"과 "시도했지만 실패"를 항상 구분해서 표시한다.

`started_ads`/`reactivated_ads`/`stopped_ads`(변화 목록)는 **이벤트 기준**으로 dedupe 없이
나열한다 — 동일 광고가 기간 안에서 여러 이벤트를 가진 경우 event history 의미를 보존하기 위함이다.
(단일 날짜 `get_ad_changes()`의 이 동작은 그대로 유지 — 건드리지 않았다.)

### 11.1 `visual_pattern`/`campaign_mix`의 분모 — "alive 기준"으로 재정의 (2026-09 추가 개정)

**최초 도입 당시(2026-09 초)에는 `visual_pattern`/`campaign_mix`를 "STARTED 또는 REACTIVATED
이벤트가 있었던 unique 광고" 기준으로 집계했다.** 이 방식은 실제로는 문제가 있었다 — 선택 기간
내내 조용히 라이브 상태를 유지한 기존 광고(새 이벤트가 전혀 없는 광고)가 전부 집계에서 빠져서,
실제로는 라이브 광고가 많아도 `visual_pattern`이 텅 비어 보이는 현상이 있었다.

**지금은 두 값 모두 `collection_history.get_alive_ads_in_range()`가 계산하는
"선택 기간에 한 번이라도 실제로 라이브 상태로 관측된 광고"(alive_ads_in_range) 집합을 공유
분모로 삼는다.** STARTED/REACTIVATED 이벤트가 없어도, 그 기간 동안 `AdObservation`으로 계속
관측됐다면 포함된다.

- **source**: `AdObservation`(성공/부분 수집에서 실제 fetch된 광고에 대해서만 기록되는 직접
  관측 데이터) ⋈ `CollectionRun.run_date BETWEEN start_date AND end_date`에서 `DISTINCT ad_id`.
  같은 광고가 기간 내 여러 날 관측돼도 1회만 집계한다.
  - `FAILED` collection_run은 `AdObservation` 자체가 생성되지 않으므로 자동으로 제외된다 —
    "못 받아온 광고를 죽었다고 추정"하지 않으면서 동시에 "봤다"는 근거도 없으므로 alive로도
    치지 않는다.
  - `PARTIAL` collection_run에서 실제 fetch된 광고는 관측 사실 자체는 유효하므로 alive에 포함한다
    (P0-02 — snapshot이 잘렸을 수 있다는 것과, 실제로 발견된 소재가 그 순간 라이브였다는 것은
    별개의 사실이다).
- **`visual_pattern` 분모**: alive_ads_in_range 전체. `visual_type`이 없는(아직 Gemini 분석 전인)
  광고를 조용히 제외하지 않고 `"UNANALYZED"` 키로 명시한다 — 그렇지 않으면 "분석 완료 광고만
  보면 100%"처럼 실제 라이브 광고 대비 비율이 왜곡된다.
- **`campaign_mix` 분모**: 동일한 alive_ads_in_range. `campaign_tag_id`가 있고
  `campaign_classification_status == SUCCESS`인 광고만 해당 태그로 집계하고, `NEEDS_REVIEW`는
  별도 키, 그 외(`PENDING`/`FAILED`/태그 없음)는 전부 `"UNCLASSIFIED"`로 묶는다.
- **`alive_ad_count`**(신규 additive 필드): 위 두 dict의 값 합계와 항상 같다 — 프론트가 "선택 기간
  라이브 소재 N개 기준"이라는 문구에 활용한다.
- 비주얼 패턴과 캠페인 패턴은 **항상 같은 분모**를 쓴다 — 하나는 이벤트 기준, 다른 하나는 다른
  기준으로 절대 갈라지지 않는다.
- **재분류/재분석이 과거 기간 집계에 미치는 영향은 §9의 원칙과 동일하다** — `Ad.visual_type`/
  `campaign_tag_id`는 "현재 값"이므로, 소재를 재분석/재분류하면 그 소재가 걸린 과거 주차의
  집계도 함께 바뀐다(스냅샷이 아니다).
- 단일 날짜 `get_ad_changes()`의 `visual_pattern`은 이 개정의 영향을 받지 않는다(이벤트 기준
  그대로 유지 — 건드리지 않았다). 향후 단일 날짜 API도 동일한 필요가 생기면 별도로 검토한다.

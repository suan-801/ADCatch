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

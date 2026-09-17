---
name: 11-monitor
description: Meta·GA4 → Google Sheets 3탭 ETL. raw 데이터 적재 + Looker Studio·시트 직접 시각화. KST 08:30 cron. Clarity 는 본 스킬 범위 ❌ (별도 HTML 리포트 트랙).
trigger: "ETL 돌려", "모니터링 갱신", "시트 채워줘", "/11-monitor"
---

# /11-monitor — Google Sheets 3탭 ETL 오케스트레이터

## 무엇

2 소스 → 1 시트 (3탭):

| 탭 | 키 | 소스 |
|---|---|---|
| `meta_daily` | date | Meta 어카운트 합계 |
| `meta_breakdowns` | date+level+id | Meta 캠페인·광고 단위 |
| `ga4_daily` | date | GA4 sessions·utm·신규vs재방문 |

Looker Studio·구글시트 자체 차트로 시각화 → 별도 Next.js 빌드 ❌.

> ⚠️ **Clarity 제외** — 이 스킬은 데이터 축적 ❌. Clarity 는 별도 HTML 리포트 트랙 (on-demand) 으로 분리됨.

## 어떻게

```bash
# 어제 자동 + Sheets 갱신
python3 _shared/scripts/etl_run.py

# Sheets 키 없을 때 — 페이로드만 dump
python3 _shared/scripts/etl_run.py --date 2026-05-11 --dry-run
```

자동화: `.github/workflows/etl_run.yml` 가 매일 **UTC 23:30 = KST 08:30** (daily-slack 30분 전).

## 입력

- `09_tracking/.env` — Meta (필수), `GOOGLE_SHEETS_ID`, `GOOGLE_SERVICE_ACCOUNT_PATH` 또는 `_JSON` (또는 `_EMAIL`+`_PRIVATE_KEY`), `GA4_PROPERTY_ID` + `GA4_SERVICE_ACCOUNT_PATH`/`_JSON`

## 출력

- Google Sheets (운영) — UPSERT 패턴, 같은 키 행은 덮어쓰기
- `11_dashboard/etl/etl_payload_{date}_{ts}.json` — dry-run dump (Sheets 미설정 시)

## 핵심 룰

1. **GA4 vs Meta 분리 (메모리 룰)** — ROAS·매출은 Meta 만. GA4 는 utm·트래픽 분석용. Sheets 도 그렇게 분리 적재.
2. **freshness 컬럼 필수** — meta_daily 의 D-1 = `t1_preview`, D-2~6 = `t2_stable`, D-7+ = `t7_meta_refresh`, D-28+ = `t28_meta_final`. period-report 가 이 컬럼을 보고 집계 여부 결정.
3. **UPSERT 키 안정성** — meta_breakdowns 는 `(date, level, id)`. 같은 광고 행이 덮어써져 freshness 변동을 자연스럽게 반영.
4. **dry-run 친화** — Sheets 키 없어도 코드 검증 가능. CI 가 키 누락 시 자동 dry-run 으로 전환.

## CHANGELOG

- 2026-05-27 v2 단순화 — Clarity 탭·experiments_observed 탭 제거. 5탭 → 3탭 (meta_daily·meta_breakdowns·ga4_daily). Clarity 는 별도 HTML 리포트 트랙으로 분리. `--skip-clarity` 플래그·Clarity 한도 보호 룰 제거.
- 2026-05-12 v1 신규 — 4-4_marketing_dashboard 의 5탭 스키마 + UPSERT 로직 흡수. dry-run 모드 추가.

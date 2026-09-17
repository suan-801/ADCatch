#!/bin/bash
# 대시보드 일일 자동 갱신 — cron 용.
# ① ETL dry-run(JSON dump) → ② 시트 UPSERT → ③ 소재 썸네일 → ④⑤⑥ 대시보드 재렌더
# cron 은 최소 환경이라 절대경로 사용. 로그는 _shared/logs/refresh_YYYY-MM-DD.log
set -u

# 스크립트 위치(_shared/scripts/) 기준으로 워크스페이스 루트 자동 산출 — 브랜드·경로 하드코딩 없음
WS="$(cd "$(dirname "$0")/../.." && pwd)"
PY="/opt/homebrew/bin/python3"
BRAND="sample_brand"
export HOME="${HOME:-/Users/hyeongtaekim}"   # gcloud ADC (~/.config/gcloud) 위치용

cd "$WS" || exit 1
mkdir -p "$WS/_shared/logs" "$WS/_shared/outputs/etl"
LOG="$WS/_shared/logs/refresh_$(date +%Y-%m-%d).log"

run() {
  echo "── $* ──"
  "$@"
  local rc=$?
  echo "   exit=$rc"
  return $rc
}

{
  echo "════════ refresh start $(date '+%Y-%m-%d %H:%M:%S %Z') ════════"

  # ① 데이터 수집(JSON dump) — Meta+GA4 API 1회 pull
  run "$PY" _shared/scripts/etl_run.py --brand "$BRAND" --dry-run --skip-clarity
  cp "$WS"/11_dashboard/etl/etl_payload_*.json "$WS"/_shared/outputs/etl/ 2>/dev/null || true

  # ② 소재 썸네일 (신규만)
  run "$PY" _shared/scripts/download_creatives.py

  # ③ HTML 대시보드 — 전부 JSON 소스(--source dry_run)로 렌더 → Sheets 읽기 쿼터와 무관
  run "$PY" _shared/scripts/render_overview_dashboard.py --brand "$BRAND" --range 30
  run "$PY" _shared/scripts/render_meta_dashboard.py --brand "$BRAND" --days 30 --source dry_run
  run "$PY" _shared/scripts/render_ga4_dashboard.py --brand "$BRAND" --days 30 --source dry_run

  # ④ 시트 UPSERT(Looker용) — 맨 끝에 분리, 앞에 sleep 으로 읽기 쿼터 윈도 분리
  sleep 25
  run "$PY" _shared/scripts/backfill_sheets_from_json.py

  echo "════════ refresh done  $(date '+%Y-%m-%d %H:%M:%S %Z') ════════"
} >> "$LOG" 2>&1

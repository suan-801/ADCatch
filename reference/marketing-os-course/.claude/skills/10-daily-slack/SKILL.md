---
name: 10-daily-slack
description: Meta Ads 어제 데이터 → Slack 데일리 리포트 1통. 매일 KST 09:00 GitHub Actions cron 자동 발송 + 슬래시로 수동 실행 가능.
trigger: "데일리 슬랙", "오늘 리포트", "어제 광고 요약", "/10-daily-slack"
---

# /10-daily-slack — Meta Ads 데일리 슬랙 리포트

## 무엇

어제 Meta Ads 데이터 한 통의 슬랙 메시지로:
- 어제 KPI 카드 (지출·CTR·ROAS·구매·CPA) + 전일/7일평균 대비
- 캠페인 TOP 5 (신호등 🟢🟡🔴)
- 고성과 소재 TOP 5 (구매≥1)
- 저성과 소재 (구매 0 or ROAS < 경계)
- 가드레일 알림 (예산 초과, CTR/ROAS 경계 미달)

## 어떻게

```bash
# 어제 자동
python3 _shared/scripts/daily_slack.py

# 특정 날짜 + 발송 안 함 (로컬 검증)
python3 _shared/scripts/daily_slack.py --date 2026-05-11 --no-slack

# 브랜드 전환
python3 _shared/scripts/daily_slack.py --brand [브랜드명]
```

자동화: `.github/workflows/daily_report.yml` 가 매일 **UTC 00:00 = KST 09:00** 에 호출.

## 입력

- `09_tracking/.env` — `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN`, `META_AD_ACCOUNT_ID`, `SLACK_WEBHOOK_URL`
- `_shared/config/brand_kpi.yml` — 브랜드별 신호등 임계값 (`roas_green`, `roas_red`, `ctr_red_pct`, `cpa_red`, `spend_min`, `daily_budget`)

## 출력

- `10_daily/{브랜드}/{YYYY-MM-DD}-slack.txt` — Slack 발송 메시지 원본
- `10_daily/{브랜드}/{YYYY-MM-DD}-slack.json` — 원시 데이터 (period-report 가 후속 흡수)
- Slack 채널 발송 (`--no-slack` 일 때만 skip)

## 핵심 룰

1. **어트리뷰션** — ROAS·매출은 Meta Ads Manager 기본값(7d-click + 1d-view)만 표기. GA4 블록은 utm 유입 트래픽 검증용으로 사용. 메시지 footer 에 출처 명시.
2. **freshness tier** — 어제(D-1) 데이터는 `t1_preview`. 메시지 헤더와 footer 에 tier 표기. 주간/월간 보고에는 t2_stable 이상만 권장.
3. **TOP/BOTTOM 필터** — 지출 `spend_min` 미만은 노이즈로 제외. TOP 은 구매≥1 인 소재만. BOTTOM 은 구매=0 또는 ROAS<경계.
4. **신호등** — `kpi_config.light()` 가 green/red 임계값에 따라 🟢🟡🔴 부여. brand_kpi.yml 만 수정하면 모든 리포트에 적용.

## 의존성

- facebook-business >= 25.0.1
- Jinja2, PyYAML
- (Slack 발송용) `urllib`만 사용 — 외부 패키지 불필요

## CHANGELOG

- 2026-05-12 v1 신규 — Meta 단독, GA4 블록은 Phase 2 ETL 후 연결.

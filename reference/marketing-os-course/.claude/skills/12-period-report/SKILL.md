---
name: 12-period-report
description: 주간·월간·캠페인 종료 리포트. Meta API 직접 풀 + GA4 흡수 → HTML + PDF. frontend-slides 스킬로 deck 렌더, 양식 = _shared/templates/period_v1/deck.html.j2.
trigger: "주간 리포트", "월간 리포트", "캠페인 결산", "임원 보고서", "/12-period-report"
---

# /12-period-report — 기간 리포트 (HTML + PDF)

## 무엇

임원·고객 보고용 리포트. HTML 슬라이드 묶음을 chromium 으로 캡처해 A4 가로 PDF 까지 한 번에 출력.

| 슬라이드 | 내용 |
|---|---|
| 1 표지 | 기간·브랜드·핵심 KPI 4카드 |
| 2 추이 | 일별 지출·매출·ROAS Chart.js |
| 3 캠페인 TOP | 지출 상위 5 캠페인 ROAS·구매 |
| 4 소재 TOP | 고성과 8 + 저성과 5 광고 |
| 5 GA4 채널 믹스 | 트래픽·신규 vs 재방문 (없으면 placeholder) |
| 6 어트리뷰션 footer | Meta vs GA4 차이% 명시 |
| 7 다음 액션 | 우선순위·일반 액션 |

> ⚠️ **Clarity 슬라이드 ❌** — 11-monitor v2 정책에 따라 Clarity 는 본 리포트 범위에서 제외 (별도 HTML 리포트 트랙).

## 의존 스킬·양식

- **`frontend-slides` 스킬** — HTML 슬라이드 렌더링 엔진. viewport-base.css + STYLE_PRESETS + html-template 사용. 100vh 슬라이드, zero-dependency.
- **참조 양식**: `_shared/templates/period_v1/deck.html.j2` (Jinja2 템플릿, ~705줄 — 실제 렌더링 엔진). 표지 + KPI·캠페인·소재·GA4·액션 섹션 구조 + Noto Serif KR / Pretendard 폰트 + `:root` 브랜드 중립 컬러 토큰. 실제 색은 `01_brand/brand_brief.md` 6슬롯에서 매핑.

## 어떻게

```bash
# 주간 (지난주 월~일)
python3 _shared/scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11

# 월간
python3 _shared/scripts/period_report.py --period monthly --from 2026-05-01 --to 2026-05-31

# 캠페인 종료
python3 _shared/scripts/period_report.py --period campaign --from 2026-05-01 --to 2026-05-11 --campaign-id 12345

# HTML 만 (Playwright 없을 때)
python3 _shared/scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11 --no-pdf
```

## 입력

- **필수**: `09_tracking/.env` — `META_APP_ID/SECRET/ACCESS_TOKEN/AD_ACCOUNT_ID`
- **선택**: `GA4_PROPERTY_ID` + `GA4_SERVICE_ACCOUNT_*` (있으면 GA4 슬라이드 채움)
- **양식 참조**: `_shared/templates/period_v1/deck.html.j2` — 새 리포트 생성 시 이 파일의 슬라이드 구조·CSS 토큰·레이아웃을 그대로 사용

## 출력

- `12_period/{브랜드}/{since}_{until}-v{N}.html`
- `12_period/{브랜드}/{since}_{until}-v{N}.pdf` (Playwright chromium A4 landscape)

## 핵심 룰

1. **ROAS·매출 진실값 = Meta** — 슬라이드 1·2·3·4·7 의 ROAS/구매/매출은 모두 Meta. GA4 슬라이드는 별도 섹션으로 분리.
2. **어트리뷰션 차이 명시 (footer)** — "ROAS·매출은 Meta Ads Manager 어트리뷰션(7d-click + 1d-view) 기준. GA4 는 utm 유입·트래픽 분석용. freshness: {tier}." 모든 슬라이드에 같은 카피.
3. **freshness 표기** — 표지에 `t1_preview` ~ `t28_meta_final` 명시. D-7 이상 (t7+) 만 임원 보고 권장.
4. **고/저 성과 컷오프** — `config/brand_kpi.yml` 의 `spend_min` 미달 광고는 후보 제외. TOP 은 `purchases >= 1`, BOTTOM 은 `purchases == 0` 또는 `roas < roas_red`.
5. **버전 자동 증가** — 같은 기간 재실행 시 `v2`, `v3` 자동.
6. **frontend-slides 100vh 룰 준수** — 슬라이드 내 스크롤 ❌. 콘텐츠 넘치면 슬라이드 분할.

## 디자인 토큰

`_shared/templates/period_v1/deck.html.j2` 의 `:root` CSS 변수 그대로 흡수. 새 브랜드 적용 시 `01_brand/brand_brief.md` 의 컬러 팔레트 6슬롯 → 토큰 매핑.

## 자동화

수동 트리거 only. 캠페인 끝났을 때 / 매주 월요일 / 매월 1일 사용자가 슬래시 호출.
(Phase 2 — 주간 cron 가능, 단 실제 PDF 가 슬랙에 첨부되는 흐름은 별도 작업)

## CHANGELOG

- 2026-05-27 v2 단순화 — Clarity 슬라이드 제거 (11-monitor v2 정책 정합). 슬라이드 8→7. frontend-slides 스킬 의존성 명시. 양식 = `_shared/templates/period_v1/deck.html.j2` 로 단일 참조.
- 2026-05-12 v1 신규 — Meta 직접 풀 + GA4/Clarity placeholder + Playwright PDF. 5/5~5/11 데이터로 HTML+PDF 1세트 검증.

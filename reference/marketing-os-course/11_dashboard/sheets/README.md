# Google Sheets 탭별 CSV 묶음

> `_build_sheets.py` 가 ETL 페이로드를 탭별 CSV 로 consolidate 한 결과를 이 폴더에 모아둡니다. 학생이 본인 브랜드 데이터로 ETL 실행 시 자동 생성됩니다.

## 🔗 실제 Google Sheets (라이브)

**URL**: https://docs.google.com/spreadsheets/d/

**ID**: ``

12개 탭 = 아래 CSV 파일과 1:1 매핑. 본인 구글 계정 (ADC 인증) 으로 편집 가능. `09_tracking/.env` 에 `GOOGLE_SHEETS_ID` 로 등록하면 11-monitor ETL 의 UPSERT 타겟으로 사용.

---

## 데이터 출처

`11_dashboard/etl/etl_payload_*.json` 81개 → `_build_sheets.py` 로 탭별 단일 CSV 로 합침.

```
ETL 페이로드 (raw, 일자별)              →  CSV (consolidated, 탭별)
─────────────────────────────────         ──────────────────────────
etl_payload_2026-03-01_*.json
etl_payload_2026-03-02_*.json
... × 81 일                       →     meta_daily.csv (81 rows)
                                         meta_breakdowns.csv (594 rows)
                                         meta_demographics.csv (1995 rows)
                                         meta_creatives.csv (399 rows)
                                         ga4_daily.csv (81 rows)
                                         ga4_channel_daily.csv (438 rows)
                                         ga4_device_daily.csv (243 rows)
                                         ga4_landing_daily.csv (729 rows)
                                         ga4_product_daily.csv (405 rows)
                                         ga4_funnel_daily.csv (81 rows)
                                         ga4_demo_daily.csv (324 rows)
                                         ga4_geo_daily.csv (1377 rows)
```

> ⚠️ `clarity_*` 탭은 의도적으로 제외 (11-monitor v2 스킬에서 Clarity 제외 결정. Clarity 는 별도 HTML 리포트 트랙).

## 탭 12개

| 탭 (= CSV 파일) | 행 수 | 주요 컬럼 |
|---|---|---|
| `meta_daily` | 81 | date, spend, impressions, ctr, roas, cpa, purchases |
| `meta_breakdowns` | 594 | date+level+id, campaign/adset/ad 단위 성과 |
| `meta_demographics` | 1995 | 성별×연령 segment 성과 |
| `meta_creatives` | 399 | ad_id, ad_name, thumbnail, copy |
| `ga4_daily` | 81 | sessions, users, conversions, top_source |
| `ga4_channel_daily` | 438 | channel·source·medium 별 |
| `ga4_device_daily` | 243 | Desktop/Mobile/Tablet |
| `ga4_landing_daily` | 729 | landing_path 별 bounce·conv |
| `ga4_product_daily` | 405 | 상품별 view→ATC→purchase |
| `ga4_funnel_daily` | 81 | 일자별 5단 퍼널 |
| `ga4_demo_daily` | 324 | 연령×성별 demographics |
| `ga4_geo_daily` | 1377 | 지역별 sessions·conversions |

## 강의 시연 시 사용법

### A. CSV 그대로 사용 (가장 간단)
강의 화면에서 CSV 1~2개 열어 "이게 Sheets 의 한 탭이라고 가정합니다" 라고 설명.

### B. Google Sheets 에 임포트 (라이브감 ↑)
1. [sheets.google.com](https://sheets.google.com) 접속 → 새 스프레드시트
2. 좌하단 `+` 로 12 탭 생성 후 탭 이름을 CSV 파일명과 동일하게 설정 (meta_daily, meta_breakdowns, ...)
3. 각 탭에서 **파일 → 가져오기 → 업로드** → 해당 CSV 선택 → "현재 시트 바꾸기"
4. 스프레드시트 URL 의 `/d/{ID}/edit` 부분의 `{ID}` 를 `GOOGLE_SHEETS_ID` 환경변수로 두면 11-monitor 가 그 시트로 ETL 결과 UPSERT
5. 시트 공유 권한 → 본인 구글 계정·서비스 계정 모두 편집자 추가

### C. 재생성
페이로드가 갱신되면 CSV 다시 빌드:
```bash
python3 11_dashboard/sheets/_build_sheets.py
```

## 대시보드 연결

`11_dashboard/dashboards/*.html` 의 6개 정적 HTML 은 본 데이터를 기반으로 사전 빌드된 결과물.
- `overview_2026-04-30.html` / `_2026-05-13.html` — 두 시점 종합 뷰
- `meta_dashboard_*.html` — Meta 단독
- `ga4_dashboard_*.html` — GA4 단독

> Clarity 대시보드는 의도적으로 제거 — 본 OS 의 11-monitor v2 스킬 정책 (Clarity 별도 HTML 리포트 트랙으로 분리).

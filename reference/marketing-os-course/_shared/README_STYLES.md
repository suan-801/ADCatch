# 기간 리포트 두 가지 스타일 가이드

`period_report.py` 는 동일한 데이터(Meta·GA4·Clarity)로 **두 가지 톤의 기간 리포트**를 만들 수 있습니다.

| 스타일 | 용도 | 톤 | 슬라이드 수 | 가독 컨텍스트 |
|---|---|---|---|---|
| **`compact`** | 실무 점검·일일 회의 | navy `#1E3A5F` + copper `#B87333` + pearl `#FAF5F0` · 데이터 직시 | 8 슬라이드 (단일 페이지 reveal) | A4 landscape PDF·Slack 첨부·인쇄 |
| **`deck`** | 발표·경영진 보고·외부 공유 | Luminous Purple `#8B6BCF` + Deep Violet `#4A3A7D` + Ice Lavender `#EFE9FB` · 스토리텔링 | 16 슬라이드 (100vh scroll-snap) | 브라우저 풀스크린·키노트 대체·키보드 네비 |

`compact` 는 빠르게 "어디가 새고 있나" 를 보기 위한 한 화면 점검이고, `deck` 는 "왜 이렇게 됐는지" 를 한 슬라이드씩 풀어 설명하는 발표용입니다. 두 산출물은 같은 Meta/GA4 데이터에서 자동 생성되므로 수치는 항상 일치합니다.

---

## 호출 방법

```bash
cd Claudecode_MarketingOS_student/_shared

# 1) 둘 다 (기본값)
python3 scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11

# 2) compact 만
python3 scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11 --style compact

# 3) deck 만
python3 scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11 --style deck

# 4) PDF 스킵 (HTML 만)
python3 scripts/period_report.py --period weekly --from 2026-05-05 --to 2026-05-11 --style both --no-pdf
```

`--style` 미지정 시 기본값은 `both` — 두 산출물이 동시에 생성됩니다.

---

## 출력 파일명

```
outputs/period/{brand}/{since}_{until}-{style}-v{N}.html
outputs/period/{brand}/{since}_{until}-{style}-v{N}.pdf
```

예시 ([브랜드명] 주간 리포트):

```
outputs/period/[브랜드명]/2026-05-05_2026-05-11-compact-v1.html
outputs/period/[브랜드명]/2026-05-05_2026-05-11-compact-v1.pdf
outputs/period/[브랜드명]/2026-05-05_2026-05-11-deck-v1.html
outputs/period/[브랜드명]/2026-05-05_2026-05-11-deck-v1.pdf
```

같은 기간을 재실행하면 `-v2`, `-v3` 으로 자동 증분되어 이전 파일을 덮어쓰지 않습니다.

---

## 데이터 소스 · 동등성

두 스타일 모두 동일한 데이터 풀에서 산출됩니다:

| 소스 | 항목 |
|---|---|
| Meta Ads API | 광고비·노출·클릭·구매·매출·ROAS (어트리뷰션 7d-click+1d-view) |
| `outputs/daily/{brand}/*-slack.json` | 일별 캐시 (Meta API 호출 절약) |
| GA4 Service Account | 세션·신규유저·이벤트 (선택 — 없으면 placeholder) |
| `outputs/cro/{brand}/*-cro-v*.md` | CRO 가설·페인 페이지 (선택) |

→ KPI 수치는 두 산출물에서 항상 동일합니다.

---

## 스타일별 슬라이드 구조

### `compact` (8 슬라이드)
`templates/period_v1/index.html.j2` 참조.

| # | 슬라이드 | 내용 |
|---|---|---|
| 01 | 표지 | navy 그라데이션 + 4 KPI |
| 02 | 한 줄 요약 | 핵심 결론 |
| 03 | KPI 카드 | spend·revenue·roas·purchases |
| 04 | Top 캠페인 | 5위까지 |
| 05 | Top 광고 | 8위까지 |
| 06 | OFF 권장 | 5위까지 |
| 07 | 다음 액션 | 우선순위 4개 |
| 08 | 어트리뷰션·푸터 | freshness tier · 데이터 소스 |

### `deck` (16 슬라이드)
`templates/period_v1/deck.html.j2` 참조.

| # | 슬라이드 | 내용 |
|---|---|---|
| 01 | Cover | 다크보라 + WEEK 번호 + 인사말 |
| 02 | TOC | 12개 챕터 목차 |
| 03 | Divider | "이 주의 숫자들" |
| 04 | 한 줄 요약 | headline + lead + 4 big numbers |
| 05 | 8대 KPI | sessions/new_users/impressions/ctr/spend/revenue/roas/cpa |
| 06 | 캠페인 점유 | Top 4 캠페인 ROAS + 매출 |
| 07 | 소재별 효율 | Top 12 풀 테이블 (ROAS desc) |
| 08 | 🥇 베스트 #1 | Hero 카드 — 썸네일 + 4 통계 + 인사이트 |
| 09 | 베스트 2~5 | 2×2 미니 카드 |
| 10 | 🚨 워스트 #1 | Hero 카드 — 빨강 톤 |
| 11 | OFF 권장 4종 | 2×2 미니 카드 |
| 12 | 이긴 앵글 분석 | 3 패턴 (override 가능) |
| 13 | 진 앵글 분석 | 3 패턴 (override 가능) |
| 14 | Clarity CX | 4 CX 메트릭 (CRO 흡수 시) |
| 15 | 다음 주 액션 | 우선순위 5개 |
| 16 | Closing | 다크보라 + 다음 주 시작 메시지 |

---

## 썸네일 자동 추출

`deck` 스타일은 베스트/워스트 슬라이드에 광고 소재 썸네일을 표시합니다.

- 원본 위치: `outputs/creatives/{ad_name_base}.jpg|png|mp4`
- 자동 처리:
  1. `outputs/creatives/` 에 동일 이름 jpg/png 가 있으면 → 그대로 `outputs/period/{brand}/assets/creatives/` 로 복사
  2. mp4 만 있으면 → ffmpeg 로 1초 지점 480px 썸네일 자동 추출
- 이름 매칭: `meta036_260420_sh_FP` → `meta036_260420_sh.{jpg|png|mp4}`
- ffmpeg 가 PATH 에 있어야 동영상 추출이 작동합니다 (없으면 썸네일 자리는 라벤더 박스로 빈 상태).

---

## 언제 어떤 스타일?

| 상황 | 추천 스타일 |
|---|---|
| 매주 월요일 09:00 자동 슬랙 발송 첨부 | `compact` (PDF) |
| 월요일 팀 미팅에서 한 화면씩 띄우며 설명 | `deck` (브라우저 풀스크린) |
| 외부 파트너·외주 디자이너 공유 | `deck` (브랜드 보라 일관성) |
| 모바일에서 빠르게 훑기 | `compact` |
| 1주 단위 디스크 보존·아카이브 | `both` (자동 v 증가로 누적) |

---

## 향후 확장

- `deck` 의 narrative 블록(이긴/진 앵글 분석, headline 카피) override — 현재는 데이터에서 자동 도출, YAML 오버라이드 옵션 검토
- Clarity CX 슬라이드 — `outputs/cro/{brand}/*-cro-v*.md` 자동 파싱 (현재는 데이터 없으면 슬라이드 자동 생략)
- `--style executive` (deck 변형 — 발표용 더 압축한 6 슬라이드)
- `--lang en` (영문 발표 — 글로벌 파트너 공유용)

---

*이 문서는 `period_report.py --style` 플래그 추가와 함께 `2026-05-14` 작성됨.*

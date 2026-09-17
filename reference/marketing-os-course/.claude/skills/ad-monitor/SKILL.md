---
name: ad-monitor
description: 독립형 광고 모니터링 스킬. Meta 광고 라이브러리 URL 하나를 넣으면 자사·경쟁사 구분 없이 ① 소재(이미지·영상) 수집 ② USP 3항목(User's Problem·Solution·Promotion) + Creative Key Visual + ad_pattern 분석 ③ 브랜드별 인사이트 요약 ④ 랜딩 URL의 UTM/트래킹 파라미터 관찰 + 캠페인·그룹·소재명 규칙 베스트에포트 유추 ⑤ 팀 공유용 구글독스 발행까지 처리. `Claudecode_MarketingOS_student` 프로젝트의 01_brand/02_competitor/03_customer/04_brief 등 다른 스킬 산출물을 전혀 참조하지 않는 독립 스킬 — `ad_monitor/` 폴더 하나로 완결됨. 사용자가 "광고 모니터링해줘", "이 URL 광고 분석해줘 (독립적으로)", "/ad-monitor" 등으로 요청할 때 호출.
---

# ad-monitor — 독립 광고 모니터링 스킬

> `02-competitor-from-adlib` 스킬을 기반으로 만든 독립형 버전. 이 스킬은 `01_brand/`·`02_competitor/`·`03_customer/`·`04_brief/`
> 등 프로젝트의 다른 스킬 산출물을 **전혀 읽지 않습니다**. 모든 입출력은 `ad_monitor/` 폴더 안에서만 일어납니다.
> 자사 브랜드든 경쟁사든 구분하지 않고, 넣은 URL 을 전부 동등한 분석 대상으로 취급합니다.

## 언제 호출되는가

- "광고 모니터링해줘"
- "이 URL 광고 분석해줘 (독립적으로)"
- "/ad-monitor"
- `ad_monitor/` 가 이미 있고 URL 을 추가/갱신할 때

## Prerequisites

- `ad_monitor/.env` — `APIFY_TOKEN` 필수, `GEMINI_API_KEY_FREE`(또는 `GEMINI_API_KEY`) 없으면 수집만 하고 분석은 스킵. 템플릿: `.env.example`
- Google Docs 공유 단계(Step 8)를 쓰려면 claude.ai Google Drive 커넥터 연결 필요 (`mcp__claude_ai_Google_Drive__*` 도구 사용 가능 여부로 확인)

---

## 작업 순서 (8 단계)

### Step 1. URL 입력

`ad_monitor/_inputs/urls.md` 한 파일에 URL 을 한 줄씩 적으면 끝. `##` 헤딩은 자유 그룹 라벨(선택, 분류 강제 ❌).

```bash
python3 ad_monitor/_scripts/fetch_ads.py
```

단발 URL(파일 안 건드림): `python3 ad_monitor/_scripts/fetch_ads.py "<URL>"`
기존 슬러그 재실행: `python3 ad_monitor/_scripts/fetch_ads.py <slug>`

> Page ID 기반 딥링크 권장. 자세한 입력 규칙은 `ad_monitor/_inputs/README.md` 참고.

### Step 2. Apify 크롤링

```bash
python3 ad_monitor/_scripts/fetch_ads.py --max 50     # 브랜드당 최대 광고 수
python3 ad_monitor/_scripts/fetch_ads.py --no-gemini  # 분석 스킵 (수집만)
python3 ad_monitor/_scripts/fetch_ads.py --md-only    # 기존 데이터로 보고서만 재생성
python3 ad_monitor/_scripts/fetch_ads.py --paid       # 유료 Gemini 키 사용
```

Gemini 무료 한도(250 RPD) 도달 시 부분 결과를 보존하고 종료 — 24시간 후 재실행하면 미분석분만 이어서 처리됩니다 (`analysis.json` 의 `status: "quota_exceeded"` 로 마킹).

### Step 3. 미디어 + 메타 저장

`ad_monitor/{slug}/ad-creatives/{metadata.json, images/, videos/, keyframes/}` 에 저장. 원본 스킬과 동일한 7필드(ad_id·title·caption·cta_text·link_url·landing_domain·active_period·media).

### Step 4. USP 3항목 + Creative Key Visual + ad_pattern 분석

`ad_monitor/_reference/analysis_method.md` 정의 그대로 적용 (User's Problem · Solution · Promotion + Creative Key Visual, `ad_pattern` 1개 라벨). 이미지/영상 처리 방식은 원본 02 스킬과 동일 — 영상은 ffmpeg 키프레임 6장 → Gemini 멀티모달 분석, 대본·오디오 추출 ❌.

### Step 5. 브랜드별 1페이지 요약

`ad_monitor/{slug}/ad-creatives.md` 자동 생성 — 포맷 믹스·CTA 분포·랜딩 도메인·캡션 키워드·**UTM 관찰**·광고 카드 전수.

### Step 6. 로컬 대시보드

```bash
python3 ad_monitor/_scripts/build_dashboard.py
```

`ad_monitor/dashboard/index.html` — 더블클릭으로 로컬 확인.

### Step 7. UTM/캠페인 명명 규칙 유추 (★ 베스트에포트)

`fetch_ads.py` 실행 시 `ad_monitor/ads_report.md` § 9 에 브랜드별 UTM 관찰 표가 자동 삽입됩니다 (파라미터 키·등장 빈도·관찰된 값 예시 — `ad_monitor/_scripts/utm_pattern.py` 가 순수 데이터만 추출, "규칙 확정" 주장 안 함).

**Claude 가 직접 할 일** (스크립트가 못 하는 판단 단계):
1. `ads_report.md` § 9 표 또는 개별 `{slug}/ad-creatives/utm_samples.json` 을 읽는다.
2. 브랜드별로 값들 사이에서 델리미터(예: `_`·`-`)·포지션별 토큰 패턴이 보이면, "추정 규칙"을 1~2줄로 채팅에 제시한다. 예: `utm_campaign` 값이 `2026spring_launch`, `2026summer_sale` 처럼 보이면 → "`{연도+시즌}_{목적}` 패턴으로 추정".
3. 근거가 부족하면(값이 아예 없거나 무작위 해시로 보이면) **추정하지 말고** "규칙을 유추할 근거가 부족합니다"라고 명시한다.
4. ⚠️ **이 추정은 항상 베스트에포트임을 밝힌다.** 경쟁사 URL 은 리다이렉트·클릭ID(fbclid 등)만 있고 utm 값 자체가 없는 경우가 흔해 정확도가 낮을 수 있고, 자사 URL 은 직접 설계하므로 신뢰도가 높다는 점을 구분해서 말한다.

### Step 8. 팀 공유 — 구글독스 발행

1. `ads_report.md`(통합) 또는 `{slug}/ad-creatives.md`(브랜드 단일)를 HTML 로 변환 (헤딩·표가 살아있도록 마크다운 → 간단한 `<h1>`~`<h3>`/`<table>`/`<p>` HTML로 변환. 별도 CSS 불필요, 가독성만 확보).
2. `mcp__claude_ai_Google_Drive__create_file` 호출 — `title`: `{브랜드}_광고모니터링_{YYYY-MM-DD}`, `textContent`: 위 HTML, `contentMimeType`: `text/html` (자동으로 Google Docs 형식으로 변환됨).
3. 공유가 필요하면 사용자에게 공유 대상(팀원 이메일 또는 링크 공유 여부)을 물어보고 `mcp__claude_ai_Google_Drive__share_file` 호출.
4. 생성된 문서 링크를 채팅으로 전달.

> ⚠️ **알려진 한계 — 매번 새 문서.** 현재 연결된 Drive 도구는 파일 생성/메타데이터 수정만 가능하고 **기존 문서의 본문 내용을 갈아끼우는 기능이 없습니다.** 즉 이 Step 8 은 실행할 때마다 새 독스 문서를 만듭니다 — 팀원이 북마크한 링크가 계속 최신 상태로 업데이트되는 방식이 아닙니다. 항상 같은 링크가 갱신되는 "진짜 업데이트"가 필요하면, Google Cloud 서비스 계정을 만들어 Docs API 쓰기 권한을 주고 같은 문서 ID 에 매번 본문을 교체하는 방식으로 전환해야 합니다 (`09-tracking-setup`/`11-monitor` 와 동일한 패턴 — 사용자가 원하면 별도로 안내).

---

## 이 스킬이 하지 않는 것 (독립성 유지)

- ❌ `01_brand/brand_brief.md` 읽기 — "자사 대비 빈틈" 같은 비교 섹션 없음. 대신 § 8 "메시지 각도 커버리지"에서 추적 중인 브랜드 전체 기준 0건/저점유 앵글만 중립적으로 제시.
- ❌ 직접경쟁/간접경쟁 분류 강제 — `##` 그룹 라벨은 자유 텍스트, 있어도 그만 없어도 그만.
- ❌ 다른 스킬(04/05/06/07/08) 자동 호출 — 이 스킬의 출력은 오직 `ad_monitor/` 안에만 쌓임.

## 트러블슈팅

| 상황 | 대응 |
|---|---|
| `_inputs/urls.md` 비어 있음 | Step 1 양식대로 URL 작성 안내 |
| Apify 액터 차단 | URL 형식 점검 → Page ID 딥링크로 변경 |
| ffmpeg 미설치 | 영상 키프레임 추출 실패 — 설치 후 재실행 |
| Gemini 무료 한도 초과(429) | 부분 결과 보존, 24h 후 재실행 또는 `--paid` |
| UTM 표가 텅 비어있음 | 해당 브랜드 링크가 리다이렉트/단축 URL 이거나 utm 자체를 안 씀 — Step 7 에서 "근거 부족"으로 명시하고 규칙 추정 생략 |
| Google Drive 도구가 안 보임 | claude.ai Google Drive 커넥터 미연결 — 사용자에게 연결 안내 (https://claude.ai/customize/connectors), 안내 후 Step 8 은 스킵하고 로컬 `ads_report.md`/HTML 만 전달 |

## 관련 파일

- `ad_monitor/_inputs/urls.md` — ★ 사용자가 편집하는 유일한 입력 파일
- `ad_monitor/_reference/analysis_method.md` — USP 3항목 + Creative Key Visual + ad_pattern 정의
- `ad_monitor/_scripts/fetch_ads.py` — Apify+Gemini 크롤·분석 메인 스크립트
- `ad_monitor/_scripts/utm_pattern.py` — UTM/트래킹 파라미터 추출 (관찰 데이터만, 규칙 확정 ❌)
- `ad_monitor/_scripts/build_dashboard.py` — 로컬 HTML 대시보드 빌드
- `ad_monitor/README.md` — 빠른 시작 가이드

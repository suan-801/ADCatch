# 02_competitor/_scripts — 경쟁사 광고 자동화 스크립트

## 파일

| 파일 | 용도 | 호출 |
|---|---|---|
| `competitor_inputs.py` | `_inputs/*.md` 시드 파서 + URL→슬러그 정규화 | (다른 스크립트가 import) |
| `fetch_competitor_ads.py` | Apify 광고 크롤 + Gemini 5단계 분석 + 통합 트렌드 리포트 | `python3 fetch_competitor_ads.py "<URL>"` (URL 직접) / `python3 fetch_competitor_ads.py [slug]` / `python3 fetch_competitor_ads.py [--max N] [--no-gemini] [--md-only] [--paid]` |
| `build_dashboard.py` | 정적 HTML 모니터링 대시보드 빌드 | `python3 build_dashboard.py [--no-copy]` |

## 빠른 시작 — URL 1개로 시작

```bash
export APIFY_TOKEN="apify_api_..."
export GEMINI_API_KEY="AQ..."   # 2026년 새 키는 AQ 로 시작 (옛 AIza 키는 9월 전까지만 동작)

python3 fetch_competitor_ads.py "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&view_all_page_id=123456789"
python3 build_dashboard.py
open ../dashboard/index.html
```

→ 첫 호출 시 Apify 응답의 `page_name` 으로 슬러그 자동 도출 + `_inputs/{slug}.md` 자동 생성. 다음 호출부터는 슬러그로도 재실행 가능.

## 환경 변수

```bash
export APIFY_TOKEN="apify_api_..."     # https://console.apify.com/settings/integrations

# Gemini 키 — 무료/유료 듀얼 키 지원 (택1)
export GEMINI_API_KEY_FREE="AQ..."   # 무료 티어 키 (결제 미연결, 250 RPD 한도) — 디폴트 사용
export GEMINI_API_KEY_PAID="AQ..."   # 유료 티어 키 — `--paid` 플래그 시 사용
export GEMINI_API_KEY="AQ..."        # 단일 키만 쓰는 경우 (둘 다 폴백)
```

**키 선택 우선순위**:
- 디폴트(무료): `GEMINI_API_KEY_FREE` > `GEMINI_API_KEY`
- `--paid` 플래그: `GEMINI_API_KEY_PAID` > `GEMINI_API_KEY`

**★ 키 형식 (2026년 새 정책)**: 새로 발급하는 Gemini 키는 `AIza` 가 아니라 **`AQ` 로 시작**합니다 (표준 키 → 인증 키 전환, 보안 강화). 예전에 받아둔 `AIza` 키는 2026년 9월 전까지만 동작하니 그 전에 새 키(`AQ`)로 교체하세요. 코드 수정은 불필요 — env 값 한 줄만 바꾸면 됩니다.

**무료 키 만들기**: AI Studio (https://aistudio.google.com/apikey) → "Create API key" → **결제 계정 연결 안 함** → 250 RPD 한도 안쪽이면 영구 0원. (새 키는 자동으로 인증 키 `AQ` 로 발급됩니다.)

## 사용 액터

- `curious_coder/facebook-ads-library-scraper` (Apify)
  - 1회 활성화 필요: https://apify.com/curious_coder/facebook-ads-library-scraper

## 의존성

표준 라이브러리만 사용 (urllib·json·pathlib). 별도 pip 설치 불필요.

## 실행 흐름

```
사용자 → Meta 광고 라이브러리 URL 1개
       ↓
fetch_competitor_ads.py "<URL>"
       ↓ Apify 액터 실행 → 광고 dataset 수신
       ↓ page_name → 슬러그 자동 도출 → _inputs/{slug}.md 자동 생성
       ↓ 미디어 다운로드 (이미지·영상)
       ↓ Gemini 5단계 분석 (문제·해결·근거·후킹·프로모션)
       ↓ 영상은 Gemini Files API 업로드 → 대본 + 5단계
       ↓
{slug}/ad-creatives/
  ├── metadata.json        # 광고 카드 원본 (Apify)
  ├── analysis.json        # 5단계 분석 (ad_id 별)
  └── images/, videos/

{slug}/ad-creatives.md     # 경쟁사별 1페이지 보고서
competitor_ads.md          # ★ 통합 트렌드 리포트 (모든 경쟁사 가로 비교)
       ↓
build_dashboard.py
       ↓ 모든 슬러그의 metadata + analysis 통합
       ↓ HTML + JSON + 미디어 사본
       ↓
dashboard/index.html      # 브라우저로 더블클릭
```

## 트러블슈팅

| 상황 | 대응 |
|---|---|
| Apify 액터 차단·실패 | URL 형식 점검 (Page ID 딥링크 권장) |
| 미디어 다운로드 실패 | `excluded_keys` 점검 — 페이지 표지·썸네일이 미디어로 잘못 저장될 때 |
| Gemini 무료 한도 초과 (429) | **자동 graceful 처리** — 한도 도달 광고는 `analysis.json` 에 `status: "quota_exceeded"` 저장, 부분 결과로 대시보드 빌드. 24시간 후 재실행하면 미분석 광고만 이어서 분석. 즉시 완료 필요 시 `--paid` 플래그로 유료 키 사용 |
| Gemini 분석 결과를 대시보드에서 식별 | 카드 우상단 배지 — 🟢 분석완료 / ⏸️ 분석대기 / 🚫 무료한도 / ❌ 분석실패 |
| 영상 대본 추출 실패 | 키프레임 멀티모달 분석으로 폴백 (대본 없이 5단계만) |
| 한글 파일명 문제 | python `subprocess.run([...])` 으로 ffmpeg 호출 (인자 배열) |

## 스크립트 추가·수정

- 표준 라이브러리·`competitor_inputs.py` 기반
- 새 액터 추가 시 `fetch_competitor_ads.py` 의 actor_id 만 교체
- 대시보드 컴포넌트 추가는 `build_dashboard.py` 의 HTML 템플릿 수정

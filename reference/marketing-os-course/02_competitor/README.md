# 02_competitor — 경쟁사 광고 분석

경쟁사의 Meta 광고 라이브러리 URL 을 입력으로 광고 크리에이티브를 자동 크롤링·분석.

## 시작하기

1. `_inputs/competitors.md` 에 경쟁사 Meta 광고 라이브러리 URL 한 줄씩 입력 (포맷은 `_inputs/README.md` 참조)
2. 스킬 호출:

```bash
/02-competitor-from-adlib
```

## 산출물

| 경로 | 용도 |
|---|---|
| `competitor_ads.md` | 1페이지 경쟁사 광고 통합 분석 (스킬이 자동 생성) |
| `{경쟁사-슬러그}/ad-creatives.md` | 경쟁사별 광고 크리에이티브 상세 |
| `{경쟁사-슬러그}/ad-creatives/` | 크롤링된 이미지·영상 원본 |
| `dashboard/` | 인터랙티브 HTML 대시보드 |

## 사전 준비

`.env` 의 `APIFY_TOKEN` 필요. 발급 방법은 루트 `SETUP_GUIDE.md` 참조.

> 본 폴더는 강의 2-2 (경쟁사 광고 분석) 의 산출물 저장소.

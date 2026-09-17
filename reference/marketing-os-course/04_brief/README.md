# 04_brief — 광고 브리프 (3C → USP 4축)

> 2-1·2-2·2-3 의 3C 분석 (자사·경쟁사·고객) 을 합성해 광고 시안 1장으로 가는 브리프를 보관하는 폴더.

## 파일 구조

```
04_brief/
├── README.md                     # 본 파일
├── confirmed_brief.md            # ★ /04-brief-synthesizer 자동 산출물 (05 분기 A 진입점)
├── brief_2026-05_v1.md           # planner 에이전트 산출물 (월간 안 1·2·3 비교)
└── archive/                      # 이전 캠페인 자동 백업
    └── {캠페인-슬러그}_brief.md
```

## 두 가지 흐름

### 1. 캠페인 1건 — `/04-brief-synthesizer`

- 인풋: 3C 분석 3 파일 (`01_brand/brand_brief.md` + `02_competitor/competitor_ads.md` + `03_customer/pain_points.md`)
- 산출: `confirmed_brief.md` 1 파일 (~120줄) — **컨셉 한 줄 + USP 4축 1세트 (① User's Pain Point · ② Solution · ③ Creative Key Visual · ④ Promotion(+CTA)) + 메시지 앵글 + 비주얼 시드**
- 다음: `/05-ad-image-nanobanana` 가 본 파일을 감지하면 **분기 A** 진입 → § 2~6 그대로 인용 → v1 PNG 생성
- 새 호출 시 기존 `confirmed_brief.md` 는 `archive/{기존-슬러그}_brief.md` 로 자동 백업

### 2. 월간·분기 전략 — `planner` 에이전트

- 인풋: 사용자의 월간 전략 요청 ("4월 결과 분석 + 5월 전략" 등)
- 산출: `brief_{캠페인}_{날짜}-v{N}.md` — **안 1·2·3 비교표 + 트레이드오프**
- 다음: 사용자 선택 → `copywriter` · `creator` · `analyst` 위임
- 본 흐름의 산출물은 archive 로 가지 않고 그대로 보존 (월간 영구 자료)

## 두 흐름의 차이

| 항목 | /04-brief-synthesizer | planner |
|---|---|---|
| 단위 | 캠페인 1건 (시안 1장) | 월간·분기 |
| 산출물 수 | 1장 (단일 권고) | 안 1·2·3 (선택 대기) |
| USP 4축 | 포함 (§ 3) | 미포함 (전략·KPI 중심) |
| 05 분기 A 진입 | ✅ (자동) | ❌ (전략 단계) |

## 분기 A vs 분기 B (05-ad-image-nanobanana)

- **분기 A** — `confirmed_brief.md` 존재 → § 2~6 그대로 인용. 도출 단계 스킵. 빠른 v1.
- **분기 B** — `confirmed_brief.md` 부재 (디폴트) → 3C 동적 로드 → `references/` 5 모듈로 in-memory 도출 → v1 생성

## 사용 예

```bash
# 1. 3C 분석 3 파일 준비 (없으면 먼저 채우기)
/01-brand-from-url https://{브랜드홈페이지-URL}
/02-competitor-from-adlib <Meta 광고라이브러리 URL>
/03-pain-from-reviews

# 2. 브리프 합성
/04-brief-synthesizer
# → 04_brief/confirmed_brief.md 자동 생성, § 3 USP 4축 채팅 동봉

# 3. 광고 이미지 생성 (분기 A 자동 진입)
/05-ad-image-nanobanana
# → 05_ad_image/{브랜드}_{캠페인}_meta-feed_conceptA-v1.png
```

## 디테일 회피 룰

- 페르소나·ICP 산출 ❌ (그건 customer-analyzer)
- 안 1·2·3 비교 ❌ (그건 planner)
- HTML 시안 컨펌 게이트 ❌ (04-storyboard-brief deprecated 사유 회피)
- 사후 검수 정책 유지 — 자동 생성 후 사용자가 자연어로 v2 요청

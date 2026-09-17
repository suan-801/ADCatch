# Performance Marketing OS — 수강생용 워크스페이스

> 클로드코드로 만드는 **심플한 퍼포먼스 마케팅 OS** 강의의 수강생용 시작 템플릿.
> 광고 소재 기획·제작·데이터 분석을 1페이지·1스킬 단위로 자동화합니다.

본 폴더는 **본인 브랜드로 처음부터 실습**할 수 있게 모든 결과물이 비워진 상태입니다.
폴더 구조·스킬·프롬프트·워크플로우는 그대로, 실제 분석 결과물만 비어있어요.

---

## 수강생 시작 가이드

```bash
# 1. (최초 1회) MCP·자격증명 셋업 — SETUP_GUIDE.md 참고
cp 09_tracking/.env.example 09_tracking/.env
# → .env 와 .mcp.json 의 `YOUR_*_HERE` 값을 본인 키로 교체
/09-tracking-setup     # 인터랙티브 셋업 안내

# 2. 이 폴더에서 클로드코드 실행
claude

# 3. 강의 순서대로 호출
/01-brand-from-url https://{내브랜드도메인}
/02-competitor-from-adlib <Meta 광고라이브러리 URL>
/03-pain-from-reviews
/04-brief-synthesizer
# → 04_brief/confirmed_brief.md 자동 합성 (3C → USP 4축)
/05-ad-image-nanobanana
# → 05_ad_image/*.png (v1 후 사후 검수 → v2)
```

자연어로도 호출 가능:
- "이 URL로 브랜드 분석해줘"
- "이 광고라이브러리 봐줘"
- "이 PDP 리뷰로 고객 분석"
- "브리프 만들어줘" / "광고 컨셉 도출해줘"
- "이미지 만들어줘" / "카드뉴스 만들어줘" / "랜딩페이지 만들어줘"

### 브랜드 에셋 먼저 채우기 (선택, 권장)

`01_brand/` 하위 2개 폴더에 자료를 넣어두면 04·05 결과물의 정확도가 크게 올라갑니다.
- `logos/` — 브랜드 로고 (벡터 + PNG 투명배경)
- `products/` — 제품 누끼·라이프스타일·매크로 샷

---

## 폴더 구조

```
Claudecode_MarketingOS_student/
├── README.md                  ← 이 파일
├── CLAUDE.md                  ← 클로드코드용 프로젝트 규칙
├── .mcp.json                  ← MCP 서버 설정 (NanoBanana)
│
├── 01_brand/                  ← URL → 브랜드 1페이지
│   ├── logos/                 (브랜드 로고 — 05 reference 로 첨부)
│   └── products/              (제품 누끼·라이프스타일 — 05 reference)
│
├── 02_competitor/             ← Meta 광고라이브러리 → 경쟁사 광고 1페이지
│   └── _inputs/competitors.md (사용자가 URL 입력)
│
├── 03_customer/               ← 경쟁사 리뷰 → 페인포인트 1페이지
│   ├── _inputs/reviews_pdp.md (사용자가 PDP URL 입력)
│   └── reviews/               (리뷰 원본 — URL이 막혔을 때 캡처·복붙 보관)
│
├── 04_brief/                  ← 3C → USP 4축 + 컨셉 자동 합성
│   └── (★ /04-brief-synthesizer 실행 시 confirmed_brief.md 자동 생성 — 05/07/08 진입점)
│
├── 05_ad_image/               ← 광고 이미지 (NanoBanana .png + copy/)
├── 06_ad_video/               ← 광고 영상 (Higgsfield .mp4 + movie_ref_frames/)
├── 07_carousel/               ← 카드뉴스 캐러셀 슬라이드 (NanoBanana)
├── 08_landing/                ← 랜딩페이지 (NanoBanana + HTML 단일 파일)
├── 09_tracking/               ← Meta·GA4·Clarity 트래킹 셋업
├── 10_daily/                  ← 일일 슬랙 리포트 ({brand}/{YYYY-MM-DD}-*.{txt,json})
├── 11_dashboard/              ← 대시보드·CRO·모니터링 (dashboards/, cro/, recommendations/, setup/)
├── 12_period/                 ← 기간 리포트 ({brand}/*.{md,html,pdf})
├── _shared/                   ← 공용 라이브러리 (scripts/, lib/, templates/, config/, data/, logs/)
│
└── .claude/
    ├── agents/                ← 직무별 에이전트 5명
    └── skills/                ← 스킬 12개 (강의 5~16강 매핑)
        ├── 01-brand-from-url/
        ├── 02-competitor-from-adlib/
        ├── 03-pain-from-reviews/
        ├── 04-brief-synthesizer/
        ├── 05-ad-image-nanobanana/
        ├── 06-ad-video-higgsfield/
        ├── 07-carousel-nanobanana/
        ├── 08-landing-page/
        ├── 09-tracking-setup/
        ├── 10-daily-slack/
        ├── 11-monitor/
        └── 12-period-report/
```

각 폴더 번호 = 워크플로우 순서. 위에서 아래로 진행하면 됩니다.

---

## 본인 브랜드로 채워나가는 법

1. **`/01-brand-from-url https://{내브랜드도메인}`** — URL 1개로 `01_brand/brand_brief.md` 자동 생성

2. **`02_competitor/_inputs/competitors.md`** 에 경쟁사 Meta 광고라이브러리 URL 추가 → **`/02-competitor-from-adlib`**

3. **`03_customer/_inputs/reviews_pdp.md`** 에 자사·경쟁사 PDP URL 추가 → **`/03-pain-from-reviews`**
   - 올리브영·자사몰·쿠팡 등 어디든 OK

4. **`/04-brief-synthesizer`** — 1·2·3 결과를 모아 USP 4축 + 컨셉 자동 합성

5. **`/05`·`/06`·`/07`·`/08`** — 이미지·영상·카드뉴스·랜딩페이지 v1 즉시 생성

---

## 사후 검수 정책 (★ 사전 컨펌 게이트 폐기)

이 OS의 핵심은 **v1 즉시 산출 → 사용자가 검수 → v2 반복** 흐름입니다.

- `/04-brief-synthesizer` 가 3C 분석을 모아 `04_brief/confirmed_brief.md` 1장을 자동 합성합니다.
- 05/07/08 스킬(이미지·카드뉴스·랜딩)은 그 브리프의 § 3 USP 4축을 그대로 인용해 **v1 즉시** 만들고, 채팅에 USP 4축·시나리오를 동봉합니다.
- 사용자는 v1 결과 보고 *"② 더 짧게"* 식으로 자연 반복 → v2 호출.

---

## MCP 의존성

`.mcp.json` 에 3개 서버가 등록되어 있습니다 — **모든 키 값은 `YOUR_*_HERE` 플레이스홀더**.
본인 키로 교체 방법은 `SETUP_GUIDE.md` 참고.

| MCP | 용도 | 필요 키 |
|---|---|---|
| `nanobanana` | 이미지 생성 (05·06·08·09) | `GEMINI_API_KEY` |
| `analytics-mcp` | GA4 데이터 (09 리포트) | `GOOGLE_PROJECT_ID` + gcloud ADC |
| `clarity` | UX 세션 분석 (09 리포트) | `CLARITY_API_TOKEN`, `CLARITY_PROJECT_ID` |

Higgsfield(영상)·Apify(경쟁사 크롤링) 등 슬래시 스킬·`.env` 의존 서비스는 `SETUP_GUIDE.md` 의 발급 절차를 따라가세요.

---

## 강의 후속 모듈

- **데이터 리포트** (`10_daily/·11_dashboard/·12_period/`) — 광고 집행 데이터(Meta·GA4 CSV) → 1페이지 리포트 자동화
- 별도 SKU 추가 운영, A/B 테스트 자동화, 캠페인 일별 리포트 등은 본 강의 후속 챕터에서 다룹니다.

---

*문의: 강의 페이지 또는 강사에게.*

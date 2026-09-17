# 03_customer/_inputs — 고객 분석 PDP URL 입력

> **빠른 시작 (Less is More):** `_inputs/reviews_pdp.md` 에 자사·경쟁사 PDP URL 만 한 줄씩 적어두면 됩니다. `/03-pain-from-reviews` 호출 시 스크립트가 이 파일만 읽고 자사 만족 포인트·경쟁사 페인포인트·트렌드 키워드를 통합 분석합니다.

## 입력 모드 (우선순위 순)

### Mode 1 — 통합 파일 `reviews_pdp.md` (★ 권장)

사용자가 편집하는 **유일한 파일**. 한 곳에서 자사·경쟁사 PDP 를 관리.

**파일:** `_inputs/reviews_pdp.md`

**포맷:**
```markdown
## 자사 PDP (만족 포인트·욕구 분석)
https://www.oliveyoung.co.kr/...goodsNo=A0000XXX   # {브랜드명} 글로우 카로틴 세럼

## 경쟁사 PDP (페인포인트 분석)
https://www.oliveyoung.co.kr/...goodsNo=A0000YYY   # 경쟁사 A 비건 광채 세럼 (직접경쟁)
https://www.oliveyoung.co.kr/...goodsNo=A0000ZZZ   # 닥터자르트 V7 (직접경쟁)

## 카테고리·트렌드 시드 (Perplexity 리서치용)
비건 카로틴 광채 세럼
30~40대 직장인 톤업 페인
```

**규칙:**
- URL 한 줄에 하나
- 헤딩 `## 자사 PDP` / `## 경쟁사 PDP` / `## 카테고리·트렌드 시드` 로 분류
- 올리브영 PDP URL → `oliveyoung_crawler.py` 4트랙 dedupe 자동 호출 (★ 디폴트 경로)
- 자사몰·쿠팡·네이버 → Playwright MCP 폴백
- URL 뒤 `# 메모` 는 brand/제품명 힌트로만 사용 (선택)
- 빈 줄·`#` 시작 일반 주석 라인은 무시
- URL 라인 맨 앞에 `#` 붙이면 일시 비활성화 (다음 실행 스킵)

**호출:**
```bash
# 인자 없이 — reviews_pdp.md 일괄 처리
/03-pain-from-reviews

# 또는 단발 — 한 PDP URL만 분석
/03-pain-from-reviews https://www.oliveyoung.co.kr/...goodsNo=A0000XXX
```

### Mode 2 — 단발 URL (Mode 1 무시)

reviews_pdp.md 안 건드리고 한 번만 분석하고 싶을 때.

```bash
/03-pain-from-reviews "https://www.oliveyoung.co.kr/store/goods/getGoodsDetail.do?goodsNo=A0000XXXXXXXX"
```

### Mode 3 — 폴더 인풋 (자사몰·시크릿몰 리뷰)

올리브영 PDP가 없거나 자사 자체 리뷰 자료가 있을 때:

```
03_customer/reviews/
├── our/                # 자사 리뷰 원본 (사용자 직접 드롭)
│   ├── 자사리뷰.md
│   ├── pdp-스크린샷.png
│   └── ...
└── competitor/         # 경쟁사 리뷰 원본 (사용자 직접 드롭)
```

스킬이 이미지·텍스트 모두 Read (멀티모달) 후 분석에 합산.

---

## 출력

호출하면 다음 산출물이 생성됩니다:

| 위치 | 내용 |
|---|---|
| `03_customer/pain_points.md` | ★ 최종 1페이지 — 페인 Top 5 + 욕구 Top 3 + 트렌드 키워드 + 페어링 3세트 |
| `2-3_customer_market_analysis/outputs/raw/<goodsNo>_<ts>.json` | 원본 리뷰 (자동) |
| `2-3_customer_market_analysis/outputs/raw/<goodsNo>_<ts>.csv` | 분석용 핵심 필드 (자동) |
| `2-3_customer_market_analysis/outputs/raw/<goodsNo>_<ts>_stats.json` | 모집단 통계 — 별점 분포·피부타입 만족도·자극도 % |

**캐시**: 동일 goodsNo 24시간 이내 데이터가 있으면 재호출 ❌, Read 우선.

---

## 입력 우선순위

같은 호출에서 여러 인풋이 동시에 있으면 다음 순서로 처리:

```
1. 명령어 인자 (URL 직접 전달) — Mode 2
2. _inputs/reviews_pdp.md — Mode 1 (디폴트)
3. 03_customer/reviews/{our,competitor}/ 폴더 파일 — Mode 3 (보조)
4. 01_brand/brand_brief.md 의 카테고리·USP 자동 추출 — 시드
```

→ 1·2·3 중 **1개 이상** 있으면 분석 가능. 3개 모두 있으면 가장 풍부한 통합 분석.

---

## 자주 묻는 질문

**Q. 자사 PDP가 아직 올영에 없으면?**
- 헤딩 `## 자사 PDP` 아래 URL 라인을 `#` 으로 비활성화하거나 자사몰 URL 만 남기세요. 자사 만족 포인트 축은 자사몰 Playwright 또는 폴더 인풋으로 자동 대체됩니다.

**Q. 경쟁사가 올영이 아닌 쿠팡·네이버이면?**
- 그대로 URL 적으시면 Playwright MCP 가 폴백으로 동작합니다. 다만 `oliveyoung_crawler.py` 의 4트랙 dedupe·RATING_ASC oversampling 같은 페인 농축 기능은 올영 PDP 한정.

**Q. Perplexity 트렌드 리서치는 자동 실행되나요?**
- 네. `## 카테고리·트렌드 시드` 섹션에 카테고리·키워드를 적어두면 1쿼리 자동 호출. 비워두면 `01_brand/brand_brief.md` 의 카테고리·USP 키워드를 자동 추출해 사용.

**Q. 동일 goodsNo 를 다시 분석하려면?**
- 24시간 이내 캐시는 자동 재사용. 강제 재크롤이 필요하면 `outputs/raw/<goodsNo>_*.{json,csv,stats.json}` 파일을 삭제 후 재실행.

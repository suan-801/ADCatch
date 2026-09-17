# 02_competitor/_inputs — 경쟁사 입력

> **빠른 시작 (Less is More):** `_inputs/competitors.md` 에 Meta 광고 라이브러리 URL 만 한 줄씩 적어두면 됩니다. `/02-competitor-from-adlib` 호출 시 스크립트가 이 파일만 읽고 경쟁사별 폴더·분석·대시보드를 자동 생성합니다.

## 입력 모드 3가지 (우선순위 순)

### Mode 1 — 통합 파일 `competitors.md` (★ 권장)

사용자가 편집하는 **유일한 파일**. 한 곳에서 모든 경쟁사를 관리.

**파일:** `_inputs/competitors.md`

**포맷:**
```markdown
## 직접경쟁
https://www.facebook.com/ads/library/?...&view_all_page_id=111   # 경쟁사A
https://www.facebook.com/ads/library/?...&view_all_page_id=222   # 경쟁사B

## 간접경쟁
https://www.facebook.com/ads/library/?...&view_all_page_id=333   # 경쟁사C
```

**규칙:**
- URL 한 줄에 하나
- 헤딩 `## 직접경쟁` / `## 간접경쟁` 은 classification 으로 자동 매핑
- URL 뒤 `# 메모` 는 `brand_name_kr` 힌트로만 사용 (선택)
- URL 라인 맨 앞에 `#` 붙이면 비활성화 (다음 실행 스킵)
- 슬러그(폴더명)는 Apify 응답의 `page_name` 으로 자동 도출

**호출:**
```bash
python3 _scripts/fetch_competitor_ads.py
```

### Mode 2 — URL 직접 던지기 (단발 추가)

```bash
python3 _scripts/fetch_competitor_ads.py "https://www.facebook.com/ads/library/?...&view_all_page_id=123"
```

스크립트가 `page_name` 으로 슬러그를 자동 생성하고 `_inputs/{slug}.md` 도 자동 작성. `competitors.md` 는 안 건드림.

### Mode 3 — 슬러그 단일 갱신 (옛 방식 호환)

```bash
python3 _scripts/fetch_competitor_ads.py medicube
```

`_inputs/medicube.md` 를 읽어 그 한 곳만 재크롤. 통합 파일과 별개로 작동.

## URL 종류 — Page ID 기반 권장

✅ **Page ID 딥링크 (권장)** — 특정 페이스북 페이지의 광고만 노출, 정확도 높음
```
facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&view_all_page_id={PAGE_ID}
```

⚠️ **검색 쿼리 URL** — 동명·유사 브랜드, 광고에 브랜드명을 멘션한 무관 광고주까지 섞임
```
facebook.com/ads/library/?q={브랜드명}
```

⚠️ **모기업 단위 페이지 주의** — 한 페이지에 여러 브랜드 광고 운영 . `competitors.md` 의 `# 메모` 에 명시하면 이후 분석에서 참고됨.

## Page ID 찾는 법

1. Meta 광고 라이브러리 검색 → 광고주 클릭
2. URL 에서 `view_all_page_id={숫자}` 부분 복사
3. `competitors.md` 에 새 줄로 추가

## 자동 생성되는 per-slug 시드 (참고)

스크립트가 URL 을 처음 처리할 때 `_inputs/{slug}.md` 를 자동 생성합니다 (Mode 1·2 공통). 이는 **추적·이력용** 이며, 사용자가 직접 편집하지 않아도 됩니다.

자동 생성된 시드의 양식:

```markdown
---
competitor_slug: medicube              # page_name 에서 자동 도출
brand_name_kr: 캐롯글로우                # competitors.md 메모 힌트 또는 page_name
brand_name_en: Medicube
classification: 직접경쟁                # competitors.md 헤딩에서 상속
status: active
---

## Meta Ad Library
https://www.facebook.com/ads/library/?...&view_all_page_id={PAGE_ID}

## Notes
(자동 생성 — competitors.md 의 메모 또는 분석 시 메타)
```

## 새 경쟁사 추가 워크플로우

```
1. competitors.md 열기
2. ## 직접경쟁 (또는 간접경쟁) 헤딩 아래에 URL 한 줄 추가
3. (선택) URL 뒤 `# 메모` 추가
4. 저장
5. /02-competitor-from-adlib 호출 — 끝
```

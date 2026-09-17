# _inputs/ 사용법

## 기본 (통합 파일) — `urls.md`

한 파일에 URL 을 한 줄씩 적으면 끝. `##` 헤딩은 자유 그룹 라벨 (생략 가능, 분류 강제 ❌).

```markdown
## 자사
https://www.facebook.com/ads/library/?...&view_all_page_id=111   # 메모

## 관찰 대상
https://www.facebook.com/ads/library/?...&view_all_page_id=222   # 메모
```

```bash
python3 ad_monitor/_scripts/fetch_ads.py
```

- URL 앞에 `#` 를 붙이면 다음 실행에서 스킵 (비활성화)
- 첫 실행 시 Apify 응답의 `page_name` 으로 슬러그를 자동 도출해 `_inputs/{slug}.md` 시드 파일을 자동 생성 (추적용, 편집 불필요)

## 단발 URL (urls.md 안 건드림)

```bash
python3 ad_monitor/_scripts/fetch_ads.py "https://www.facebook.com/ads/library/?...&view_all_page_id=123"
```

## 개별 시드 파일 (`{slug}.md`) — 보통 직접 편집할 필요 없음

자동 생성되며, 필요하면 아래 형식으로 수동 편집도 가능:

```markdown
---
brand_slug: my-brand
brand_name_kr: 마이 브랜드
brand_name_en: MyBrand
product_name_kr:
group: 자사
status: active
---

## Meta Ad Library
https://www.facebook.com/ads/library/?...&view_all_page_id=123

## Notes
메모
```

`status: paused` 로 설정하면 일괄 실행에서 제외됩니다.

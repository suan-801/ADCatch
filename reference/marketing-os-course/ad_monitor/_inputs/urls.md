# 광고 모니터링 URL 목록 (ad-monitor 독립 스킬)

> 자사·경쟁사 구분 없이, 보고 싶은 Meta 광고 라이브러리 URL 을 한 줄씩 추가하세요.
> URL 한 줄 추가 → `python3 ad_monitor/_scripts/fetch_ads.py` 실행 → 끝.
>
> `##` 헤딩은 자유 텍스트 그룹 라벨입니다 (분류 강제 ❌ — "자사"/"경쟁사"/"관찰 대상 A" 등 원하는 대로).
> URL 라인 맨 앞에 `#` 를 붙이면 비활성화(다음 실행 스킵)됩니다.
> 아래는 작성 예시(샘플)입니다. 실제 URL로 교체해 사용하세요.

## 자사

https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=000000000000000
# 우리 브랜드 — 최근 캠페인 크리에이티브 확인용

## 관찰 대상

https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=KR&is_targeted_country=false&media_type=all&search_type=page&sort_data[direction]=desc&sort_data[mode]=total_impressions&view_all_page_id=111111111111111
# 관찰 대상 A — 메모는 자유롭게

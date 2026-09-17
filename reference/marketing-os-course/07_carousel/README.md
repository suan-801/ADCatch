# 07_carousel — 인스타 카드뉴스

NanoBanana 로 5축 시각 일관성을 강제한 캐러셀(카드뉴스) 슬라이드 생성.

## 시작하기

`01_brand/`, `02_competitor/`, `03_customer/` 분석이 끝난 상태에서:

```bash
/07-carousel-nanobanana
```

> 사용자가 컨셉을 자연어로 지시하면 스킬이 자동으로 N장 슬라이드를 생성하고, v1 후 시나리오를 채팅에 동봉.

## 산출물 구조

```
07_carousel/
└── {토픽-슬러그}/
    ├── {브랜드}_{캠페인}_carousel-v1_slide01.png
    ├── {브랜드}_{캠페인}_carousel-v1_slide02.png
    └── ...
```

- 토픽 슬러그: 영소문자 + 하이픈 (예: `4week-challenge`, `glow-tips`)
- 수정 요청 시 `v2`, `v3` 으로 버전 증가 (덮어쓰기 ❌)

> 본 폴더는 강의 3-3 (카드뉴스) 의 산출물 저장소.

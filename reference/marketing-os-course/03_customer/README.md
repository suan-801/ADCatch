# 03_customer — 고객 페인포인트 분석

자사·경쟁사 PDP 리뷰에서 고객의 페인·욕구 시그널을 추출.

## 시작하기

1. `_inputs/reviews_pdp.md` 에 자사·경쟁사 PDP URL 입력 (포맷은 `_inputs/README.md` 참조)
2. 스킬 호출:

```bash
/03-pain-from-reviews
```

## 산출물

| 경로 | 용도 |
|---|---|
| `pain_points.md` | 1페이지 페인포인트 분석 (Set A/B 페어링 포함) |
| `reviews/our/` | 자사 리뷰 원본 (URL 크롤링 실패 시 수동 저장) |
| `visuals/` | 워드클라우드·시각화 자료 (`build_wordcloud.py` 실행) |

> 본 폴더는 강의 2-3 (고객 페인 분석) 의 산출물 저장소.

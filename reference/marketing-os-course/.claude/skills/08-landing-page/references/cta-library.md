# CTA Library — LP 버튼 카피·스타일

> SKILL Step 1.5 의 CTA 카피 선택, Step 3 의 버튼 HTML 마크업에서 1순위 인용.
> **모든 CTA 는 구글폼/Tally 등 외부 URL 로의 `<a>` 링크** — `<form>` 마크업 ❌, JS 검증 ❌, 결제 시스템 ❌.

---

## 1. 페이지 타입별 CTA 카피 풀

### 1-1. 체험단 모집 LP

| 위치 | 1차 추천 | 대안 1 | 대안 2 | 보조 카피 (버튼 아래) |
|---|---|---|---|---|
| **Hero CTA** | 지금 신청하기 | 체험단 신청 | 50명에 들기 | 모집 마감 D-N · 잔여 N명 |
| **중간 CTA** | 1분만에 신청하기 | 체험단 합류하기 | — | 신청서 1분 소요 |
| **Final CTA** | 지금 신청하기 | 마지막 N명에 합류 | — | 모집 마감 D-N |

### 1-2. 이벤트 / 프로모션 LP

| 위치 | 1차 추천 | 대안 1 | 대안 2 | 보조 카피 |
|---|---|---|---|---|
| **Hero CTA** | 혜택 받으러 가기 | 이벤트 참여하기 | 1+1 받기 | 이벤트 마감 D-N |
| **중간 CTA** | 자세히 보기 | 혜택 확인하기 | — | 진행 방법 1분 안내 |
| **Final CTA** | 지금 참여하기 | 혜택 받기 | — | D-N · 자정 종료 |

### 1-3. 단일 상품 LP

| 위치 | 1차 추천 | 대안 1 | 대안 2 | 보조 카피 |
|---|---|---|---|---|
| **Hero CTA** | 자세히 보기 | 구매하러 가기 | 사전 등록 | — |
| **중간 CTA** | 후기 확인하기 | 상세 페이지로 | — | 리뷰 N건 |
| **Final CTA** | 구매하러 가기 | 자세히 보기 | — | — |

---

## 2. CTA 작성 원칙

✅
- **혜택과 묶기** — "신청하기" 보다 "체험단 신청하기" / "혜택 받으러 가기"
- **행동 동사** — 받기 / 참여 / 신청 / 보기 / 합류 / 등록
- **10자 이내** — 버튼 안에서 줄바꿈 없이 한 줄
- **자릿수 표시** — 보조 카피에 "D-N", "잔여 N명", "선착순 N명" — 정량으로 긴급성 (가짜 카운트다운 타이머 ❌)

❌
- **제너릭** — "클릭", "더보기" 단독 (혜택 문맥 없음)
- **광고 의무 표현 누락** — 가격·할인 표기 시 "표시 가격은 부가세 포함" 등 (있으면) 보조 카피에
- **이중 CTA 충돌** — 같은 섹션에 다른 외부 URL 2개 ❌. 한 페이지에 신청 URL 1개로 통일

---

## 3. 버튼 HTML / CSS 표준

### Primary CTA (Hero·Final)
```html
<a class="btn-primary" href="{사용자 제공 URL}" target="_blank" rel="noopener noreferrer">
  지금 신청하기
</a>
```
```css
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 18px 36px;
  font-family: var(--font-body);
  font-size: 17px;
  font-weight: 600;
  letter-spacing: -0.3px;
  color: var(--bg-light);
  background: var(--brand-sig);
  border-radius: 100px;          /* pill */
  text-decoration: none;
  transition: transform .3s var(--ease), box-shadow .3s var(--ease);
  box-shadow: 0 8px 24px rgba(0,0,0,0.12);
}
.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 32px rgba(0,0,0,0.18);
}
.btn-primary::after {
  content: '→';
  font-weight: 400;
}
```

### Secondary CTA (중간)
```html
<a class="btn-ghost" href="..." target="_blank" rel="noopener noreferrer">
  자세히 보기
</a>
```
```css
.btn-ghost {
  display: inline-flex;
  padding: 14px 28px;
  color: var(--brand-sig);
  background: transparent;
  border: 1.5px solid var(--brand-sig);
  border-radius: 100px;
  font-weight: 500;
}
```

### 보조 카피 (버튼 아래)
```html
<p class="btn-meta">모집 마감 D-3 · 잔여 12명</p>
```
```css
.btn-meta {
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-sub);
  letter-spacing: 0.3px;
}
```

### 터치 타겟
- 최소 44px 높이 (모바일 가이드)
- 모바일 (`@media (max-width: 600px)`): primary CTA `width: 100%; max-width: 320px;` 풀폭

---

## 4. CTA 위치·빈도

페이지 타입별 권장 CTA 위치 수:

| 페이지 타입 | Hero | 중간 | Final | 총 |
|---|---|---|---|---|
| 체험단 모집 | ✅ | 1 (How-it-works 직후) | ✅ | 3개 |
| 이벤트 | ✅ | 0~1 (혜택 카드 직후) | ✅ | 2~3개 |
| 단일 LP | ✅ | 1 (사회증거 직후) | ✅ | 3개 |

- 모두 동일한 외부 URL 로 연결
- 페이지 스크롤 길이가 짧으면 (단일 화면 hero+CTA) Final 만 1개로 충분

---

## 5. URL 미수령 시 fallback

사용자가 신청 URL 을 안 알려줬을 때:

```html
<a class="btn-primary" href="#" data-cta-pending="true">
  지금 신청하기
</a>
```

+ 채팅 보고 시 명시:
> ⚠️ 신청 CTA URL 이 placeholder (`#`) 입니다. 구글폼/Tally 링크를 1줄로 알려주시면 v2 에 반영합니다.

---
name: 01-brand-from-url
description: 브랜드 홈페이지 + 대표 상세페이지 URL을 받아 광고 소재 제작에 필요한 정보(USP·타겟·톤·비주얼·가격·프로모션)만 추려 `01_brand/brand_brief.md` 1페이지로 저장하는 스킬. 사용자가 "브랜드 분석해줘", "내 브랜드 URL 분석", "/01-brand-from-url <URL>" 등으로 요청할 때 호출. **★ 비주얼 섹션의 컬러 팔레트 6슬롯 표는 의무 산출물** — 05 광고 이미지 스킬이 그대로 인용. WebFetch 로 컬러·폰트가 안 잡히면 Playwright MCP 로 스크린샷 + computed styles 직접 추출. **★ 한국 D2C 자사몰(카페24·아임웹·메이크샵)은 PDP 상세 본문 마케팅 카피·USP·임상 자산이 거의 100% 이미지(.jpg)로 들어가 있으므로 curl 다운로드 + Claude vision OCR (§ Step 2.5) 필수** — 이 단계 누락 시 시그니처 컬러·메인 카피·자사 IP 모두 놓침.
---

# 01. 브랜드 분석 (URL → 1페이지)

## 언제 호출되는가

- "브랜드 분석해줘"
- "내 사이트 URL 분석해줘"
- "/01-brand-from-url https://example.com"
- 워크스페이스 첫 진입 시 (브랜드 브리프가 없을 때)

## 인풋

- **필수**: 대표 제품 상세페이지 (PDP) URL **1개** — 시그니처 컬러·폰트·강조 톤·USP·임상 자산이 가장 정확하게 잡힘
- **옵션**: 브랜드 홈페이지·자사몰 메인 URL (라인업 전체 시야·헤로 슬로건이 필요할 때만)
- **옵션**: 시크릿몰·랜딩페이지 추가 URL (시크릿몰만 보면 본 브랜드 톤과 다를 수 있음)

## 아웃풋

- `01_brand/brand_brief.md` 1개 (덮어쓰기. 기존 파일 있으면 백업 후 갱신)
- **★ 의무**: § 비주얼 의 6슬롯 컬러 팔레트 표 + 사용 OK/❌ 컬러 + 요소별 매핑

## 작업 순서

### Step 1. URL Fetch

- `WebFetch` 로 다음 순서로 로드:
  1. **대표 제품 상세페이지 (PDP)** — 시그니처 컬러·메인 카피·USP·임상 자산 추출의 1순위 (필수, 유일 입력)
  2. 브랜드 홈페이지·자사몰 메인 (사용자가 추가 URL 제공 시만 — 라인업 전체 시야·헤로 슬로건 보강용)
  3. 시크릿몰·랜딩페이지 (있을 때, 별도 톤일 수 있음 — 본 브랜드와 구분 표기)

### Step 2. 컬러·폰트 정밀 추출 (★ Playwright 분기)

WebFetch 만으로 컬러 HEX·폰트가 안 잡히는 경우 (텍스트만 추출되고 시각 정보 손실) → **Playwright MCP** 로 분기:

```
mcp__playwright__browser_navigate(url)
mcp__playwright__browser_take_screenshot(fullPage=true) → 시각 톤·강조 컬러 직접 관찰
mcp__playwright__browser_evaluate(`
  // computed styles 직접 추출
  const sample = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const cs = getComputedStyle(el);
    return { color: cs.color, bg: cs.backgroundColor, font: cs.fontFamily };
  };
  return {
    body: sample('body'),
    h1: sample('h1, h2'),
    cta: sample('button, a.btn, [class*="buy"], [class*="cart"]'),
    accent: sample('[class*="point"], [class*="highlight"], strong, em'),
  };
`)
```

> ⚠️ Playwright 호출 시 `.mcp.json` 에 playwright 서버 설정 필요. 미설치 시 사용자에게 알리고 WebFetch 결과만으로 진행 + § 비주얼 슬롯에 `[확인 필요]` 라벨 명시.

### Step 2.5. ★ PDP 상세 본문 이미지 OCR (한국 D2C 자사몰 필수)

한국 D2C 자사몰(카페24·메이크샵·아임웹·고도몰)의 PDP는 **상세설명 본문이 거의 100% 이미지(.jpg)로 들어간다** — 마케팅 카피·USP·헤로 메시지·임상 차트·신뢰 자산이 모두 이미지 안에 있어 WebFetch/Playwright `evaluate` 만으로는 추출 ❌. 본 단계를 건너뛰면 브랜드 톤·USP·시그니처 컬러를 100% 놓친다.

> **일반 패턴 (실측 검증)**:
> - HTML/CSS 만 분석 시: 시그니처 컬러 = 자사몰 템플릿 (카페24 등) 디폴트 톤 (CTA 버튼 차콜 류), USP = 의무 표기만, 헤로 카피 = 0건
> - Step 2.5 OCR 추가 시: 시그니처 컬러 = **실제 본문 헤드라인 톤**, USP = **자사 독자 기술명 + 임상 출처**, 헤로 카피 = **10+ 건 실측**
> - **Step 2.5 없으면 광고 시안이 자사몰 템플릿 디폴트 톤으로 만들어짐**.

#### 2.5-1. ★ "상품설명 더보기" 펼치기 + 상세 본문 이미지 URL 수집

> ⚠️ **핵심 함정 (한국 쇼핑몰 공통)**: PDP 상세설명 본문이 **기본 접힘** 상태로 렌더링됨. "상품설명 더보기" / "상세설명 펼쳐보기" 류 버튼을 클릭하지 않으면 본문 이미지(`<img>`) 가 ① DOM 미삽입 또는 ② `display:none` / `max-height:0` 으로 숨김. 단순 스크롤만으로는 **시그니처 컬러·메인 카피·USP·임상 자산을 통째로 누락**.
>
> **실측 효과**: 펼치기 ❌ = 본문 이미지 ~5장 / 펼치기 ✅ = 본문 이미지 12+ 장 (시그니처 카피·임상 차트 포함). 카페24·아임웹·메이크샵·고도몰·쿠팡 동일 패턴.

Playwright 로 **4단계 콤보** 실행 — ① 더보기 버튼 자동 클릭 → ② CSS truncate 강제 해제 → ③ 풀스크롤 lazy load → ④ 큰 이미지 수집:

```javascript
mcp__playwright__browser_evaluate(`async () => {
  // ① "더보기"/"펼쳐보기" 류 버튼 자동 클릭
  //   ★ 안전 룰: 반드시 **복합 키워드** (상세/상품설명/상품정보 + 더보기/펼치기) 만 매칭.
  //              단독 '더보기'·'전체보기' 는 ❌ — 일부 쇼핑몰의 장바구니·관련 상품 버튼이 navigation 유발 (실측 검증됨).
  //   ★ 추가 안전 룰: header·nav·gnb·cart·basket·top 영역 자식 요소는 클릭 제외.
  const expandKw = ['상품설명 더보기','상세설명 더보기','상세설명 펼쳐보기','상품 상세설명 더보기','상품정보 펼쳐보기','상세정보 펼쳐보기','상세정보 더보기','상품정보 더보기','상세 더보기','상세 펼쳐보기','상세설명 펼치기','상세 펼치기','본문 더보기','스토어 정보 펼쳐보기','상품정보제공고시 더보기','정보 더보기','자세히 보기'];
  const collapseKw = ['접기','닫기','숨기기'];
  const dangerZoneRe = /header|nav|gnb|lnb|topbar|cart|basket|footer|tab-nav|swiper/i;
  const clicked = [];
  const candidates = Array.from(document.querySelectorAll('button, a, [role="button"], [class*="more"], [class*="expand"]'));
  for (const el of candidates) {
    const text = (el.textContent || el.innerText || '').trim();
    if (!text || text.length > 30) continue;
    const isExpand = expandKw.some(kw => text.includes(kw));
    const isCollapse = collapseKw.some(kw => text.includes(kw));
    if (!isExpand || isCollapse) continue;
    // 위험 영역(header·nav·cart 등) 자식이면 skip
    let inDanger = false;
    for (let p = el; p && p !== document.body; p = p.parentElement) {
      const cls = (p.className && typeof p.className === 'string') ? p.className : '';
      const id = p.id || '';
      if (dangerZoneRe.test(cls) || dangerZoneRe.test(id) || /HEADER|NAV|FOOTER/.test(p.tagName)) { inDanger = true; break; }
    }
    if (inDanger) continue;
    try {
      el.scrollIntoView({behavior: 'instant', block: 'center'});
      await new Promise(r => setTimeout(r, 200));
      el.click();
      clicked.push(text);
      await new Promise(r => setTimeout(r, 600));
      // navigation 발생 시 즉시 중단
      if (location.pathname !== window.__initialPath) break;
    } catch (e) {}
  }
  // ② CSS truncate 강제 해제 (max-height·display:none 우회)
  document.querySelectorAll('.collapsed, .truncated, [class*="hide"], [class*="ellipsis"], [class*="goods-detail"], [class*="more-content"]').forEach(el => {
    el.style.maxHeight = 'none';
    el.style.height = 'auto';
    el.style.overflow = 'visible';
    el.classList.remove('collapsed','truncated','is-hide','hide');
  });
  // ③ 풀스크롤 → lazy load 트리거 (펼친 본문 포함 새 높이 기준)
  await new Promise(r => setTimeout(r, 500));
  const finalH = document.body.scrollHeight;
  for (let y = 0; y < finalH; y += 500) {
    window.scrollTo(0, y);
    await new Promise(r => setTimeout(r, 150));
  }
  window.scrollTo(0, 0);
  await new Promise(r => setTimeout(r, 500));
  // ④ 큰 이미지(naturalWidth >= 500) URL 수집
  return {
    expandedButtons: clicked,
    finalHeight: document.body.scrollHeight,
    images: Array.from(document.querySelectorAll('img'))
      .filter(img => img.naturalWidth >= 500)
      .map(img => ({ src: img.src, alt: img.alt, w: img.naturalWidth, h: img.naturalHeight }))
  };
}`)
```

**자체 점검**: 결과의 `expandedButtons` 가 비었거나 이미지 5장 이하면 → 비표준 패턴. 폴백 2단계:
1. `mcp__playwright__browser_click` 으로 "상품설명 더보기" / "더보기" 텍스트를 직접 클릭 후 위 evaluate 재호출
2. 그래도 안 되면 본문이 iframe·shadow DOM 안일 가능성 → 페이지 HTML 에서 `<iframe>` URL 찾아 별도 navigate 후 재시도

#### 2.5-1b. ★ 몰별 어댑터 + iframe 자동 진입 (L2)

> ⚠️ **핵심 함정 (몰별 패턴 2종)**:
> 1. **iframe 패턴** (일부 카페24 템플릿·구형 메이크샵): 본문이 별도 `<iframe>` 안 → 부모 DOM 만 보면 본문 0장 → `browser_navigate` 로 iframe URL 진입 후 콤보 재실행
> 2. **lazy mount 패턴** (네이버 스마트스토어 — 실측 확인): 본문이 iframe 이 아니라 부모 DOM 안에 있지만 **`상품정보 펼쳐보기` 클릭 전까지 본문 거대 이미지가 lazy mount 안 됨**. expandKw 에 키워드 들어있으면 자동 트리거됨
>
> **실측 (네이버 스마트스토어 일반 패턴)**: `상품정보 펼쳐보기` 키워드 없으면 본문 1장도 못 잡음 / 키워드 포함 시 **거대 본문 이미지 (22,000px+) 1장 추출 성공**. iframe 미사용 (gnb 메뉴 iframe 만 존재, 본문 iframe 0개 — DOM lazy mount 패턴).

##### 몰 식별 + iframe 후보 탐지 (Playwright evaluate)

```javascript
mcp__playwright__browser_evaluate(`() => {
  const url = location.href;
  const html = document.documentElement.innerHTML;
  let mall = 'generic';
  if (/coupang\\.com/.test(url)) mall = 'coupang';
  else if (/brand\\.naver\\.com|smartstore\\.naver\\.com/.test(url)) mall = 'naver';
  else if (/oliveyoung\\.co\\.kr/.test(url)) mall = 'oliveyoung';
  else if (/musinsa\\.com/.test(url)) mall = 'musinsa';
  else if (/imweb\\.me/.test(html)) mall = 'imweb';
  else if (/cdn-nhncommerce|godomall/.test(html)) mall = 'nhn';
  else if (/cafe24|xans-product-detail/.test(html)) mall = 'cafe24';
  // 본문 iframe 후보 (src·id·name 에 detail/content/description/info/product/item/story 포함)
  const iframes = Array.from(document.querySelectorAll('iframe'))
    .filter(f => f.src && f.offsetHeight > 200)
    .map(f => ({
      src: f.src,
      id: f.id || '',
      name: f.name || '',
      cls: (typeof f.className === 'string' ? f.className : '').substring(0, 60),
      w: f.offsetWidth, h: f.offsetHeight
    }))
    .filter(f => /detail|content|description|info|product|item|story|html/i.test(f.src + ' ' + f.id + ' ' + f.name));
  return { mall, url, iframes };
}`)
```

##### iframe 후보 발견 시 → 별도 navigate + 콤보 재실행

```javascript
// 결과의 iframes[0].src 로 별도 navigate
mcp__playwright__browser_navigate(iframes[0].src)
// → 2.5-1 의 4단계 콤보 evaluate 재호출 (펼치기·CSS 해제·풀스크롤·이미지 수집)
```

##### 몰별 통합 fingerprint (v2 확장)

| 몰 | 호스트·식별 패턴 | 더보기 패턴 | 본문 위치 | 본문 이미지 도메인 |
|---|---|---|---|---|
| **쿠팡** | `coupang.com` | `상품정보 더보기`, `자세히 보기` | 본문 div | `coupangcdn.com/.../retail/images/...` |
| **네이버 스마트스토어** | `brand.naver.com`, `smartstore.naver.com` | **`상품정보 펼쳐보기`** (본문 lazy mount 트리거), `자세히 보기` | **★ lazy mount** (iframe ❌). 클릭 후 본문 거대 이미지 출현 | `shop-phinf.pstatic.net/.../JPEG/{filename}_1000.jpg` (단일 거대 이미지 22,000px+) |
| **올리브영** | `oliveyoung.co.kr` | `상품설명 더보기` | div display:none + dynamic mount | `image.oliveyoung.co.kr/cfimages/...` |
| **카페24** | `cafe24`, `xans-product-detail` 클래스 | `상세설명 더보기`, `상세정보 펼쳐보기`, `상품 상세설명 더보기` | `.xans-product-detail` truncate | `/web/upload/NNEditor/...`, `/web/product/big/...` |
| **NHN Commerce (godomall)** | `*.cdn-nhncommerce.com`, `godomall.speedycdn.net` | ❌ (기본 펼침) | 그대로 노출 | `img.{brand}.co.kr/page/{date}_{lineup}/...`, `godomall.speedycdn.net/.../goods/{id}/image/detail/...` |
| **아임웹** | `imweb.me` | `더보기` (위험 — manual click only) | div max-height | `cdn.imweb.me/...`, `/_file/...` |
| **메이크샵** | makeshop | `상세설명 더보기` | 본문 truncate | `/shopimages/{shopid}/...` |
| **고도몰** | `godo.co.kr` | `상세설명 보기` | `.goods_detail` | `/data/editor/...` |
| **무신사** | `musinsa.com` | `상품 정보 더보기` | accordion | `image.msscdn.net/...` |
| **11번가** | `11st.co.kr` | `전체보기` (위험 — manual click only) | tab section lazy | `cdn.011st.com/...` |

#### 2.5-2. ★ 본문 이미지 전수 다운로드 (curl, 선택 다운로드 ❌)

> ⚠️ **선택 다운로드 금지**: 수집된 본문 도메인 이미지를 **전부** 다운로드. 어느 청크에 핵심 USP·임상·시그니처 카피가 있을지 사전에 알 수 없음.
>
> **실측 (K-뷰티 자사몰 PDP 일반 패턴)**: 본문 14장 중 5장만 선택 OCR 시 → 9장 누락 → 시리즈 라인업·다중 어워드·임상 출처 미발견 위험. **전수 다운로드 = 전수 OCR 의 전제**.

##### URL 사전 정리 (본문 도메인 우선 필터 + 파일명 끝 번호 정렬)

다운로드 직전, 2.5-1 evaluate 결과의 `images` 배열을 **본문 도메인 패턴으로 필터링 + 파일명 끝 번호 순 정렬** → 리뷰 썸네일·관련 상품·푸터 배너 등 노이즈 제거 + 위→아래 순서 보장.

```javascript
// 부모 페이지 evaluate 또는 결과 후처리 단계에서 가공
const bodyDomainRe = /img\.[^/]+\.co\.kr\/page\/|shop-phinf\.pstatic\.net\/.*JPEG\/|coupangcdn\.com\/.*\/retail\/|image\.oliveyoung\.co\.kr\/cfimages\/|cdn-nhncommerce\.com|godomall\.speedycdn\.net\/.*\/goods\/|web\/upload\/NNEditor\/|cdn\.imweb\.me\//;
const bodyUrls = images
  .filter(img => bodyDomainRe.test(img.src) && img.h >= 300)  // ★ 본문 = 세로 긴 이미지
  .sort((a, b) => {
    // 파일명 끝 _NN.{jpg|gif|png|webp} 패턴에서 숫자 추출 → 위→아래 정렬
    const numA = parseInt((a.src.match(/_(\d+)\.(jpg|jpeg|png|gif|webp)/i) || [,'0'])[1]);
    const numB = parseInt((b.src.match(/_(\d+)\.(jpg|jpeg|png|gif|webp)/i) || [,'0'])[1]);
    return numA - numB;
  })
  .map(img => img.src);
console.log(`본문 도메인 ${bodyUrls.length}장 (정렬 완료)`);
```

> ⚠️ **bodyUrls.length === 0 이면** → 본문 미발견 → 2.5-1b iframe 진입 재시도 → 그래도 0이면 2.5-8 풀페이지 스크린샷 폴백 트리거.

##### curl 일괄 다운로드

```bash
mkdir -p 01_brand/_source/pdp-images
# 수집된 본문 URL 배열을 모두 순회 (선택 ❌, 전수 ✅, JPG·PNG·GIF·WebP 모두)
for i in "${!URLS[@]}"; do
  idx=$(printf "%02d" $((i+1)))
  url="${URLS[$i]}"
  # 확장자 보존 (gif·webp 인 경우 그대로 다운로드 — 다음 단계에서 JPG 변환)
  ext=$(echo "$url" | grep -oE '\.(jpg|jpeg|png|gif|webp)' | tail -1 | tr -d '.')
  [ -z "$ext" ] && ext="jpg"
  curl -sS -o "01_brand/_source/pdp-images/pdp_${idx}.${ext}" "$url"
done
# 패키지·로고 같은 별도 reference 자산도 함께
curl -sS -o "01_brand/_source/pdp-images/pdp_package_big.png" "<PACKAGE_URL>"
echo "총 다운로드: $(ls 01_brand/_source/pdp-images/pdp_* | wc -l) 장"
```

##### ★ GIF → JPG 첫 프레임 변환 (한국 D2C 자사몰 필수)

> ⚠️ **GIF 누락 = 신뢰 자산 누락**: 한국 D2C 자사몰은 본문 carousel·임상 차트·Before/After·인증 시일을 **GIF 애니메이션** 으로 처리하는 게 표준. JPG-only OCR 정책은 임상·인증 통째 누락.
>
> **실측 (K-뷰티 자사몰 PDP)**: 본문 16장 중 **GIF 9장에 신뢰 자산 다수** (저자극 인증·국제 인증·임상 수치·시그니처 성분 정체) 위치. JPG 만 OCR 시 임상 데이터 0건 발견.

```bash
cd 01_brand/_source/pdp-images
for f in pdp_*.gif; do
  [ -f "$f" ] || continue
  base="${f%.gif}"
  # sips macOS 내장 — 첫 프레임만 추출
  sips -s format jpeg "$f" --out "${base}_from_gif.jpg" >/dev/null 2>&1
done
echo "GIF 변환: $(ls *_from_gif.jpg 2>/dev/null | wc -l) 장 (첫 프레임 추출)"
```

##### ⚠️ 다중 프레임 추출 (★ 강력 권장 — 텍스트 누락 위험)

애니메이션 GIF 중 텍스트가 프레임마다 바뀌는 경우, **첫 프레임 OCR 만으론 풀 텍스트 누락**.

> **실측**: 누적 판매 수치를 GIF 애니메이션 카운터로 처리하는 패턴 (첫 프레임 = 시작 수치 → 마지막 프레임 = 누적 수치). 첫 프레임만 OCR 시 누적 판매 수치 (브랜드 신뢰자산 핵심) 누락 — 광고 1단 후크 후보 1개 소실.

```bash
# ffmpeg 로 첫·중간·마지막 프레임 3장 추출
cd 01_brand/_source/pdp-images
for f in pdp_*.gif; do
  [ -f "$f" ] || continue
  base="${f%.gif}"
  # 총 프레임 수 확인 (ffmpeg → ImageMagick identify 폴백)
  nframes=$(ffmpeg -i "$f" -map 0:v:0 -c copy -f null - 2>&1 | grep -oE 'frame=\s*[0-9]+' | tail -1 | grep -oE '[0-9]+')
  [ -z "$nframes" ] && nframes=$(identify -format "%n\n" "$f" 2>/dev/null | head -1)
  [ -z "$nframes" ] || [ "$nframes" -le 1 ] && continue
  mid=$((nframes / 2)); last=$((nframes - 1))
  # 첫·중간·마지막 프레임 추출
  ffmpeg -y -i "$f" -vf "select=eq(n\,0)+eq(n\,${mid})+eq(n\,${last})" -vsync vfr "${base}_frame%02d.jpg" >/dev/null 2>&1
done
echo "다중 프레임 추출: $(ls *_frame*.jpg 2>/dev/null | wc -l) 장"
```

운영 부담 시 첫·마지막 2장만 추출도 OK. ImageMagick `convert -coalesce input.gif frame_%02d.jpg` 도 동일 효과 (전 프레임 추출 후 sips 청크 분할).

> 💡 ffmpeg 미설치 시 폴백: ImageMagick `convert` (`brew install imagemagick`) 또는 첫 프레임만으로 진행 + brand_brief 에 `[GIF 다중 프레임 미적용 — 카운터 수치 검증 필요]` 표기.

#### 2.5-3. ★ 전수 청크 분할 (sips, macOS 내장)

PDP 상세 이미지는 보통 1000×4000~10500 의 거대한 세로 이미지. Vision 모델 정밀도 확보를 위해 **2500px 단위 청크 분할**. **전수 다운로드된 `pdp_*.jpg` (GIF 변환 산출물 `pdp_*_from_gif.jpg` 포함) 모두** 자동 처리:

```bash
cd 01_brand/_source/pdp-images
for f in pdp_*.jpg; do
  base="${f%.jpg}"
  height=$(sips -g pixelHeight "$f" | tail -1 | awk '{print $2}')
  chunks=$(( (height + 2499) / 2500 ))
  echo "$f → height=${height}px → ${chunks} chunks"
  for ((i=0; i<chunks; i++)); do
    y=$(( i * 2500 )); h=2500
    if (( y + h > height )); then h=$(( height - y )); fi
    sips --cropToHeightWidth "$h" 1000 --cropOffset "$y" 0 "$f" --out "${base}_chunk${i}.jpg" >/dev/null 2>&1
  done
done
echo "총 청크: $(ls *_chunk*.jpg | wc -l) 장"
```

#### 2.5-4. ★ 전수 Claude Vision OCR (선택 OCR ❌)

> ⚠️ **선택 OCR 금지**: 모든 청크를 `Read` 로 호출. 5장만 보고 끝내면 핵심 USP·라인업·임상 9장 누락 (실측). **컨텍스트 부담은 청크 30+ 일 때만** — Sonnet/Opus 는 1턴 20+ 이미지 동시 처리 가능.

청크별 직접 호출 (병렬 가능):

```
Read /절대경로/01_brand/_source/pdp-images/pdp_01_chunk0.jpg
Read /절대경로/01_brand/_source/pdp-images/pdp_01_chunk1.jpg
... (모든 청크 — 전수 호출)
```

모든 청크 호출 후 채팅에 다음 프롬프트 한 번에 제시:

```
위에 첨부된 모든 청크는 <브랜드명> PDP 상세설명 본문 (총 N장) 을 위→아래 분할한 것입니다.
광고 소재 제작에 필요한 정보를 청크 번호 명시하며 전수 추출:

1. 각 청크의 모든 카피·문구 정확 OCR (헤드라인·서브·본문·CTA·각주·임상 출처 표기 — 한 줄도 빠짐없이)
2. 컬러 톤 (배경·강조·텍스트 HEX 추정)
3. 헤드라인 폰트 스타일 (세리프/산세리프, 폰트 패밀리 추정)
4. 시각 구성 (제품 컷·라이프스타일·인포그래픽·임상 차트·어워드 메달)
5. 정량 수치 (% / ppm / 시간 / 임상 대조군·기관·기간 / 누적 판매·연속 수상 햇수)
6. 사용법·주의사항·신뢰 자산 (인증·임상·수상 메달)
7. 라인업 정보 (시리즈 제품·각 SKU 핵심 카피)
8. 5단 카피 시드로 쓸 만한 메인 카피 Top 5

한국어 답변. 청크 번호 + 위치 (상/중/하) 명시.
```

> 💡 **컨텍스트 한도**: 청크 30+ 면 한 턴 분할 (1~15 → 16~30 → ...). 50+ 면 본문 분량이 1페이지 brand_brief 범위 초과 → 핵심 청크만 우선 처리 + brand_brief 에 "[전체 OCR raw 결과는 별도 `_source/raw_ocr.md` 참조]" 표기.

##### ★ OCR 누락 자가진단 (★ 폴백 자동 트리거)

OCR 결과 통합 후, brand_brief 작성 직전에 **핵심 신뢰자산 키워드 카운트** 자가진단. 0건이면 본문 미추출 의심 → 폴백 자동 트리거.

| 키워드 패턴 | 의미 | 0건이면 |
|---|---|---|
| `%`, `퍼센트` | 임상 수치 (97% 세정, 58.1% 감소 등) | 임상 본문 미추출 |
| `임상`, `테스트`, `시험`, `인체적용` | 임상 본문 | 임상 본문 미추출 |
| `인증`, `수상`, `어워드`, `award`, `테스트 완료` | 신뢰 자산 메달 | 인증 영역 미추출 |
| `ml`, `g`, `mg`, `ppm` | 정량 스펙 | 성분/스펙 영역 미추출 |
| 브랜드명 (한·영) | 브랜드 헤더 | 본문 자체 미수집 (중대) |

```bash
# 모든 OCR 결과를 raw_ocr.md 에 누적했다고 가정
RAW=01_brand/_source/raw_ocr.md
echo "=== OCR 누락 자가진단 ==="
for kw in '%' '임상' '테스트' '시험' '인증' '수상' '어워드' 'award' 'ml' 'mg' 'ppm'; do
  cnt=$(grep -ci "$kw" "$RAW" 2>/dev/null || echo 0)
  flag=""
  [ "$cnt" = "0" ] && flag=" ⚠️ MISS"
  echo "  [$kw] ${cnt}건${flag}"
done
```

**0건 누적 다수 시 폴백 순서**:
1. **2.5-1b iframe 패턴 재시도** — 페이지가 iframe 안일 수 있음 (네이버 X / 일부 카페24 O)
2. **2.5-1 expandKw 키워드 추가** — 비표준 더보기 텍스트 가능성 (사용자 페이지 진단 후 키워드 보강)
3. **2.5-8 풀페이지 스크린샷 폴백 (L4)** — 최종 안전망

> **실측 검증**: JPG-only OCR 케이스 → "임상" 0건 / "테스트" 0건 / "인증" 0건 / "%" 가격 할인율만 → **임상 본문 미추출 의심 진단 가능 → GIF 추가 OCR 권고 자동 트리거**.

#### 2.5-5. brand_brief.md 통합

OCR 결과를 다음 섹션에 통합 (v1 분석 결과와 충돌 시 v2 OCR 결과를 우선):

- **§ USP** — 3종 분류:
  - A. **시그니처 기술 USP** (자사 독자 IP·기술명 — 1·2단 핵심 자산)
  - B. **스펙 USP** (의무 표기·성분 ppm — 3단 증거용)
  - C. **마케팅 카피 USP** (실측 헤로 카피 — 1단 후킹용)
- **§ 비주얼 6슬롯 컬러 팔레트** — 본문 이미지 추출 컬러로 **교체** (HTML CSS 결과는 카페24 헤더·CTA 영역 한정일 수 있음을 명시)
- **§ 메인 헤드라인 카피** — 실측 카피 인용 (출처: 청크 번호)
- **§ 신뢰 자산** — 임상 시험 기관·기간·대조군 / 인증 / 자사 IP 명칭

#### 2.5-6. 정리 (OCR 완료 후)

청크 12+ 장은 디스크 절약 위해 정리. 원본 PDP 이미지(`pdp_*.jpg`) + 패키지는 캐러셀·재분석 시드용으로 유지.

```bash
rm -f 01_brand/_source/pdp-images/*chunk*.jpg
# 원본 pdp_01.jpg, pdp_02.jpg, pdp_package_big.png 등은 유지
```

#### 2.5-7. 폴백·옵션 업그레이드

| 미설치 도구 | 폴백 |
|---|---|
| Playwright | `curl` 로 페이지 HTML 다운 + 정규표현식: `grep -oE 'https?://[^"]+\.(jpg\|png\|webp)' page.html` |
| sips (macOS 외) | ImageMagick `magick` / `convert` 또는 Python PIL `Image.crop()` |

> 💡 **옵션 업그레이드 (반복 배치 운영 시)**: 청크 10장+ 를 PDP 별로 자주 OCR 하면 별도 Gemini 비전 MCP 서버(예: `mcp-server-google-genai`) 를 추가해 `gemini_chat` 류 도구로 1회 10장 일괄 호출 가능 → Claude 세션 컨텍스트 절약 + 약 6배 빠름. 본 OS 기본 `nanobanana-mcp-server` 는 이미지 **생성** 전용이라 OCR 도구는 별도 등록 필요.

#### 2.5-8. ★ 풀페이지 스크린샷 폴백 (L4 최종 안전망)

위 단계 모두 실패 (콤보 evaluate → 이미지 0장 / iframe 진입 → 본문 0장 / curl 403·404) → 최후의 수단으로 **렌더링된 픽셀 자체를 캡처**.

```javascript
// 2.5-1 콤보로 페이지 펼친 상태에서 풀페이지 스크린샷
mcp__playwright__browser_take_screenshot({
  fullPage: true,
  type: 'jpeg',
  filename: '01_brand/_source/pdp-images/fullpage_fallback.jpeg'
})
```

```bash
# 풀페이지 스크린샷을 2500px 청크로 분할 → 전부 OCR 대상
cd 01_brand/_source/pdp-images
height=$(sips -g pixelHeight fullpage_fallback.jpeg | tail -1 | awk '{print $2}')
width=$(sips -g pixelWidth fullpage_fallback.jpeg | tail -1 | awk '{print $2}')
chunks=$(( (height + 2499) / 2500 ))
for ((i=0; i<chunks; i++)); do
  y=$(( i * 2500 )); h=2500
  if (( y + h > height )); then h=$(( height - y )); fi
  sips --cropToHeightWidth "$h" "$width" --cropOffset "$y" 0 fullpage_fallback.jpeg --out "fullpage_chunk${i}.jpeg" >/dev/null 2>&1
done
```

→ 2.5-4 와 동일하게 청크 전수 OCR.

**장점**: 어떤 몰·iframe·SPA·동적 렌더링 패턴이든 화면에 보이는 픽셀은 100% 캡처.
**단점**:
- 본문 이미지 별도 분리 ❌ (광고 시드 reference 로 재사용 어려움)
- 스크린샷 dpi 가 본문 원본보다 낮을 수 있어 OCR 정밀도 ↓
- 페이지 전체 UI (header·navigation·관련 상품·footer) 도 함께 포함 → 노이즈 ↑

→ 본 폴백은 **최후의 수단**. 2.5-1 → 2.5-1b iframe 진입까지 시도 후, 그래도 본문 0장이면 호출.

### Step 3. 추출 항목 (광고에 필요한 것만)

- **한 줄 정의** (브랜드가 어떤 제품을 누구에게 어떻게 약속하는가)
- **USP 3개** (광고에 절대 빠지면 안 되는 것)
- **타겟** (Primary 인구통계 + 구매 결정 트리거)
- **톤** — Always 3가지 / Never 3가지
- **★ 비주얼 (6슬롯 컬러 팔레트 + 폰트 + 제형 묘사)** — 아래 § Step 4 의무 표
- **가격 + 메인 오퍼** (광고 랜딩에 노출되는 가격 1~2개)

### Step 4. ★ 비주얼 섹션 의무 산출물 (05 스킬이 그대로 인용)

`brand_brief.md` 의 § 비주얼 섹션은 다음 4파트를 모두 포함해야 한다.

#### 4-1. 컬러 팔레트 6슬롯 표 (의무)

```markdown
| 슬롯 | 용도 | HEX | 출처 (어디서 봤나) |
|---|---|---|---|
| `BG-Light` | 배경 시작점·평면 베이스 (가장 옅은 톤) | #... | (예: 상세페이지 본문 BG) |
| `BG-Deep` | 배경 끝점·푸터 (가장 짙은 톤) | #... | (예: 푸터 / CTA띠) |
| `BRAND-Signature` | 시그니처 메인 — CTA·키워드·1포인트 강조 | #... | (예: 구매 버튼 솔리드) |
| `BRAND-Sub` | 보조 강조 — 뱃지·서브 강조 | #... | (예: 할인율·NEW 뱃지) |
| `TEXT-Primary` | 메인 텍스트 (니어 블랙 또는 짙은 톤) | #1A1A1A 류 | (본문 카피) |
| `TEXT-Sub` | 보조 텍스트 (라벨·캡션) | #6B6B6B 류 | (캡션·각주) |
```

> 슬롯이 비면 빈 칸 ❌ — `[확인 필요]` 라벨로 명시. 05 스킬은 슬롯 비어있으면 호출 중단.

#### 4-2. 사용 ❌ 컬러 (브랜드 외 / 의약품 연상 / 경쟁사 톤)

```markdown
- ❌ 네온·형광 (브랜드 톤 이탈)
- ❌ 의약품 연상 컬러 (병원 그린·블루 류) — 화장품/식품 카테고리에 한정
- ❌ 경쟁사 시그니처 컬러 (예: <경쟁사 A> 의 옐로우, <경쟁사 B> 의 핫핑크)
- ❌ 무지개 그라디언트 / 4컬러 이상 그라데이션
- ❌ <브랜드별 추가 금지 컬러> (페이지에서 일부러 회피한 컬러가 있으면 명시)
```

#### 4-3. 요소별 컬러 매핑 (★ 광고 소재 작성 시 슬롯 → 디자인 요소 1:1 매핑)

```markdown
| 디자인 요소 | 사용 슬롯 | 비고 |
|---|---|---|
| 메인 배경 (단색·그라데이션 시작) | `BG-Light` | 그라데이션은 → `#FFFFFF` 또는 → `BG-Deep` |
| 푸터·CTA 배경 띠 | `BG-Deep` 또는 `BRAND-Signature` | 시그니처 띠가 디폴트 |
| 헤드라인 (메인 카피) | `TEXT-Primary` | BG 가 어두우면 `#FFFFFF` 로 반전 |
| 서브 카피·라벨·캡션 | `TEXT-Sub` | 본문 대비 작게 |
| 가격·숫자 강조 1포인트 | `BRAND-Signature` | 한 시안에 1포인트만 |
| CTA 버튼 (배경) | `BRAND-Signature` 솔리드 | 버튼 텍스트는 `#FFFFFF` |
| 뱃지 (NEW·1+1·할인율) | `BRAND-Sub` 또는 `BRAND-Signature` | 큰 강조면 시그니처, 보조면 서브 |
| 박스·도형 외곽선 | `BRAND-Signature` 18% opacity | 두꺼운 솔리드 외곽선 ❌ |
| 외곽 stroke 텍스트 | `BRAND-Signature` 4px | 화이트 텍스트 + 시그니처 stroke |
| 강조 highlight bar (마커) | `BRAND-Sub` semi-transparent | 형광펜 효과 |
```

#### 4-4. 폰트 + 제형 묘사

- **폰트 패밀리**: (예: Pretendard / Apple SD Gothic Neo / Noto Sans KR) — 실제 페이지에서 확인된 것만
- **제형 묘사 (제품이 있는 카테고리)**: 베이스 색·투명도 / 비드·텍스처 형태·크기·색 — 페이지·제형컷 사진을 정확히 인용 (AI 추정 ❌)

### Step 5. 저장

- `01_brand/brand_brief.md` 에 마크다운으로 저장
- 정량 수치(임상·달성률 등)는 출처 표기 필수
- § 비주얼 섹션의 컬러 팔레트 표 6슬롯 모두 채워졌는지 자체 점검 — 빈 슬롯 있으면 `[확인 필요]` 라벨로 명시

## 디테일 회피 룰

- ❌ 4파일·5파일 분석 — 1페이지가 한계
- ❌ JTBD·커스터머 저니·12개월 로드맵 같은 전략 산출물 (이 스킬은 광고용)
- ❌ 인터뷰형 질문 — URL 자동 추출이 원칙
- ❌ § 비주얼 컬러 팔레트 표를 누락하거나 빈 칸으로 두기 — 슬롯 비면 `[확인 필요]` 명시
- ❌ AI 가 추정한 HEX (페이지에서 안 잡히는데 그럴듯한 값으로 채우기) — 차라리 `[확인 필요]`
- ❌ 시크릿몰·랜딩 페이지만 분석해서 본 브랜드 톤이라고 단정 — 본 브랜드 자사몰 / 대표 상세페이지가 1순위
- ❌ **한국 D2C 자사몰 PDP를 HTML 텍스트·CSS 만으로 분석 종료** — 상세 본문 마케팅 카피·USP·임상은 이미지 안에 있어 § Step 2.5 OCR 필수. 안 하면 시그니처 컬러·메인 카피·자사 IP 모두 누락 (실측 검증됨)
- ❌ HTML body/CSS 에서 추출한 컬러를 **시그니처 컬러**로 단정 — 카페24 등 자사몰 템플릿의 헤더·CTA·푸터 영역 한정일 수 있음. 본 브랜드 시그니처 컬러는 **PDP 본문 이미지에서 헤드라인 강조 색**을 1순위로 봐야 함
- 부족한 정보가 있으면 `[확인 필요]` 라벨로 명시하고 진행 (멈추지 말 것)

## 다음 단계 안내

저장 후 사용자에게:
> "01_brand/brand_brief.md 작성 완료. § 비주얼 컬러 팔레트 6슬롯 모두 채워졌는지 한 번 검토해주세요 — 광고 소재 제작 시 그대로 인용됩니다. 다음은 `/02-competitor-from-adlib <Meta 광고라이브러리 URL>` 로 경쟁사 분석을 시작하세요."

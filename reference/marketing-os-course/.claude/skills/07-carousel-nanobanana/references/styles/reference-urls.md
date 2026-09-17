# Reference URLs — 카드뉴스 시각 흡수용

> 사용자가 인스타그램 카드뉴스 reference URL 을 라인별로 붙이는 파일.
> `_scripts/fetch_style_refs.py` 가 본 파일을 읽어 → Apify IG 액터로 다운로드 → `references/styles/{slot}/` 폴더에 저장.

---

## 작성 룰 (★ 필수 형식)

1줄 = 1 URL. URL 뒤에 슬롯 라벨 ` → {slot}` 필수. (선택) ` # 메모`.

```
https://www.instagram.com/p/XXXX/?img_index=N → 03-glossier # 핑크·뉴트럴 페미닌
```

**슬롯 라벨** (정확히 5개 중 1개 — 해외 브랜드 앵커 네이밍):

- `01-versed` — Versed 톤 (클린 미니멀·흰 BG·산세리프·라벨 박스)
- `02-glowrecipe` — Glow Recipe 톤 (비비드 컬러 블록·과일 모티프·빅 타이포)
- `03-glossier` — Glossier 톤 (글로시 핑크·뉴트럴·한·영 세리프 믹스)
- `04-tula` — TULA 톤 (프로바이오틱 더마 사이언티픽·콜드 그레이·큰 숫자·그리드)
- `05-herbivore` — Herbivore Botanicals 톤 (내추럴·식물·헤리티지·빈티지 라벨)

**슬롯 결정 휴리스틱**: STYLE-GUIDE.md § Quick Comparison 표 참조 (1초 매핑).

`?img_index=N` — 캐러셀 게시물의 N번째 슬라이드만 다운로드 (1부터). **`?img_index` 자체를 빼면 캐러셀 전체 슬라이드 일괄 다운로드** (★ 추천).

**비활성화**: 라인 맨 앞에 `#` 붙이면 다운로드 스킵.

---

## URL 리스트

```
# === 1차 시드 (2026-05-11 해외 브랜드 재편 · 캐러셀 전체 슬라이드 일괄 다운로드) ===

# Versed (클린 미니멀) — 흰 BG · 산세리프
https://www.instagram.com/p/DP1lz9diSNt/ → 01-versed # @versed

# Glow Recipe (컬러 블록) — 비비드 컬러 + 과일 모티프
https://www.instagram.com/p/DXcKsnCAJok/ → 02-glowrecipe # @glowrecipe
https://www.instagram.com/p/DYCj-7qjpFh/ → 02-glowrecipe # @glowrecipe

# Glossier (소프트 페미닌) — 핑크·뉴트럴
https://www.instagram.com/p/DU_y9w1Ehzt/ → 03-glossier # @glossier
https://www.instagram.com/p/DSxdgHNFDiu/ → 03-glossier # @glossier

# TULA (사이언티픽 데이터) — 프로바이오틱 더마
https://www.instagram.com/p/DTOZBeJEesg/ → 04-tula # @tula

# Herbivore Botanicals (내추럴·헤리티지)
https://www.instagram.com/p/DXrxjGXEcgG/ → 05-herbivore # @herbivorebotanicals

# === 추가 reference (사용자가 줄바꿈으로 붙여주세요, 슬롯당 4~6장 추가 권장) ===
# 예시:
# https://www.instagram.com/p/Cxxxxxxxxxxx/?img_index=2 → 03-glossier
# https://www.instagram.com/p/Dxxxxxxxxxxx/ → 02-glowrecipe # 컬러 블록 톤

# === 사용자 추가 카드뉴스 reference (예시) ===
https://www.instagram.com/p/DYhdiSsIHAI/?img_index=1 → 02-glowrecipe # @glowrecipe "Glow with Pride" — 라벤더→핑크 그라데이션 BG, 일러스트 스티커(무지개·하트·수박·물방울), 빅 스크립트 타이포

# === 권장 추가 출처 (슬롯별) ===
# 01-versed: @theinkeylist, @bubble, @vichy
# 02-glowrecipe: @drunkelephant, @youthtothepeople, @milkmakeup
# 03-glossier: @rarebeauty, @merit, @summerfridays
# 04-tula: @paulaschoice, @theinkeylist, @vichy
# 05-herbivore: @youthtothepeople, @beboldforbeauty, @ranavat
```

---

## 다운로드 실행

```bash
export APIFY_TOKEN="apify_api_..."

# 전체 활성 URL 일괄 다운로드
python3 .claude/skills/07-carousel-nanobanana/_scripts/fetch_style_refs.py

# 특정 슬롯만
python3 .claude/skills/07-carousel-nanobanana/_scripts/fetch_style_refs.py --slot 03-glossier

# Dry-run (URL 파싱·분배만 확인)
python3 .claude/skills/07-carousel-nanobanana/_scripts/fetch_style_refs.py --dry-run
```

**출력**: `references/styles/{slot}/ref-NN-{shortcode}.jpg`
**번호**: 슬롯 폴더 내 기존 ref-NN 의 다음 번호로 자동 증가
**중복 방지**: 같은 shortcode + img_index 조합은 스킵

---

## 다음 단계 (다운로드 후)

1. 다운로드된 PNG 가 슬롯에 맞는지 시각 확인 (잘못 분류된 건 수동 이동)
2. `STYLE-GUIDE.md § 참조 자료` 는 폴더 enumerate 로 자동 인용 (수동 갱신 불필요)
3. 카드뉴스 작업 호출 시 SKILL Step 1.5-2 ③ 가 자동 시각 흡수

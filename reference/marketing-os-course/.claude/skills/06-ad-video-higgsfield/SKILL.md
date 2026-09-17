---
name: 06-ad-video-higgsfield
description: 01_brand(자사) + 02_competitor(경쟁사) + 03_customer(고객) 1페이지 분석을 통합 인풋으로 받고, 시드 이미지(`05_ad_image/*.png` 또는 `01_brand/products/*.jpg`) 위에 모션 디렉션을 합성해 Higgsfield Skills 팩(`/higgsfield:generate`, OAuth) 로 6초 내외 짧은 광고 영상(.mp4) 을 **디폴트 단일 모델로 1편 생성** (크레딧 절약) 해 `06_ad_video/{YYYY-MM-DD}_{캠페인-슬러그}/` 서브폴더에 저장하는 스킬. **2-tier 모델 세트**: Tier 1 디폴트 **1종** (Seedance 2.0 — 720p·9:16·6초 기준 27 크레딧/편으로 가장 저렴) / Tier 2 비교 확장 (Kling 3.0·Veo 3.1·Seedance 2.0 3종 또는 그 이상 ~10종). 사용자가 "비교", "여러 모델로", "다양하게", "풀 확장", "이전처럼", "풍부하게", "마케팅 스튜디오 포함" 등으로 명시 시에만 Tier 2 자동 호출. 사용자가 "영상 만들어줘", "광고 영상 제작해줘", "이 이미지로 짧은 영상", "/06-ad-video-higgsfield" 등으로 요청 시 호출 (디폴트 = Tier 1 단일 생성). **사전 컨펌 게이트 ❌** — v1 출력 직후 모션 디렉션·무드 시드를 채팅에 동봉해 사용자가 사후 검수·v2 반복. 파워 유저가 `04_brief/confirmed_brief.md` 를 사전 작성한 경우만 § 2·3·4·6 그대로 인용 (분기 A). 없으면 brand_brief/pain_points/competitor 에서 무드·제품 reference·포맷을 동적 로드 (분기 B, 디폴트). 본 스킬이 합성하는 건 **모션 디렉션** (카메라 무브·주체 동작·환경/소품·라이팅 변화) 1축뿐.
---

# 05. 광고 영상 생성 (Higgsfield → MP4)

> 이 스킬의 목표는 **01~03 분석 통합 + 시드 이미지 → Higgsfield 모션 프롬프트 → MP4**.
> **분기 A** (confirmed_brief.md 존재): § 2·3·4·6 그대로 인용. **분기 B** (디폴트): brand_brief/pain_points/competitor 에서 무드·제품 reference·포맷 동적 로드 + Step 1.5 in-memory 도출. 본 스킬이 추가하는 건 모션 디렉션 (카메라 무브·동작·라이팅 변화·길이) 1축이다.

## 호출 시점

- "영상 만들어줘"
- "광고 영상 제작해줘"
- "이 이미지로 짧은 영상"
- "시안 만들었으니 영상으로" / "이거 움직이게"
- "/06-ad-video-higgsfield"
- 05-ad-image-nanobanana 직후 (시드 이미지가 막 만들어진 상태)
- 사용자가 임의 시드 이미지 경로를 첨부한 경우

**Tier 자동 판정**:
- 디폴트 (Tier 1, **1종 — Seedance 2.0**): 위 일반 트리거. **크레딧 절약 — 27 크레딧/편 (720p·9:16·6초)**.
- 비교 확장 (Tier 2, 3~10종): 트리거에 "비교" / "여러 모델로" / "다양하게" / "풀 확장" / "이전처럼" / "풍부하게" / "마케팅 스튜디오 포함" 키워드 포함 시에만 자동.

---

## Setup (1회성, 사용자 직접)

> 출처: `Claudecode_MarketingOS_student/ref/higgsfield.md` Part 6 (OAuth + Skills 팩). 본 OS 는 OAuth 방식을 디폴트로 채택 — API 키 발급·`.env` 관리 없이 슬래시 스킬로 위임. cloud.higgsfield.ai 의 cloud API 라인업(DoP·Soul·Popcorn) 은 자체 모델만 노출하므로 Kling/Veo/Seedance 같은 외부 모델 비교는 OAuth + Skills 팩 경로가 유일.

1. **CLI 설치 + OAuth 로그인**
   ```bash
   npm install -g @higgsfield/cli
   higgsfield auth login        # 브라우저 자동 오픈 → 5초
   ```
   브라우저 떴다 닫히면 끝. Higgsfield 계정으로 OAuth 인증 1회.

2. **Skills 팩 설치** (슬래시 스킬 4종)
   ```bash
   npx skills add higgsfield-ai/skills
   ```
   설치되는 슬래시 스킬:
   - `/higgsfield:generate` — 이미지·영상 (Kling 3.0·Veo 3.1·Seedance 2.0·Wan·Minimax Hailuo 등 30+ 모델)
   - `/higgsfield:soul-id` — Soul Character 학습 (얼굴 일관 ID — 모델 시안 광고용)
   - `/higgsfield:product-photoshoot` — 제품 사진 10모드
   - `/higgsfield:marketplace-cards` — 마켓플레이스 카드 (쿠팡·스마트스토어)

3. **연결 확인**
   ```bash
   higgsfield account           # 잔여 크레딧 + 로그인 상태
   higgsfield model list        # 사용 가능 모델 ID 출력 (kling3_0 등)
   ```
   Claude Code 채팅창에서 `/higgsfield:generate` 자동완성에 떠야 정상.

4. **무료 크레딧 확인**
   - `higgsfield account` 출력에서 잔여 크레딧 50+ 확인
   - OAuth 방식은 가입 시 자동 지급되는 경우 多. 부족하면 cloud.higgsfield.ai 또는 `higgsfield account` 에서 토픕.

> ⚠️ **`.env` / `.mcp.json` 의 `HF_API_KEY` 항목 ❌** — OAuth 단일화. cloud API 키 방식과 혼용 시 혼란 ↑ . 만약 `.mcp.json` 에 `higgsfield` 항목이 남아 있다면 제거.

---

## Prerequisites

**필수**:
- `@higgsfield/cli` 설치 + `higgsfield auth login` OAuth 완료 (`higgsfield account` 으로 확인)
- `npx skills add higgsfield-ai/skills` 설치 — `/higgsfield:generate` 슬래시 스킬 호출 가능
- `01_brand/brand_brief.md` § 4-1 컬러 6슬롯 채워짐 — 라이팅 톤 가이드의 ground truth. 없으면 → "`/01-brand-from-url <URL>` 로 컬러를 먼저 채워주세요" 안내 후 종료
- **시드 이미지 1장** — 다음 중 1:
  - (a) `05_ad_image/<파일명>.png` (05-image 산출물 — 권장)
  - (b) `01_brand/products/<파일명>.jpg` (실재 제품컷)
  - (c) 사용자가 첨부한 임의 경로
  - 미존재 시 → "`/05-ad-image-nanobanana` 로 시드 이미지 먼저 생성하거나 시드 경로 첨부해주세요" 안내 후 종료

**선택**:
- `02_competitor/competitor_ads.md` — 있으면 빈틈·헤드라인 패턴을 모션 톤 반영 (경쟁사가 안 쓰는 카메라 무브 선택)
- `03_customer/pain_points.md` — 있으면 페인 톤을 모션 무드에 매핑 (예: "잡티 절박" → slow brighten reveal)
- **`04_brief/confirmed_brief.md`** — 있으면 § 2·3·4·6 그대로 인용 (분기 A). 없으면 분기 B 디폴트로 Step 1.5 자동 도출.

## 핵심 원칙 (5줄, 절대 위반 ❌)

✅ **시드 이미지 픽셀 AS-IS** — 첫 프레임은 시드 그대로. 모션은 카메라·환경·소품에서만 발생, 제품/라벨/제형은 변형 ❌
✅ **무드·제품 reference 인용 출처 = 분기별 분리** — **분기 A** (confirmed_brief.md 존재): § 2·3·4·6 그대로 인용. **분기 B** (디폴트): 01_brand/02_competitor/03_customer 1페이지 분석에서 무드·페인·포맷 동적 로드 후 Step 1.5 에서 in-memory 도출. AI 추정 ❌
✅ **단일 모델 생성이 디폴트 (크레딧 절약)** — 디폴트 1종 = **Seedance 2.0** (720p·9:16·6초 = 27 크레딧/편). 다중 모델 비교는 사용자가 "비교"/"여러 모델로"/"풀 확장" 등 명시 시에만 (Tier 2 진입)
✅ **길이 디폴트 6s** / **비율** — 분기 A: confirmed_brief § 6 / 분기 B: 사용자 지정 또는 9:16 fallback
✅ **output_path 항상 절대경로 명시** — `Claudecode_MarketingOS_student/06_ad_video/{YYYY-MM-DD}_{캠페인-슬러그}/{파일명}.mp4`. 서브폴더 없으면 `mkdir -p` 선행 (★ 2026-05-25 날짜·캠페인 서브폴더 의무. `{YYYY-MM-DD}` = 시안 생성일, `{캠페인-슬러그}` = `04_brief/confirmed_brief.md` frontmatter `campaign:` 값)

> **카피 텍스트는 본 스킬이 영상 안에 합성 ❌** — 한글 자모 깨짐 룰. 카피·CTA·자막은 후처리(CapCut/Premiere) 영역. 본 스킬이 인용하는 "카피·무드" 는 모션 톤 매핑 시드일 뿐 (영상 안에 박는 텍스트가 아님).

---

## Workflow (6 steps)

### Step 1: Gather Inputs (인풋 로드) + 분기 판정

먼저 `04_brief/confirmed_brief.md` 존재 여부를 확인해 분기:

- **분기 A — `confirmed_brief.md` 존재**: § 2·3·4·6 그대로 인용 (재해석 ❌). **Step 1.5 (자동 도출) 스킵** → 바로 Step 2 로.
  - **카피** (§ 2 5단): 모션 톤 매핑 시드로만 사용 (영상 안 합성 ❌, 후처리 영역)
  - **무드** (§ 3): 모션 톤 매핑 핵심 시드 (예: "차분·임상" → 슬로우 푸시인 / "절박·시크릿" → 빠른 줌·컷 / "럭셔리" → 오빗 돌리 / "일상·후기" → 핸드헬드 미세 흔들림)
  - **제품 reference** (§ 4): 시드 이미지 후보군 reference 일관성 점검
  - **포맷·비율** (§ 6): 영상 비율 1순위
- **분기 B — `confirmed_brief.md` 부재 (디폴트)**: Step 1.5 "Derive Motion Mood" 진입.

**brand_brief.md § 4-1 컬러 6슬롯 점검 (분기 무관 공통)** — `[확인 필요]` 잔존 시 호출 중단:
> "brand_brief.md § 4-1 컬러 팔레트 슬롯이 비어있습니다. `/01-brand-from-url <대표 상세페이지 URL>` 로 컬러를 먼저 채워주세요."

**시드 이미지 경로 확정**:
- 사용자 첨부 우선
- 없으면 `05_ad_image/` 의 가장 최근 conceptA-v{최신N} 자동 픽 (mtime 기준)
- 사용자가 "0128.jpg 로", "그 이미지 말고 hero 컷" 등 명시 시 override

---

### Step 1.5: Derive Motion Mood (★ 분기 B 만, in-memory 도출)

> ⚠️ 분기 A (confirmed_brief.md 존재) 면 본 단계 전체 스킵.

토큰 폭발 회피를 위해 각 파일에서 필요한 섹션만 Read (풀파일 ❌):

| 파일 | 추출 섹션 | 모션 매핑 용도 |
|------|----------|--------------|
| `01_brand/brand_brief.md` | § 4-1 컬러 6슬롯 + § 4-2 금지컬러 + § 톤·Never 표현 + § USP 3개 | 라이팅 톤·환경 컬러 (예: 라벤더 시그니처 → soft purple flare) |
| `03_customer/pain_points.md` | Top 5 페인 + Top 3 욕구 (리뷰 원문 ❌) | 모션 무드 매핑 시드 (예: "잡티 절박" → slow brighten reveal) |
| `02_competitor/competitor_ads.md` | 자주 쓰는 카메라 무브 패턴·빈틈 3개 | 경쟁사가 안 쓰는 모션 방향 선택 (차별화) |

> ⚠️ **차별화 가드 (의무)**: 디폴트 단일 모델(Seedance 2.0) 호출 시에도 모션 방향은 02 competitor 의 *경쟁사가 안 쓰는 카메라 무브* 로 선택. Hook 0-3초 구조·페이싱은 자사 USP 기반. (Tier 2 비교 확장 시에는 N종 모두 같은 차별화 가드 적용 — 시각 데모·엔딩만 모델별 자연 변주)

**도출 결과 (in-memory 변수, 디스크 저장 ❌)**:
1. **모션 무드 키워드 2~3개** (예: "차분·임상·신뢰" / "절박·공감·결과" / "럭셔리·미니멀·정적")
2. **포맷·비율** — 사용자 지정 또는 9:16 fallback
3. **카메라 무브 후보 1순위** — Step 2 4축 매핑 표에서 무드에 매칭

> v1 보고 시 채팅에 동봉 → 사용자 사후 검수. confirmed_brief.md 디스크 영구화는 사용자 명시 요청 시만.

### Step 2: Build Motion Direction (4축)

모션 프롬프트는 다음 4축으로 합성. 각 축은 **분기 A**: confirmed_brief § 3 무드 키워드 / **분기 B**: Step 1.5 도출 무드 키워드에서 자동 매핑. 사용자 override 우선.

| 축 | 무드 → 디폴트 매핑 | 예시 어휘 (영문 프롬프트) |
|---|---|---|
| **카메라 무브** | 차분·임상 → slow push-in / 절박·시크릿 → quick zoom & cut / 럭셔리 → orbit dolly / 일상·후기 → handheld subtle sway | "slow cinematic push-in toward the jar over 6s" |
| **주체 동작** | 제품 단독 → 회전·라벨 정면 / 텍스처 매크로 → 제형 surface 잔 진동 / 모델컷 → 손이 자를 살짝 들어올림 | "the jar gently rotates 15° clockwise, beads inside slowly catch light" |
| **환경/소품** | brand_brief § 4-1 컬러 톤의 light flare / floating particles (1포인트 룰 준수) | "soft purple light flare passes left→right, sparse lavender particles drift up" |
| **라이팅 변화** | 정적 무드 → 부드러운 spotlight pulse / 다이내믹 무드 → bright reveal | "key light gradually brightens 70%→100% over 3s, soft ambient stays" |

> **영상 자막 ❌ 룰**: 한글 자막·CTA 텍스트는 Higgsfield 영상 모델이 자모 깨짐·왜곡으로 못 그림. 자막은 후처리에서 입힘. 영문 1~3단어 라벨 (예: "NEW", "1+1") 은 가끔 가능하지만 디폴트 ❌.

### Step 3: Determine Format, Duration, Model Set

**비율** — **분기 A**: `confirmed_brief.md § 6` 1순위 / **분기 B**: 사용자 지정 또는 9:16 fallback:
| 옵션 | 용도 |
|---|---|
| 9:16 | Reel/TikTok/Story (디폴트 fallback) |
| 1:1 | Meta Feed 정사각 |
| 4:5 | Meta Feed portrait |
| 16:9 | YouTube 인스트림·웹 배너 |

**길이** — 디폴트 **6s**. 사용자 명시 override (4s / 8s / 10s — 모델별 한도 내).

**모델 세트** (모델 ID 출처: GitHub `higgsfield-ai/cli` README 2026-05 기준)

본 스킬은 **2-tier 모델 세트 정책** (크레딧 절약 디폴트):

#### Tier 1 — 디폴트 (1종 단일 생성, 크레딧 절약)

사용자가 모델·확장 명시 안 한 경우 자동 호출. **27 크레딧/편 (720p·9:16·6초 기준)**.

- **Seedance 2.0** (`seedance_2_0`) 1종 — 가장 저렴 + 한국 D2C 영상 톤 정합 양호
- 같은 시드 + 같은 모션 프롬프트 → 1번 호출
- v1 결과 보고 사용자가 사후 검수 → v2~v5 자연 반복 (모션 강도·각도·길이 변형)
- "Kling 으로 해줘" / "Veo 로" 같은 단일 모델 override 도 Tier 1 (모델만 갈아끼움)
- ★ 비율 제약 (override 시): Veo 3.1 은 1:1 미지원 → `9:16` 또는 `16:9` 로 자동 조정
- ★ 플래그 차이 (override 시): Veo 3.1 은 `--start-image` 미지원 → `--image` 사용
- ★ 비교가 필요하면 → 사용자에게 "여러 모델로 비교하시려면 '비교'/'여러 모델로' 키워드로 다시 요청해주세요. Tier 2 (3~10종) 진입 시 크레딧 80+ 소모됩니다." 안내 후 단일 생성

#### Tier 2 — 비교 확장 (3~10종, 사용자 명시 시만)

사용자가 **"비교"** / **"여러 모델로"** / **"다양하게"** / **"풀 확장"** / **"이전처럼"** / **"풍부하게"** / **"마케팅 스튜디오 포함"** 등으로 명시 시 자동 호출. **크레딧 소모량 ↑ — 호출 직전 잔여 크레딧 점검·사용자 확인 필요**.

**3종 기본 비교** (트리거에 "풀 확장"/"마케팅 스튜디오" 없음): Kling 3.0 + Veo 3.1 + Seedance 2.0 → 같은 시드·같은 프롬프트, model 만 변경 3번 호출 (약 80+ 크레딧).

**풀 확장 즉시 가능 7종 (3종 기본 비교 + 추가 4종)** — "풀 확장" 명시 시 호출. 같은 시드, 일부 카메라 무브 변형:
| 모델 | 카메라 무브 | 비율 | 플래그 |
|---|---|---|---|
| Kling 3.0 (`kling3_0`) | push-in (디폴트) | 1:1 | `--start-image` |
| Veo 3.1 (`veo3_1`) | push-in (디폴트) | 9:16 (1:1 미지원) | `--image` |
| Seedance 2.0 (`seedance_2_0`) v1 | push-in (디폴트) | 1:1 | `--start-image` |
| Seedance 2.0 (`seedance_2_0`) v2 | **orbit dolly** | 1:1 | `--start-image` |
| Seedance 2.0 (`seedance_2_0`) v3 | **pull-back** | 1:1 | `--start-image` |
| Wan 2.7 (`wan2_7`) | push-in | 1:1 | `--image` |
| Cinema Studio 3.0 (`cinematic_studio_3_0`) | push-in (시네마틱) | 1:1 | `--image` |

**Marketing Studio 3모드 (셋업 필요, 별도 흐름 — 본 § 아래 "Marketing Studio 풀 확장 흐름" 참조)**:
| 모드 | `--mode` slug | 비율 | 비고 |
|---|---|---|---|
| UGC 기본 | `ugc` | 9:16 | presenter avatar + product |
| Review | `product_review` | 9:16 | 후기형 톤 |
| Showcase | `product_showcase` | 9:16 | 제품 단독 강조 |

총 **10종 영상** (7 즉시 + 3 MS) = 이전 풀 확장 회차(14종)의 75% 수준 (강의 데모성 풍부함 확보).

#### Marketing Studio 풀 확장 흐름

1. **product fetch** (자사몰 URL 1회만):
   ```bash
   higgsfield marketing-studio products fetch --url <brand_brief 의 자사몰 URL> --wait
   ```
   → 출력의 product_id 캡처.

2. **avatars list** (preset 1개 자동 픽, 기본은 `Yuna` 또는 `Jia` 같은 K-뷰티 정합 preset):
   ```bash
   higgsfield marketing-studio avatars list --json
   ```

3. **3모드 영상 생성** (Tier 2 트리거 시 자동 3회 병렬):
   ```bash
   higgsfield generate create marketing_studio_video \
     --prompt "<5요소 prompt>" \
     --avatars @<avatars.json> \
     --product_ids @<product_ids.json> \
     --mode {ugc | product_review | product_showcase} \
     --duration 15 \
     --resolution 720p \
     --aspect_ratio 9:16 \
     --wait
   ```
   파일명: `{브랜드}_{메시지슬러그}_meta-reel_conceptHero-mktstudio-{모드}-v1.mp4`

#### 사용자 override 패턴

- "Kling만으로" → `kling3_0` 1종
- "최신 Veo 라이트로" → `veo3_1_lite`
- "5종 다 비교" → `kling3_0` + `veo3_1` + `seedance_2_0` + `wan2_7` + `minimax_hailuo`
- "Veo만 빼고" → `kling3_0` + `seedance_2_0` (2종)
- "마케팅 스튜디오 빼고 풀 확장" → Tier 2 의 즉시 가능 7종만

#### 사용 가능 영상 모델 16종 (`ref/higgsfield.md` § Part 6 Step 5)

`veo3_1` · `veo3_1_lite` · `veo3` · `kling3_0` · `kling2_6` · `seedance_2_0` · `seedance1_5` · `wan2_7` · `wan2_6` · `minimax_hailuo` · `grok_video` · `cinematic_studio_3_0` · `cinematic_studio_video` · `cinematic_studio_video_v2` · `soul_cast` · `marketing_studio_video`

> 첫 호출 시 `higgsfield model list --json` 으로 실제 노출 모델 enumerate. 모델 ID 위 16종이 GitHub 공식 README 기준 ground truth.

### Step 4: Build the Prompt (5요소 모션 프롬프트)

```
[1] FIRST FRAME: Use the seed image AS-IS as the opening frame.
    DO NOT redraw, repaint, or restyle the product. The jar/cap/label/
    formula/typography from the seed image must remain visually identical
    throughout the clip. Allowed motion: camera move, environment particles,
    lighting changes, gentle subject motion (rotation, hand gesture).

[2] SUBJECT MOTION:
    <Step 2 §주체 동작 그대로 인용>

[3] CAMERA MOVE:
    <Step 2 §카메라 무브 그대로 인용>
    Duration: <length>s, smooth easing, no abrupt cuts.

[4] ENVIRONMENT & LIGHTING:
    <Step 2 §환경/소품 그대로 인용>
    Lighting: <Step 2 §라이팅 변화 그대로 인용>
    Color palette respects brand_brief § 4-1 (BG-Light / BG-Deep /
    BRAND-Signature). No off-brand color shifts.

[5] MOOD/STYLE:
    <분기 A: confirmed_brief § 3 / 분기 B: Step 1.5 도출 무드 키워드 2~3개 그대로>.
    Premium <카테고리> ad aesthetic, 2025 Korean beauty cinematography,
    cinematic depth of field, magazine-quality lighting.

[NEGATIVE]
    no warped product, no morphing label or text, no extra text overlay,
    no fake speaking model lips, no flickering, no jump cuts,
    no AI-hallucinated logos or fingers, no sudden color shift,
    no off-brand neon glow, no syringe/pill/medical imagery (if cosmetic),
    no warped fingers/teeth/eyes (if model present).
```

> ⚠️ AI 가 추정한 무드·HEX·제형 묘사 ❌. **분기 A**: confirmed_brief.md / brand_brief.md 토큰을 그대로 인용. **분기 B**: Step 1.5 도출본 + brand_brief.md 토큰을 그대로 인용해 채운다.

### Step 5: Generate the Videos (Skills 팩 위임)

**위임 대상 슬래시 스킬**: `/higgsfield:generate`
- 시드 이미지 + 모션 프롬프트 + 모델 ID + 길이/비율 을 묶어서 1번에 던짐
- Skills 팩이 OAuth 토큰으로 인증 → API 호출 → 결과 영상 다운로드까지 알아서 처리

**호출 패턴 — Tier 1 디폴트 (단일 모델, 크레딧 절약)**:
```
Use /higgsfield:generate to create a 6-second image-to-video clip.

Seed image: /Users/.../05_ad_image/[브랜드명]_1plus1_meta-feed_conceptA-v5.png

Prompt:
<Step 4 의 5요소 모션 프롬프트 그대로 붙여넣기 — FIRST FRAME / SUBJECT MOTION /
 CAMERA MOVE / ENVIRONMENT & LIGHTING / MOOD & STYLE + NEGATIVE>

Model: seedance_2_0
Duration: 6s
Aspect ratio: 9:16 (또는 confirmed_brief § 6)
Resolution: 720p

Save output to:
- 06_ad_video/{YYYY-MM-DD}_{캠페인-슬러그}/[브랜드명]_1plus1_meta-reel_conceptA-seedance20-v1.mp4
```

**호출 패턴 — Tier 2 비교 확장 (사용자 명시 시만, 크레딧 ↑)**:
```
Compare on these models (run once each, same seed, same prompt):
- kling3_0
- veo3_1
- seedance_2_0

→ 각 모델별 파일 저장:
- 06_ad_video/.../[브랜드명]_1plus1_meta-reel_conceptA-kling30-v1.mp4
- 06_ad_video/.../[브랜드명]_1plus1_meta-reel_conceptA-veo31-v1.mp4
- 06_ad_video/.../[브랜드명]_1plus1_meta-reel_conceptA-seedance20-v1.mp4
```

**모델 ID** (GitHub `higgsfield-ai/cli` README 기준, 언더스코어·점 없음):
- 디폴트 1종: `seedance_2_0` (Tier 1)
- 비교 확장 3종 (Tier 2 기본): `kling3_0` / `veo3_1` / `seedance_2_0`
- 사용자 override: `veo3_1_lite` · `kling2_6` · `wan2_7` · `minimax_hailuo` 등

**호출 직전 크레딧 체크 (Tier 2 진입 시 의무)**:
1. `higgsfield account` 로 잔여 크레딧 확인
2. 예상 소모 = N(모델 수) × 27 크레딧 (720p·9:16·6초 기준)
3. 잔여 < 예상 소모 × 1.5 → 사용자에게 "현재 X 크레딧. 비교 N종은 약 Y 크레딧 소모됩니다. 진행할까요?" 확인

**저장 경로 처리**: Skills 팩이 다운로드한 영상 파일을 `06_ad_video/{파일명}` 으로 이동·리네임 (Bash `mv` 또는 다운로드 위치 직접 지정).

> **Skills 팩이 노출하는 실제 파라미터·플래그** 는 `npx skills inspect higgsfield-ai/skills` 또는 첫 호출 시 슬래시 자동완성에서 확정. 본 스킬의 위임 프롬프트는 자연어 기반이라 슬래시가 알아서 매핑함.

### Step 6: Save and Deliver (저장·보고)

**저장 경로**: `Claudecode_MarketingOS_student/06_ad_video/{YYYY-MM-DD}_{캠페인-슬러그}/` ★ (2026-05-25 도입)
- 서브폴더가 없으면 호출 직전 자동 생성 (`mkdir -p`)
- `{YYYY-MM-DD}` = 시안 **생성일** (오늘 날짜). 같은 캠페인 며칠 후 재생산이면 새 서브폴더로 분리
- `{캠페인-슬러그}` = `04_brief/confirmed_brief.md` frontmatter `campaign:` 값 (분기 A). 분기 B 면 사용자 컨셉에서 자동 슬러그

**파일명 규칙** (CLAUDE.md § 5 확장):
- 단일 모델 (Tier 1 디폴트): `{브랜드}_{캠페인}_{채널}-{포맷}_concept{ID}-{모델키}-v{N}.mp4`
  - 예) `[브랜드명]_1plus1_meta-reel_conceptA-seedance20-v1.mp4`
- 모델 비교 (Tier 2): 같은 시안 + 모델키 다른 N개 동시 저장
- **모델키 컨벤션** (소문자, 점·하이픈·언더스코어 없음, 8자 이내 권장 — GitHub 모델 ID 의 점·언더스코어를 제거한 형태):
  - Kling 3.0 (`kling3_0`) → `kling30`
  - Veo 3.1 (`veo3_1`) → `veo31`
  - Veo 3 (`veo3`) → `veo3`
  - Seedance 2.0 (`seedance_2_0`) → `seedance20`
  - Wan 2.7 (`wan2_7`) → `wan27`
  - Cinema Studio 3.0 (`cinematic_studio_3_0`) → `cinema30`
  - Minimax Hailuo (`minimax_hailuo`) → `hailuo`
  - Marketing Studio (`marketing_studio_video`) → `mktstudio` + `-{모드slug}` 접미사 (예: `mktstudio-ugc`, `mktstudio-review`, `mktstudio-showcase`)
- **카메라 무브 변형 접미사** (Tier 2 풀 확장 시 같은 모델의 변형 구분):
  - `-orbit` (orbit dolly)
  - `-pullback` (pull-back)
  - `-handheld` (handheld sway)
  - 디폴트 push-in 은 접미사 없음
- 같은 시안 변형 → v 증가 (덮어쓰기 ❌)
- 다른 시안 → conceptB / conceptC

**보고 포맷** (★ 사후 검수 정책 — v1 출력 직후 모션 디렉션·무드 시드를 채팅 동봉):

**Tier 1 디폴트 (단일 모델)**:
> "{캠페인} 영상 1편 생성 완료 (디폴트 단일, 크레딧 절약).
> - {파일명} ({모델키} — 약 27 크레딧 소모)
>
> 🎬 사용된 모션 디렉션
> - 카메라 무브: <2~3단어 — 예: slow push-in>
> - 주체 동작: <2~3단어 — 예: jar gentle rotate>
> - 환경/라이팅: <2~3단어 — 예: soft purple flare>
> - 무드 시드: <2~3개 키워드> (출처: 분기 A → confirmed_brief § 3 / 분기 B → pain_points #N · brand_brief USP #M)
>
> 시드: {시드경로}, 길이: {N}s, 비율: {AR}.
> 잔여 크레딧: {약 X} (생성 후 추정).
>
> v2~v5 자연 반복 가능 — '슬로우 푸시인 말고 오빗으로' / '6s 말고 8s' / '더 차분하게' 처럼 한 줄.
> 모델 비교를 원하면 '비교' / '여러 모델로' 키워드로 다시 요청 (Tier 2 진입, 약 80+ 크레딧)."

**Tier 2 비교 확장 (사용자 명시 시)**:
> "{캠페인} 영상 {N}종 생성 완료 (모델 비교, 약 {N×27} 크레딧 소모).
> - {파일명1} ({모델1})
> - {파일명2} ({모델2})
> - {파일명3} ({모델3})
>
> 🎬 사용된 모션 디렉션 / 무드 시드 (동일 시드·동일 프롬프트, 모델만 변경) ...
> 비교 후 마음에 드는 모델로 v2~v5 변형 가능."

> ⚠️ confirmed_brief.md 디스크 저장 ❌ (분기 A 가 아니면). v2~ 반복은 in-memory 무드/모션 변수 일부만 수정 후 호출 → 디스크 영구화는 사용자 명시 요청 시만.

---

## 변형 옵션 (사용자 요청 시만 — v2~v5 자연 반복)

Tier 1 디폴트 단일 모델로 v1 생성 후, 사용자가 마음에 들어 변형을 원할 때만 호출. 같은 시드 N변형 = 다음 4축 중 1~2개 비틀어 **재작성** (같은 프롬프트 N번 ❌):

| 축 | 비틀기 예시 |
|---|---|
| 카메라 무브 | push-in / pull-back / orbit / handheld / static lock |
| 모션 강도 | slow / medium / fast / dramatic |
| 라이팅 변화 | static / pulse / brighten / flare-pass |
| 길이 | 4s / 6s / 8s / 10s |

---

## 호출 직전 체크리스트 (9항목)

```
□ 분기 판정 완료 (A: confirmed_brief.md 존재 → § 2·3·4·6 인용 / B: 부재 → Step 1.5 도출)
□ ★ brand_brief.md § 4-1 컬러 6슬롯 모두 채워짐 (BG-Light / BG-Deep / BRAND-Signature 등)
   — `[확인 필요]` 라벨 잔존 ❌. 슬롯 비면 호출 중단
□ 분기 B: 01_brand / 03_customer / 02_competitor 1페이지 분석에서 무드·페인 시드 추출 완료
□ 시드 이미지 경로 확정 (05_ad_image/ 또는 01_brand/products/ 또는 사용자 첨부)
□ higgsfield account 로 로그인 + 잔여 크레딧 확인 (Tier 1 = 27+ / Tier 2 = N×27+)
□ /higgsfield:generate 슬래시 자동완성에 노출 확인
□ Tier 판정 (디폴트 Tier 1 단일 / 사용자 "비교"/"여러 모델로"/"풀 확장" 명시 시만 Tier 2)
□ 모델 ID 결정 (Tier 1 디폴트 = seedance_2_0 / 사용자 override = kling3_0·veo3_1 등)
□ Tier 2 진입 시 호출 직전 사용자 크레딧 확인 ("약 N×27 크레딧 소모, 진행?")
□ 출력 경로 = 06_ad_video/{YYYY-MM-DD}_{캠페인-슬러그}/{파일명}.mp4 (Skills 팩 다운로드 후 이동·리네임)
□ 모션 프롬프트에 "FIRST FRAME AS-IS" 디렉티브 + NEGATIVE 6줄 포함
```

---

## 디테일 회피 룰 (7줄)

- ❌ brand_brief.md § 4-1 6슬롯이 비어있는데 임의 라이팅 톤·HEX 추정 (호출 중단 후 `/01-brand-from-url` 안내)
- ❌ 분기 B 에서 자동 도출한 모션 무드를 confirmed_brief.md 로 디스크 저장 (사용자 명시 요청 시만 영구화)
- ❌ 시드 이미지 없이 텍스트만으로 영상 생성 (사용자 명시 시만 — 첫 프레임 일관성 깨짐)
- ❌ 영상 안에 한글 자막·CTA 합성 시도 (모델이 자모 깨짐 → 후처리)
- ❌ 같은 모델·같은 프롬프트 5번 호출해서 변형 채우기 (4축 중 1~2개 비틀어 재작성)
- ❌ 사용자 명시 없이 자동으로 3종+ 모델 비교 호출 (Tier 2 는 "비교"/"여러 모델로"/"풀 확장" 키워드 명시 시만 — 디폴트 = Tier 1 단일 1편, 크레딧 절약)
- ❌ output_path / 다운로드 후 리네임 누락 — `06_ad_video/{파일명규칙}.mp4` 강제
- ❌ cloud API key 방식 (`.env` HF_API_KEY) 과 OAuth 혼용 — OAuth 단일화. cloud API 라인업(DoP·Soul·Popcorn) 은 Kling/Veo/Seedance 비교 不可

---

## Troubleshooting (`ref/higgsfield.md` § Part 5·6 인용)

| 에러 | 원인 | 해결 |
|---|---|---|
| `higgsfield account` → `Not authenticated` | OAuth 토큰 만료 또는 미로그인 | `higgsfield auth login` 재실행 |
| `/higgsfield:generate` 슬래시 안 보임 | Skills 팩 미설치 또는 Claude Code 재시작 안 함 | `npx skills add higgsfield-ai/skills` 후 Claude Code 재시작 |
| `command not found: higgsfield` | CLI 미설치 또는 PATH 누락 | `npm install -g @higgsfield/cli`, `node --version` 18+ 확인 |
| `Not enough credits` | 크레딧 소진 | `higgsfield account` 잔여 확인 → cloud.higgsfield.ai 토픕/플랜 |
| 영상 결과가 첫 프레임을 재해석함 | "FIRST FRAME AS-IS" 디렉티브 누락 | Step 4 [1] 블록 그대로 박았는지 점검 |
| 한글 자막이 자모 깨짐 | 영상 모델 한계 | 자막은 후처리(CapCut/Premiere) 로. 영상 자체에는 자막 ❌ |
| 분기 B 무드 키워드가 너무 추상적 ("프리미엄" 같은 빈 표현) | pain_points / brand_brief 인용 부족 | pain_points Top 페인을 모션 무드로 직접 매핑 (예: "잡티 절박" → slow brighten reveal, "끈적임" → fresh dew droplets drift) |

## 다음 단계

영상 생성 완료 후:
> "(옵션) 자막·BGM·CTA 오버레이는 후처리(CapCut/Premiere) 권장. Higgsfield 영상 모델은 한글 텍스트 합성을 잘 못함."
> "광고 집행 후 데이터가 모이면 `/06-meta-report` 로 성과 리포트를 만들 수 있습니다. (06 모듈은 추후 구축 예정)"

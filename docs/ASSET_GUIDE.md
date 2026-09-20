# ADCatcher Asset Guide

`apps/web/public/` 아래 asset을 추가/교체할 때 따르는 규칙. 자세한 폴더 구조는
[`PROJECT_STRUCTURE.md`](./PROJECT_STRUCTURE.md)를 참고한다.

## 형식 선택

| 종류 | 형식 | 이유 |
|---|---|---|
| 로고 / 심볼 / 간단한 아이콘 | SVG (진짜 vector일 때만) | 어떤 해상도에서도 선명하고 용량이 작다. |
| 3D 렌더 캐쳐 / 명화 재해석 아트워크 같은 사진·렌더 이미지 | WebP (필요 시 AVIF) | 원본 PNG보다 90%+ 작으면서 시각 품질 손실이 거의 없다. |
| Product 화면의 작은 pixel 마스코트 위젯 아이콘 | PNG (또는 WebP) | 아주 작은 아이콘이라 형식보다 실제 렌더 크기에 맞춘 dimension이 더 중요하다. |

**절대 하지 않는 것**: PNG/JPEG를 `<image href="data:image/png;base64,...">`로 감싸기만 한
"SVG"를 최적화된 벡터처럼 취급하지 않는다. Figma 등에서 내보낸 파일이 실제로 `<path>`/`<rect>`
등 vector 요소로 구성돼 있는지 반드시 열어서 확인한 뒤에만 SVG로 채택한다. (2026-09 정리에서
`public/` 루트에 있던 7개 SVG가 전부 이 케이스였다 — 전부 삭제하고 이미 추출되어 있던 raster
버전만 유지했다.)

## 크기

- 소스 asset의 pixel dimension은 실제 화면에 렌더링되는 최대 크기의 2~3배(레티나 대응)를
  넘지 않게 한다. 예: 150px 너비로 보여줄 로고에 2000px가 넘는 원본을 그대로 쓰지 않는다.
- 여러 화면에서 같은 파일을 다른 크기로 쓴다면, 그 중 **가장 큰** 표시 크기를 기준으로
  한 벌만 만든다(화면마다 별도 파일을 만들지 않는다).

## 네이밍

- `lowercase-kebab-case.ext`를 기본으로 한다 (`catcher-hero.webp`, `catcher-happy.png`).
- 기존 파일 이름을 바꿀 때는 그 변경 하나로 모든 코드 참조(`grep -rn`으로 확인)를 함께
  갱신한다 — 이름만 바꾸고 참조를 나중에 고치는 중간 상태를 남기지 않는다.
- **Windows 개발 환경 주의**: NTFS는 대소문자를 구분하지 않는다. `Foo.png` → `foo.png`처럼
  대소문자만 바꾸는 rename은 `mv`/파일 저장만으로는 git에 반영되지 않을 수 있다(같은 파일로
  덮어써질 뿐). git에 실제로 대소문자가 다른 새 경로로 인식시키려면
  `git rm --cached <old>` 후 `git add <new>`를 명시적으로 실행한다 — 이 과정을 건너뛰면
  git 인덱스는 옛 대문자 경로를 그대로 들고 있다가, 대소문자를 구분하는 배포 환경(Linux 서버,
  Vercel 등)에서 코드가 참조하는 소문자 경로가 404가 나는 사고로 이어진다.

## 폴더

- `brand/` — 로고.
- `mascot/` — 캐릭터 "캐쳐" 이미지. 랜딩/온보딩용 3D 렌더(`catcher-hero.webp`)와 Product 화면
  우측 하단 위젯용 작은 아이콘(`catcher.png`/`catcher-happy.png`)은 스타일이 다른 별개
  asset이다 — 하나로 통일하지 않는다.
- `landing/gallery/` — Landing 전용 아트워크.
- `icons/` — 커스텀 아이콘. 실제 파일이 없으면 빈 폴더를 미리 만들지 않는다.

빈 파일이 없는데 새 최상위 폴더를 만들지 않는다 — 위 4개 폴더 중 맞는 곳이 없다면, 정말 새
카테고리가 필요한지 먼저 확인한다.

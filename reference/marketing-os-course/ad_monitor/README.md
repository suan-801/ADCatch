# ad-monitor — 독립 광고 모니터링 스킬

> `02-competitor-from-adlib` 스킬을 기반으로 만든 **독립형** 버전. `Claudecode_MarketingOS_student` 프로젝트의
> 01_brand/02_competitor/03_customer/04_brief 등 어떤 산출물도 참조하지 않습니다 — 이 폴더 하나만으로 완결됩니다.

## 뭐가 다른가 (원본 02 스킬 대비)

1. **자사·경쟁사 구분 없음** — URL 을 넣으면 그게 뭐든 똑같이 분석 대상. `##` 그룹 라벨은 자유 텍스트(선택).
2. **UTM/트래킹 파라미터 관찰** — 랜딩 URL에서 `utm_*`·`fbclid`·`gclid` 등을 추출해 브랜드별 표로 정리. 캠페인/그룹/소재명 규칙을 코드가 "확정"하지 않고, 관찰 데이터를 근거로 실행 시 Claude 가 베스트에포트로 유추(정확도는 브랜드마다 다를 수 있음 — SKILL.md Step 7 참고).
3. **자체 자격증명** — `ad_monitor/.env` 전용 파일 (09_tracking/.env 와 별개).
4. **구글독스 공유** — 실행마다 새 독스 문서를 만들어 팀원과 공유 (링크가 매번 바뀜 — 고정 링크로 "업데이트"가 필요하면 SKILL.md 참고).

## 빠른 시작

```bash
# 1) 자격증명 채우기 (이미 값이 들어있음 — 09_tracking/.env 에서 복사됨)
#    필요하면 ad_monitor/.env 직접 수정

# 2) URL 등록
#    ad_monitor/_inputs/urls.md 열어서 Meta 광고 라이브러리 URL 한 줄 추가

# 3) 실행
python3 ad_monitor/_scripts/fetch_ads.py

# 4) 로컬 대시보드
python3 ad_monitor/_scripts/build_dashboard.py
# → ad_monitor/dashboard/index.html 더블클릭

# 5) 통합 리포트
# → ad_monitor/ads_report.md (자동 생성)
```

## Claude Code 에서 쓰는 법

이 저장소 안에서는 `.claude/skills/ad-monitor/SKILL.md` 로 등록되어 있어 자연어로도 트리거됩니다:
- "이 URL 광고 모니터링해줘"
- "독립적으로 광고 분석해줘"
- "/ad-monitor"

다른 프로젝트에서 쓰고 싶다면 `ad_monitor/` 폴더 전체 + `.claude/skills/ad-monitor/` 폴더를 그대로 복사하면 됩니다 (외부 의존 없음).

## 폴더 구조

```
ad_monitor/
├── .env                      # 자격증명 (커밋 ❌)
├── .env.example
├── README.md                 # (이 파일)
├── ads_report.md             # ★ 통합 트렌드 리포트 (자동 생성)
├── _inputs/
│   ├── urls.md                # ★ 사용자가 편집하는 유일한 파일
│   └── {slug}.md              # 자동 생성 시드 (추적용)
├── _scripts/
│   ├── ad_inputs.py
│   ├── fetch_ads.py            # 메인 실행 스크립트
│   ├── utm_pattern.py
│   └── build_dashboard.py
├── _reference/
│   └── analysis_method.md     # USP 3항목 + Creative Key Visual + ad_pattern 정의
├── {slug}/
│   └── ad-creatives/{metadata.json, analysis.json, utm_samples.json, images/, videos/, keyframes/}
└── dashboard/                 # 로컬 HTML 대시보드 (자동 생성)
```

## 현실적으로 어려운 부분 (미리 알아두면 좋은 것)

- **UTM 규칙 유추는 베스트에포트** — 경쟁사 URL 은 리다이렉트/클릭ID만 있고 utm 값이 아예 없는 경우가 흔합니다. 자사 URL 은 신뢰도가 높지만, 경쟁사는 낮을 수 있습니다.
- **구글독스는 "새 문서 생성" 방식** — 지금 연결된 도구로는 기존 문서의 본문을 덮어쓰는 게 불가능해, 실행마다 새 문서를 만들고 공유합니다. 링크가 실행마다 바뀝니다. 고정 링크가 필요하면 별도 서비스 계정 + Docs API 설정이 필요합니다 (SKILL.md 참고).
- **Gemini 무료 티어 250 RPD** — 광고가 많으면 하루에 다 못 돌 수 있습니다. `--paid` 플래그로 유료 키 사용 가능.

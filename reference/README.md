# reference/ — 참고 전용 자료 (앱 코드가 여기를 import하지 않음)

이 폴더는 실제 ADCatcher 애플리케이션 코드가 아닙니다. 아이디어/코드 패턴을 참고하기 위해 보관하는 자료이며, 실제 제품 기획은 루트의 `PRD.MD` + `.cursorrules`가 유일한 기준입니다.

## marketing-os-course/
"클로드코드로 만드는 심플한 퍼포먼스 마케팅 OS" 강의의 수강생용 워크스페이스 템플릿(원래 폴더명: `Claudecode_MarketingOS_student_Your Brand_0629`)을 통째로 옮겨온 것입니다. ADCatcher와는 별개의 프로젝트지만, 이 안의 `02_competitor/_scripts/fetch_competitor_ads.py`에 있는 **Apify(facebook-ads-library-scraper) 호출 + Gemini Vision REST 분석** 코드 패턴을 ADCatcher의 광고 수집기(`apps/api/app/services/ad_library_collector.py`)에 그대로 이식했습니다.

## adetect-reference/
위 강의 워크스페이스 안에 있던 `adetect_reference.zip`을 압축 해제한 사본입니다. 이 자료는 "ADetect"라는 **ADCatcher와는 다른 컨셉의 제품**(브랜드명+경쟁사 입력 → 1회성 AI 분석 리포트, 다크+골드 UI)을 위해 준비된 코드/디자인 번들이며, 그 제품의 상세 기획서(`new_prd.md`)는 이 저장소에 없습니다.

**ADCatcher는 이 ADetect 컨셉을 채택하지 않았습니다.** (2026-09-17, 제품 방향 확인 완료 — PRD.MD의 데일리 트래커로 진행) 다만 `scrapers/fetch_competitor_ads.py`의 Apify/Gemini 호출 코드는 marketing-os-course와 동일 계열이라 교차 확인용으로 남겨두고, `templates_sample/ui_ref.png`(다크+골드 UI 목업)는 ADCatcher의 UI 방향(라이트 미니멀)과 무관하므로 참고하지 마세요.

## original-docs/
프로젝트 초기에 루트에 있던 `collector_spec.py` 원본(인터페이스 스펙, 구현 없음)을 그대로 보관합니다. 실제 구현은 `apps/api/app/schemas.py` + `apps/api/app/services/`에 있습니다.

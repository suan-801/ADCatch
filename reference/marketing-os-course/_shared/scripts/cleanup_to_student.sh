#!/usr/bin/env bash
# cleanup_to_student.sh
# Performance Marketing OS 워크스페이스를 캐롯글로우 완성본 → 수강생용 초기 템플릿으로 정리한다.
#
# 사용법:
#   ./_shared/scripts/cleanup_to_student.sh --dry-run   # 무엇이 지워지는지 미리 확인
#   ./_shared/scripts/cleanup_to_student.sh             # 실제 실행
#
# 처리 대상:
#   A. 라이브 자격증명 5종 (.mcp.json, 09_tracking/.env 등) → 삭제 + 플레이스홀더 교체
#   B. 캐롯글로우 산출물 (01~08) → 삭제, 폴더 스켈레톤 유지
#   C. 캐롯글로우 데이터 (10~12) + 포맷 견본 (variants/, sample_brand/) → 삭제
#   D. 캐시·메모리 (.playwright-mcp/, .claude/agent-memory/, __pycache__/, .DS_Store) → 삭제
#   E. 인프라 (_shared/, .agents/, .claude/skills/, README/가이드 다수) → 유지

set -euo pipefail

DRY="${1:-}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

if [[ "$DRY" == "--dry-run" ]]; then
  echo "=== DRY-RUN 모드 (실제 삭제하지 않음) ==="
fi

run() {
  if [[ "$DRY" == "--dry-run" ]]; then
    echo "[DRY] $*"
  else
    eval "$@"
  fi
}

say() { printf "\n▸ %s\n" "$*"; }

#############################################
# A. 보안 — 라이브 자격증명 삭제
#############################################
say "A. 라이브 자격증명 삭제"
run "rm -f .mcp.json"
run "rm -f 09_tracking/.env"
run "rm -f 09_tracking/.env.backup-*"
run "rm -f 09_tracking/oauth-client.json"
run "rm -f 09_tracking/client_secret_*.json"

#############################################
# B. 캐롯글로우 산출물 삭제 (01~08)
#############################################
say "B1. 01_brand — brand_brief, 자산 삭제 (스켈레톤 유지)"
run "rm -f 01_brand/brand_brief.md"
run "rm -rf 01_brand/_source"
run "rm -f 01_brand/logos/*.png 01_brand/logos/*.jpg 01_brand/logos/*.svg"
run "rm -f 01_brand/products/main-angles/*.png 01_brand/products/main-angles/*.jpg"
run "rm -f 01_brand/products/lifestyle/*.png 01_brand/products/lifestyle/*.jpg"
run "rm -f 01_brand/products/studio/*.png 01_brand/products/studio/*.jpg"

say "B2. 02_competitor — 분석본·경쟁사 폴더·인풋 삭제 (스킬 인프라 유지)"
run "rm -f 02_competitor/competitor_ads.md"
run "rm -f 02_competitor/_inputs/competitors.md"
# _inputs 안의 경쟁사별 .md (README.md 만 남기고 나머지 .md 삭제)
run "find 02_competitor/_inputs -mindepth 1 -maxdepth 1 -type f -name '*.md' ! -name 'README.md' -delete"
run "rm -rf 02_competitor/dashboard"
# 경쟁사 슬러그 폴더 (_inputs / _reference / _scripts 제외)
run "find 02_competitor -mindepth 1 -maxdepth 1 -type d ! -name '_inputs' ! -name '_reference' ! -name '_scripts' -exec rm -rf {} +"
run "rm -rf 02_competitor/_scripts/__pycache__"

say "B3. 03_customer — 페인포인트·인풋·리뷰·워드클라우드·크롤러 캐시 삭제"
run "rm -f 03_customer/pain_points.md"
run "rm -f 03_customer/_inputs/reviews_pdp.md"
run "find 03_customer/reviews -mindepth 1 -maxdepth 1 -type f ! -name 'README.md' -delete"
run "rm -f 03_customer/visuals/*.png"
run "rm -f 03_customer/visuals/*.csv"
run "rm -rf 03_customer/outputs"
run "rm -rf 03_customer/_scripts/__pycache__"

say "B4. 04_brief — 합성본·archive 캠페인 삭제 (README + 템플릿 유지)"
run "rm -f 04_brief/confirmed_brief.md"
run "rm -rf 04_brief/research"
run "mkdir -p 04_brief/research"
# archive 안에서 _template-original.md 만 남기고 캠페인 brief 모두 삭제
run "find 04_brief/archive -mindepth 1 -maxdepth 1 -type f -name '*.md' ! -name '_template-original.md' -delete"

say "B5. 05_ad_image — 캐롯글로우 캠페인 서브폴더 10개 전부 삭제"
run "find 05_ad_image -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +"

say "B6. 06_ad_video — 캐롯글로우 캠페인 서브폴더 + 영상제작플랜.md 삭제"
run "find 06_ad_video -mindepth 1 -maxdepth 1 -type d -exec rm -rf {} +"
run "rm -f 06_ad_video/영상제작플랜.md"

say "B7. 07_carousel — 캐롯글로우 2폴더 + carrot23-secret(캐롯글로우 변형) 삭제. 벤치마크 5폴더 유지"
run "rm -rf 07_carousel/2026-05-26_carrotglow-daily-safe-glow"
run "rm -rf 07_carousel/2026-05-26_carrotglow-morning-glow-routine"
run "rm -rf 07_carousel/carrot23-secret"

say "B8. 08_landing — 캐롯글로우 캠페인 3폴더 삭제 (README 유지)"
run "rm -rf 08_landing/carrotglow-home"
run "rm -rf 08_landing/carrotglow-launch-tester"
run "rm -rf 08_landing/2026-05-26_carrotglow-pyeongchang-farm-june"

#############################################
# C. 데이터 폴더 (10~12)
#############################################
say "C1. 10_daily — 캐롯글로우 + 포맷 견본 모두 삭제"
run "rm -rf 10_daily/carrotglow"
run "rm -rf 10_daily/sample_brand"

say "C2. 11_dashboard — ETL·시트·대시보드·CRO·추천·variants 삭제 (setup·README·_build_sheets.py 유지)"
run "rm -rf 11_dashboard/etl"
run "rm -f 11_dashboard/sheets/*.csv"
run "rm -rf 11_dashboard/dashboards"
run "rm -rf 11_dashboard/cro"
run "rm -rf 11_dashboard/recommendations"
run "rm -rf 11_dashboard/variants"

say "C3. 12_period — 캐롯글로우 리포트 삭제"
run "rm -rf 12_period/carrotglow"

#############################################
# D. 캐시·메모리·로그
#############################################
say "D. 캐시·메모리·임시 파일 삭제"
run "rm -rf .playwright-mcp"
run "rm -rf .claude/agent-memory"
run "find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true"
run "find . -name .DS_Store -type f -delete 2>/dev/null || true"
run "rm -rf _shared/logs/* 2>/dev/null || true"

#############################################
# E. 플레이스홀더 .mcp.json 재생성
#############################################
say "E. 플레이스홀더 .mcp.json 작성"
if [[ "$DRY" == "--dry-run" ]]; then
  echo "[DRY] write .mcp.json with YOUR_*_HERE placeholders"
else
  cat > .mcp.json <<'JSON'
{
  "mcpServers": {
    "nanobanana": {
      "command": "uvx",
      "args": ["nanobanana-mcp-server@latest"],
      "env": {
        "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY_HERE"
      }
    },
    "analytics-mcp": {
      "command": "pipx",
      "args": ["run", "analytics-mcp"],
      "env": {
        "GOOGLE_PROJECT_ID": "YOUR_GCP_PROJECT_ID_HERE"
      }
    },
    "clarity": {
      "command": "npx",
      "args": ["-y", "@microsoft/clarity-mcp-server"],
      "env": {
        "CLARITY_API_TOKEN": "YOUR_CLARITY_API_TOKEN_HERE",
        "CLARITY_PROJECT_ID": "YOUR_CLARITY_PROJECT_ID_HERE"
      }
    },
    "playwright": {
      "command": "npx",
      "args": ["-y", "@playwright/mcp@latest"]
    },
    "perplexity": {
      "command": "npx",
      "args": ["-y", "server-perplexity-ask"],
      "env": {
        "PERPLEXITY_API_KEY": "YOUR_PERPLEXITY_API_KEY_HERE"
      }
    },
    "meta-ads": {
      "type": "http",
      "url": "https://mcp.facebook.com/ads"
    }
  }
}
JSON
fi

#############################################
# F. 빈 산출물 폴더 보장 (mkdir -p)
#############################################
say "F. 빈 산출물 폴더 보장"
for d in \
  01_brand/logos \
  01_brand/products/main-angles \
  01_brand/products/lifestyle \
  01_brand/products/studio \
  04_brief/research \
  04_brief/archive \
  05_ad_image \
  06_ad_video \
  08_landing \
  10_daily \
  12_period; do
  run "mkdir -p \"$d\""
done

echo
echo "============================================"
if [[ "$DRY" == "--dry-run" ]]; then
  echo "  DRY-RUN 완료. 실제 실행은 인자 없이 다시 호출."
else
  echo "  ✓ 수강생 워크스페이스 정리 완료"
  echo ""
  echo "  다음 단계:"
  echo "  1. .mcp.json 의 YOUR_*_HERE 값을 본인 키로 교체"
  echo "  2. 09_tracking/.env.example 을 09_tracking/.env 로 복사 후 채우기"
  echo "  3. /09-tracking-setup 으로 GA4·Clarity·Meta 연결"
  echo "  4. /01-brand-from-url <본인 도메인> 부터 강의 시작"
fi
echo "============================================"

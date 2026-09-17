#!/bin/bash
# ============================================================
# GA4 OAuth + ADC 로그인 헬퍼 (★ 디폴트 트랙)
# ============================================================
#
# 본 OS 의 GA4 디폴트 트랙은 OAuth ADC — 본 스크립트가 그 진입점.
# 서비스 계정 트랙은 cron 무인 운영·자산 격리 필요 시만 사용 (가이드 § 9 부록 A).
#
# 사용 시점:
# - 최초 GA4 연결 셋업 (1회)
# - OAuth refresh token 만료 후 재로그인 (수개월 1회)
#
# 사전 준비: 09_tracking/oauth-client.json (Desktop OAuth Client JSON)
# 상세: 09_tracking/GA4_연결_가이드.md § 5
# ============================================================

# 스크립트 위치 기준 자동 경로 — 어디서 실행하든 동작 (사용자명·폴더명 무관)
SD="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OAUTH_CLIENT_JSON="$SD/oauth-client.json"

if [ ! -f "$OAUTH_CLIENT_JSON" ]; then
  echo "❌ OAuth client JSON not found: $OAUTH_CLIENT_JSON"
  echo "→ GA4 디폴트 트랙(서비스 계정)을 쓰고 있다면 본 스크립트 호출 불필요."
  echo "→ 부록 트랙이 필요하면 가이드 § 9.2 에서 oauth-client.json 발급."
  exit 1
fi

gcloud auth application-default login \
  --client-id-file="$OAUTH_CLIENT_JSON" \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform

#!/bin/bash
# ADC 재인증 — 기존 analytics + cloud-platform 스코프 유지 + spreadsheets + drive 추가
# 사용: bash 09_tracking/_reauth_with_sheets.sh
# 브라우저 열리면 본인 구글 계정 선택 → 권한 동의

gcloud auth application-default login \
  --client-id-file=/Users/hyeongtaekim/Desktop/Claudecode_MarketingOS_student/09_tracking/oauth-client.json \
  --scopes=https://www.googleapis.com/auth/analytics.readonly,https://www.googleapis.com/auth/cloud-platform,https://www.googleapis.com/auth/spreadsheets,https://www.googleapis.com/auth/drive

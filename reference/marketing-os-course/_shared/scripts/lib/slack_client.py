"""Slack Incoming Webhook 래퍼 — 텍스트 한 줄, dry-run 모드 지원."""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Optional


class SlackClient:
    def __init__(self, webhook_url: Optional[str] = None, dry_run: bool = False):
        self.webhook_url = webhook_url
        self.dry_run = dry_run or not webhook_url

    def send(self, text: str) -> bool:
        if self.dry_run:
            print(f"[DRY-RUN slack] {len(text)}자 메시지 — 발송 skip")
            return True
        data = json.dumps({"text": text}).encode("utf-8")
        req = urllib.request.Request(
            self.webhook_url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                ok = 200 <= resp.status < 300
                if not ok:
                    print(f"❌ Slack 발송 실패 status={resp.status}")
                return ok
        except urllib.error.URLError as e:
            print(f"❌ Slack 발송 에러: {e}")
            return False

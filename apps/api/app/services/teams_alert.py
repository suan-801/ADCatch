"""Microsoft Teams Incoming Webhook 알림.

reference/marketing-os-course 의 레퍼런스에는 Slack 알림(_shared/scripts/daily_slack.py)만 있어
그대로 이식할 코드가 없다 — PRD 4장 요구사항(Teams Webhook Alert)에 맞춰 새로 작성했다.
"""

import httpx

from app.config import settings
from app.schemas import SyncResult


def _build_message_card(project_name: str, results: list[SyncResult], top_survivor: str | None) -> dict:
    # P0-17: "신규 소재"는 DB INSERT 건수가 아니라 실제 STARTED 이벤트 기준으로 센다.
    # is_baseline=True인 run의 new_ads는 "오늘 켠 광고"가 아니라 "처음 확인한 기존 집행 소재"이므로
    # 별도 항목으로 분리해서 알리고, 신규 소재 합계에는 포함하지 않는다.
    total_started = sum(r.new_ads for r in results if not r.is_baseline)
    total_baseline_discovered = sum(r.new_ads for r in results if r.is_baseline)
    total_inactive = sum(r.newly_inactive for r in results)

    facts = [
        {"name": "신규 소재", "value": f"{total_started}건"},
        {"name": "종료 소재", "value": f"{total_inactive}건"},
    ]
    if total_baseline_discovered:
        facts.append({"name": "처음 확인한 기존 소재(Baseline)", "value": f"{total_baseline_discovered}건"})
    if top_survivor:
        facts.append({"name": "최고 장수 소재", "value": top_survivor})

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensible-card",
        "summary": f"ADCatcher 일일 수집 요약 — {project_name}",
        "themeColor": "0F172A",
        "title": f"📦 ADCatcher — {project_name} 일일 수집 완료",
        "sections": [{"facts": facts, "markdown": True}],
    }


def send_daily_summary(project_name: str, results: list[SyncResult], top_survivor: str | None = None) -> bool:
    """일일 수집 완료 후 Teams 채널로 요약 알림을 보낸다. webhook 미설정 시 조용히 스킵."""
    if not settings.teams_webhook_url:
        return False

    payload = _build_message_card(project_name, results, top_survivor)
    resp = httpx.post(settings.teams_webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    return True

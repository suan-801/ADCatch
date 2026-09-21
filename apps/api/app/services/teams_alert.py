"""Microsoft Teams Incoming Webhook 알림.
"""

import httpx

from app.config import settings
from app.schemas import SyncResult


def _build_message_card(
    project_name: str,
    results: list[SyncResult],
    top_survivor: str | None,
) -> dict:
    # 실제 신규 광고만 집계
    total_started = sum(r.new_ads for r in results if not r.is_baseline)

    # 최초 수집 시 발견된 기존 광고
    total_baseline_discovered = sum(
        r.new_ads for r in results if r.is_baseline
    )

    # 새롭게 종료된 광고
    total_inactive = sum(r.newly_inactive for r in results)

    # 변화가 있는지에 따라 문구 변경
    if total_started == 0 and total_inactive == 0:
        title = f"🐈‍⬛ [AD Catcher] {project_name} 오늘은 조용해요 🐾"
        subtitle = "오늘 새롭게 포착된 변화가 없어요."
    else:
        title = f"🐈‍⬛ [AD Catcher] {project_name} 변화를 Catch했어요 🐾"
        subtitle = "오늘 포착한 광고 변화를 알려드릴게요!"

    facts = [
        {
            "name": "🆕 신규 소재",
            "value": f"**{total_started}건**",
        },
        {
            "name": "⏹️ 종료 소재",
            "value": f"**{total_inactive}건**",
        },
    ]

    if total_baseline_discovered:
        facts.append({
            "name": "🔎 최초 확인 소재",
            "value": f"**{total_baseline_discovered}건**",
        })

    if top_survivor:
        facts.append({
            "name": "🏆 최고 장수 소재",
            "value": top_survivor,
        })

    return {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensible-card",
        "summary": f"AD Catcher 일일 수집 요약 — {project_name}",
        "themeColor": "111827",
        "title": title,
        "text": subtitle,
        "sections": [
            {
                "facts": facts,
                "markdown": True,
            }
        ],
    }


def send_daily_summary(project_name: str, results: list[SyncResult], top_survivor: str | None = None) -> bool:
    """일일 수집 완료 후 Teams 채널로 요약 알림을 보낸다. webhook 미설정 시 조용히 스킵."""
    if not settings.teams_webhook_url:
        return False

    payload = _build_message_card(project_name, results, top_survivor)
    resp = httpx.post(settings.teams_webhook_url, json=payload, timeout=15)
    resp.raise_for_status()
    return True

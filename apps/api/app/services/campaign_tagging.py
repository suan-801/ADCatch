"""Gemini 기반 Campaign Tag 자동 분류.

app.services.vision_tagging의 REST 호출/쿼터 예외 패턴을 그대로 재사용한다. visual_type(4분류)과
달리 이 분류는 프로젝트마다 사용자가 정의한 태그 집합을 입력으로 받으므로, 프롬프트에 각 태그의
id/name/definition을 그대로 넣고, 응답의 campaign_tag_id가 그 집합에 없으면 무조건 버린다 —
Gemini가 임의의 새 태그를 만들어내는 것을 원천 차단한다("반드시 제공된 태그 중 하나만 선택").

image_url은 신규 재다운로드한다(app.services.media.process_ad_image의 시그니처는 바꾸지 않는다 —
기존 test_ad_change_history.py의 monkeypatch 계약을 보호하기 위함). 비용 트레이드오프는 구현
보고서의 "남은 제한사항"에 기록한다.
"""

import base64
import json

import httpx

from app.config import settings
from app.schemas import CampaignTagOut
from app.services.vision_tagging import GEMINI_BASE, GeminiQuotaExceeded, _is_quota_error

PROMPT_TEMPLATE = """아래 광고를 사용자가 정의한 캠페인 분류 중 가장 적절한 하나로 분류하세요.

분류 기준(반드시 아래 목록의 id 중 하나만 선택. 목록에 없는 id를 만들어내지 마세요):
{tags_json}

광고 카피: {copy_text}
CTA: {cta_text}

충분히 판단하기 어려우면 억지로 분류하지 말고 campaign_tag_id를 null로 반환하세요.

다음 JSON 형식으로만 답하세요:
{{"campaign_tag_id": "<목록의 id 중 하나 또는 null>", "confidence": 0.00, "reason": "짧은 판단 근거"}}"""


def _build_prompt(copy_text: str | None, cta_text: str | None, active_tags: list[CampaignTagOut]) -> str:
    tags_payload = [{"id": str(t.id), "name": t.name, "definition": t.definition} for t in active_tags]
    return PROMPT_TEMPLATE.format(
        tags_json=json.dumps(tags_payload, ensure_ascii=False, indent=2),
        copy_text=copy_text or "(없음)",
        cta_text=cta_text or "(없음)",
    )


def classify_campaign_tag(
    image_url: str | None,
    copy_text: str | None,
    cta_text: str | None,
    active_tags: list[CampaignTagOut],
) -> tuple[str | None, float | None, str | None]:
    """대표 이미지를 자체적으로 다운로드해(app.services.media.process_ad_image의 시그니처는
    바꾸지 않기 위해 독립적으로 1회 재다운로드 — 비용 트레이드오프는 구현 보고서 참고) Gemini에
    보내고 (campaign_tag_id | None, confidence, reason)을 반환한다. 다운로드 실패는 예외를 던지지
    않고 (None, None, None)으로 폴백한다 — Gemini 쿼터 초과(GeminiQuotaExceeded)만 호출자에게
    전파한다(호출자가 이미 광범위 try/except로 감싸므로 격리에 문제 없음).

    2026-09: image_url이 없어도 copy_text/cta_text 중 하나라도 있으면 텍스트만으로 분류를
    시도한다(멀티모달 image part를 생략하고 텍스트 전용 요청을 보낸다) — 이미지가 아직
    캐싱되지 않았거나 원본이 텍스트 위주 소재인 경우에도 분류 기회를 준다. 셋 다 없으면 Gemini를
    호출하지 않는다.

    호출자(app.services.ad_sync._enrich_one, app.services.pending_campaign_classification 등)가
    결과를 status로 변환한다:
      - campaign_tag_id가 active_tags 집합에 없으면 이미 여기서 None으로 강등해 반환한다.
      - confidence 임계값 판정은 호출자가 settings.campaign_tag_confidence_threshold로 수행한다
        (이 함수는 순수 분류만 담당 — 상태 전이 로직은 상위 레이어의 책임으로 분리).
    """
    if not settings.gemini_api_key or not active_tags:
        return None, None, None
    if not image_url and not copy_text and not cta_text:
        return None, None, None

    image_part: dict | None = None
    if image_url:
        try:
            resp = httpx.get(image_url, timeout=30)
            resp.raise_for_status()
        except httpx.HTTPError:
            return None, None, None
        b64 = base64.b64encode(resp.content).decode()
        mime_type = resp.headers.get("content-type", "image/jpeg")
        image_part = {"inline_data": {"mime_type": mime_type, "data": b64}}

    allowed_ids = {str(t.id) for t in active_tags}
    prompt = _build_prompt(copy_text, cta_text, active_tags)
    parts: list[dict] = [{"text": prompt}]
    if image_part is not None:
        parts.append(image_part)
    url = f"{GEMINI_BASE}/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }

    resp = httpx.post(url, json=body, timeout=60)
    if resp.status_code >= 400:
        if _is_quota_error(resp.status_code, resp.text):
            raise GeminiQuotaExceeded(resp.text[:200])
        resp.raise_for_status()

    data = resp.json()
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
        tag_id = parsed.get("campaign_tag_id")
        confidence = parsed.get("confidence")
        reason = parsed.get("reason")
    except (KeyError, IndexError, ValueError, json.JSONDecodeError):
        return None, None, None

    # Gemini가 임의로 지어낸(혹은 이미 비활성화된) 태그 id는 무조건 버린다 — 반드시 프로젝트의
    # active tag 중 하나여야 한다.
    if tag_id is None or str(tag_id) not in allowed_ids:
        return None, confidence, reason

    return str(tag_id), confidence, reason

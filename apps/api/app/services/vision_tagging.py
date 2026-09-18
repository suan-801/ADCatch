"""Gemini Vision 기반 비주얼 태깅.

Gemini REST 호출/재시도/쿼터 예외 처리 패턴은
reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py 의
gemini_analyze_image() 를 참고했다. 다만 그 레퍼런스는 USP 3항목 + ad_pattern 등
카피라이팅용 5단계 분석까지 하는 무거운 프롬프트였고, ADCatcher(PRD 4장)는
"인물 포함 / 텍스트 중심 / 제품 중심 / 그래픽" 4분류만 필요하므로 프롬프트와
JSON 스키마를 그 범위로 축소했다.
"""

import base64
import json

import httpx

from app.config import settings
from app.schemas import VisualType

GEMINI_BASE = "https://generativelanguage.googleapis.com"

TAGGING_PROMPT = """이 광고 이미지를 보고 다음 4가지 카테고리 중 가장 지배적인 하나를 고르세요.

- PERSON: 사람(모델/인물)이 이미지의 중심 요소인 경우
- PRODUCT: 제품 자체가 중심(단독 컷, 패키지, 디테일 샷)인 경우
- TEXT_HEAVY: 카피/텍스트가 이미지 면적의 상당 부분을 차지하는 경우
- GRAPHIC: 일러스트/아이콘/그래픽 요소 중심, 실사 촬영이 아닌 경우

JSON으로만 답하세요: {"visual_type": "PERSON" | "PRODUCT" | "TEXT_HEAVY" | "GRAPHIC"}"""


class GeminiQuotaExceeded(Exception):
    pass


def _is_quota_error(status_code: int, body: str) -> bool:
    if status_code == 429:
        return True
    if status_code == 403:
        upper = body.upper()
        return "QUOTA" in upper or "EXCEEDED" in upper or "RESOURCE_EXHAUSTED" in upper
    return False


def analyze_visual_type(image_bytes: bytes, mime_type: str = "image/jpeg") -> VisualType | None:
    if not settings.gemini_api_key:
        return None

    b64 = base64.b64encode(image_bytes).decode()
    url = f"{GEMINI_BASE}/v1beta/models/{settings.gemini_model}:generateContent?key={settings.gemini_api_key}"
    body = {
        "contents": [
            {
                "parts": [
                    {"text": TAGGING_PROMPT},
                    {"inline_data": {"mime_type": mime_type, "data": b64}},
                ]
            }
        ],
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
        return VisualType(parsed["visual_type"])
    except (KeyError, IndexError, ValueError, json.JSONDecodeError):
        return None

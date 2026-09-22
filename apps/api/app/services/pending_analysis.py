"""Part A — Gemini Pending Analysis Retry.

app.services.ad_sync._enrich_new_ads_concurrently 는 "이번에 처음 발견된" 소재만 enrichment
대상으로 삼는다. 그래서 첫 수집에서 Gemini quota/일시 오류로 analysis_status=PENDING인 채로
남은 광고는, 다음 수집부터는 더 이상 new_items가 아니므로 영구히 미분석 상태로 남을 수 있다.

이 모듈은 PENDING 소재만 따로 골라 Gemini 재분석을 재시도한다. Core Collection(ad_sync)과는
완전히 독립적으로 동작하며, 여기서 발생하는 어떤 예외/quota 초과도 호출자의 워크플로우를
실패시키지 않는다(P0-07과 동일한 원칙 — enrichment는 항상 core data보다 낮은 우선순위).

이미 analysis_status=SUCCESS인 광고는 이 모듈이 절대 다시 Gemini를 호출하지 않는다(쿼리 자체가
PENDING만 대상으로 함).
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad, Competitor
from app.services import vision_tagging
from app.services.timing import stage_timer

logger = logging.getLogger("adcatcher.pending_analysis")


@dataclass
class PendingAnalysisSummary:
    processed: int = 0
    succeeded: int = 0
    still_pending: int = 0
    failed: int = 0
    quota_stopped: bool = False


def _retry_one(image_url: str):
    """(visual_type, error_message, quota_exceeded)를 반환한다. 절대 예외를 던지지 않는다."""
    try:
        resp = httpx.get(image_url, timeout=30)
        resp.raise_for_status()
    except httpx.HTTPError as e:
        return None, str(e)[:500], False

    content_type = resp.headers.get("content-type", "image/jpeg")
    try:
        visual_type = vision_tagging.analyze_visual_type(resp.content, content_type)
        return visual_type, None, False
    except vision_tagging.GeminiQuotaExceeded as e:
        return None, str(e)[:500], True


def process_pending_analysis(
    db: Session,
    *,
    competitor_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    limit: int | None = None,
) -> PendingAnalysisSummary:
    """PENDING 소재를 oldest-first로 골라 Gemini 재분석을 재시도한다.

    - 성공: analysis_status=SUCCESS, visual_type 갱신, analysis_error=NULL, analyzed_at=now
    - quota 초과: 이번 배치를 즉시 graceful stop한다 — 이미 처리된 성공 결과는 그대로 저장되고,
      이 소재를 포함한 나머지는 PENDING 그대로 유지된다(재시도 횟수도 늘리지 않는다).
    - 그 외 실패: analysis_retry_count += 1, analysis_error 갱신. 임계값(gemini_analysis_max_retries)
      초과 시 analysis_status=FAILED로 확정한다.

    project_id를 넘기면 그 프로젝트 소속 경쟁사의 소재만 대상으로 한다(대시보드의 "분석 업데이트"
    버튼 — 다른 프로젝트의 PENDING 소재가 함께 처리되면 안 된다)."""
    batch_limit = limit if limit is not None else settings.gemini_pending_batch_size

    query = select(Ad).where(Ad.analysis_status == "PENDING", Ad.image_url.is_not(None))
    if competitor_id is not None:
        query = query.where(Ad.competitor_id == competitor_id)
    if project_id is not None:
        query = query.where(Ad.competitor_id.in_(select(Competitor.id).where(Competitor.project_id == project_id)))
    query = query.order_by(Ad.first_seen_at.asc()).limit(batch_limit)

    pending_ads = db.scalars(query).all()
    summary = PendingAnalysisSummary()

    for ad in pending_ads:
        with stage_timer("pending_gemini_retry", ad_archive_id=ad.ad_archive_id):
            visual_type, error, quota_exceeded = _retry_one(ad.image_url)

        if quota_exceeded:
            summary.quota_stopped = True
            logger.info(
                "gemini quota exceeded during pending retry — stopping batch (processed=%d)",
                summary.processed,
            )
            break

        summary.processed += 1
        if visual_type is not None:
            ad.analysis_status = "SUCCESS"
            ad.visual_type = visual_type.value
            ad.analysis_error = None
            ad.analyzed_at = datetime.now(timezone.utc)
            summary.succeeded += 1
        else:
            ad.analysis_retry_count += 1
            ad.analysis_error = error
            if ad.analysis_retry_count >= settings.gemini_analysis_max_retries:
                ad.analysis_status = "FAILED"
                summary.failed += 1
            else:
                summary.still_pending += 1
        db.commit()

    return summary

"""Campaign Tag Pending Classification Retry — app.services.pending_analysis와 동일한 모양.

app.services.ad_sync._enrich_one은 "이번에 처음 발견된" 소재만 동기적으로 분류한다. 이 모듈은
campaign_classification_status=PENDING인 소재만 따로 골라 재시도한다. Core Collection과 완전히
독립적으로 동작하며, 여기서 발생하는 어떤 예외/quota 초과도 호출자의 워크플로우를 실패시키지 않는다.

이 쿼리는 assignment_source를 전혀 확인하지 않는다 — status만 본다. USER가 직접 지정한 소재는
campaign_classification_status가 이미 SUCCESS로 고정되어 있어 이 쿼리 대상이 아니다. 재분류
(app.routers.campaign_tags의 POST .../reclassify)가 명시적으로 include_user_assigned=true를
선택했을 때만 USER 소재를 PENDING으로 되돌리며, 그 순간부터는 이 배치가 똑같이 처리한다.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad, Competitor
from app.schemas import CampaignTagOut
from app.services import campaign_tagging
from app.services.campaign_tags import list_active_campaign_tags
from app.services.timing import stage_timer
from app.services.vision_tagging import GeminiQuotaExceeded

logger = logging.getLogger("adcatcher.pending_campaign_classification")


@dataclass
class PendingCampaignClassificationSummary:
    processed: int = 0
    succeeded: int = 0
    needs_review: int = 0
    still_pending: int = 0
    failed: int = 0
    quota_stopped: bool = False


def _project_id_for_competitor(db: Session, competitor_id: uuid.UUID) -> uuid.UUID | None:
    return db.scalar(select(Competitor.project_id).where(Competitor.id == competitor_id))


def process_pending_campaign_classification(
    db: Session,
    *,
    competitor_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    limit: int | None = None,
) -> PendingCampaignClassificationSummary:
    """PENDING 소재를 oldest-first로 골라 Gemini 캠페인 분류를 재시도한다.

    project_id를 넘기면 그 프로젝트 소속 경쟁사의 소재만 대상으로 한다(§2-3 "지금 재분류 실행" —
    다른 프로젝트의 PENDING 광고가 함께 처리되면 안 된다). competitor_id와 동시에 지정하면 둘 다
    만족하는 소재만 대상이 된다(둘 다 굳이 함께 쓸 일은 없지만 배타적이지 않게 둔다).

    - 정상 분류(confidence >= threshold): classification_status=SUCCESS, campaign_tag_id/
      confidence/reason 갱신, assignment_source=AI.
    - 애매(confidence 낮음/태그 미확정이지만 Gemini는 응답함): classification_status=NEEDS_REVIEW,
      campaign_tag_id=NULL, confidence/reason은 유지(디버깅/화면 표시용), assignment_source=AI.
    - quota 초과: 이번 배치를 즉시 graceful stop한다 — 이미 처리된 결과는 그대로 저장되고, 나머지는
      PENDING 그대로 유지된다(재시도 횟수도 늘리지 않는다).
    - 완전한 실패(이미지 다운로드 실패 등, Gemini 응답 자체가 없음): retry_count += 1. 임계값
      (campaign_classification_max_retries) 초과 시 FAILED로 확정.
    - 활성 태그가 0개인 프로젝트의 소재는 애초에 대상에서 제외한다(불필요한 Gemini 호출 방지,
      실패로 세지 않고 PENDING 그대로 둔다).
    """
    batch_limit = limit if limit is not None else settings.campaign_classification_pending_batch_size

    # §2-6: image_url이 없어도 copy_text/cta_text 중 하나라도 있으면 텍스트만으로 분류를 시도할
    # 수 있다(campaign_tagging.classify_campaign_tag가 image part 없이도 요청을 보낸다) — 셋 다
    # 없는 소재만 후보에서 제외한다.
    query = select(Ad).where(
        Ad.campaign_classification_status == "PENDING",
        or_(Ad.image_url.is_not(None), Ad.copy_text.is_not(None), Ad.cta_text.is_not(None)),
    )
    if competitor_id is not None:
        query = query.where(Ad.competitor_id == competitor_id)
    if project_id is not None:
        query = query.where(Ad.competitor_id.in_(select(Competitor.id).where(Competitor.project_id == project_id)))
    # 활성 태그가 0개인 프로젝트의 소재는 스킵되므로, batch_limit보다 넉넉히 후보를 가져온다.
    query = query.order_by(Ad.first_seen_at.asc()).limit(batch_limit * 3)

    candidates = db.scalars(query).all()
    summary = PendingCampaignClassificationSummary()
    active_tags_cache: dict[uuid.UUID, list[CampaignTagOut]] = {}

    for ad in candidates:
        if summary.processed >= batch_limit:
            break

        project_id = _project_id_for_competitor(db, ad.competitor_id)
        if project_id is None:
            continue
        if project_id not in active_tags_cache:
            active_tags_cache[project_id] = [
                CampaignTagOut.model_validate(t) for t in list_active_campaign_tags(db, project_id)
            ]
        active_tags = active_tags_cache[project_id]
        if not active_tags:
            continue

        try:
            with stage_timer("pending_campaign_classification", ad_archive_id=ad.ad_archive_id):
                tag_id, confidence, reason = campaign_tagging.classify_campaign_tag(
                    ad.image_url, ad.copy_text, ad.cta_text, active_tags
                )
        except GeminiQuotaExceeded:
            summary.quota_stopped = True
            logger.info(
                "gemini quota exceeded during campaign classification retry — stopping batch (processed=%d)",
                summary.processed,
            )
            break

        summary.processed += 1

        if tag_id is None and confidence is None and reason is None:
            # 완전한 실패(이미지 다운로드 실패, Gemini 응답 파싱 실패 등) — Gemini가 판단 자체를
            # 내리지 못한 경우다.
            ad.campaign_classification_retry_count += 1
            ad.campaign_classification_error = "이미지 다운로드 또는 Gemini 응답 파싱 실패"
            if ad.campaign_classification_retry_count >= settings.campaign_classification_max_retries:
                ad.campaign_classification_status = "FAILED"
                summary.failed += 1
            else:
                summary.still_pending += 1
        elif tag_id is not None and confidence is not None and confidence >= settings.campaign_tag_confidence_threshold:
            ad.campaign_tag_id = uuid.UUID(tag_id)
            ad.campaign_tag_confidence = confidence
            ad.campaign_tag_reason = reason
            ad.campaign_tag_assignment_source = "AI"
            ad.campaign_tag_classified_at = datetime.now(timezone.utc)
            ad.campaign_classification_status = "SUCCESS"
            ad.campaign_classification_error = None
            summary.succeeded += 1
        else:
            # Gemini는 응답했지만 확신이 낮거나(threshold 미달) 태그를 확정하지 못함 — 억지 분류
            # 대신 검토 필요 상태로 남긴다.
            ad.campaign_tag_id = None
            ad.campaign_tag_confidence = confidence
            ad.campaign_tag_reason = reason
            ad.campaign_tag_assignment_source = "AI"
            ad.campaign_tag_classified_at = datetime.now(timezone.utc)
            ad.campaign_classification_status = "NEEDS_REVIEW"
            ad.campaign_classification_error = None
            summary.needs_review += 1

        db.commit()

    return summary

"""광고 상태 동기화 — NEW / ACTIVE / INACTIVE 판정 + 생존일수 추적.

reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py 는 매 실행마다
metadata.json을 통째로 덮어쓸 뿐 이전 실행과 비교하지 않는다 (신규/종료 감지 로직 없음, 조사 확인 완료).
AdCatch는 PRD 3.2/3.3, collector_spec.py 의 synchronize_ad_status 설계에 따라 이 로직을 새로 구현한다.

규칙:
  - 이번 수집에서 처음 발견된 ad_archive_id → NEW, first_seen_at = last_seen_at = now
  - 기존에 추적 중이었고 이번에도 발견됨 → ACTIVE, last_seen_at = now, consecutive_inactive_days = 0
  - 기존에 추적 중이었으나 이번엔 미발견 → INACTIVE, consecutive_inactive_days += 1
  - consecutive_inactive_days >= archive_after_inactive_days → is_archived = True (다음 수집 대상에서 제외)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad
from app.schemas import AdStatus, RawAdItem, SyncResult
from app.services import media


def synchronize_ad_status(
    db: Session,
    competitor_id: uuid.UUID,
    fetched_ads: list[RawAdItem],
    tag_visual: bool = True,
) -> SyncResult:
    now = datetime.now(timezone.utc)

    existing_ads = db.scalars(
        select(Ad).where(Ad.competitor_id == competitor_id, Ad.is_archived.is_(False))
    ).all()
    existing_by_archive_id = {ad.ad_archive_id: ad for ad in existing_ads}
    fetched_by_archive_id = {item.ad_archive_id: item for item in fetched_ads}

    new_count = 0
    kept_active_count = 0
    newly_inactive_count = 0
    newly_archived_count = 0

    # 1) 이번에 발견된 소재 → NEW 생성 또는 기존 소재 ACTIVE 갱신
    for ad_archive_id, item in fetched_by_archive_id.items():
        existing = existing_by_archive_id.get(ad_archive_id)
        if existing is None:
            image_url = item.image_url
            visual_type = None
            if tag_visual and item.image_url:
                # 다운로드 1회로 Supabase Storage 캐싱 + Gemini Vision 태깅을 함께 수행 (PRD 3.3/4장)
                image_url, visual_type = media.process_ad_image(competitor_id, ad_archive_id, item.image_url)
            db.add(
                Ad(
                    competitor_id=competitor_id,
                    ad_archive_id=ad_archive_id,
                    status=AdStatus.NEW.value,
                    visual_type=visual_type.value if visual_type else None,
                    format=item.format.value,
                    image_url=image_url,
                    copy_text=item.copy_text,
                    cta_text=item.cta_text,
                    first_seen_at=now,
                    last_seen_at=now,
                    consecutive_inactive_days=0,
                )
            )
            new_count += 1
        else:
            existing.status = AdStatus.ACTIVE.value
            existing.last_seen_at = now
            existing.consecutive_inactive_days = 0
            kept_active_count += 1

    # 2) 기존에 추적 중이었으나 이번엔 미발견 → INACTIVE, 14일 연속 미노출 시 아카이빙
    for ad_archive_id, existing in existing_by_archive_id.items():
        if ad_archive_id in fetched_by_archive_id:
            continue
        existing.status = AdStatus.INACTIVE.value
        existing.consecutive_inactive_days += 1
        newly_inactive_count += 1
        if existing.consecutive_inactive_days >= settings.archive_after_inactive_days:
            existing.is_archived = True
            newly_archived_count += 1

    db.commit()

    return SyncResult(
        competitor_id=competitor_id,
        new_ads=new_count,
        reactivated_or_kept_active=kept_active_count,
        newly_inactive=newly_inactive_count,
        newly_archived=newly_archived_count,
    )

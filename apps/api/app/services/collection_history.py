"""Daily Ad Change History — 수집 실행 기록(collection_runs) 생명주기 관리 +
날짜별 광고 변화 조회(ad-changes API가 사용).

설계 원칙 (요청 브리핑 Part A 그대로):
  - "collection 실패"와 "경쟁사가 광고를 모두 껐음"을 혼동하지 않는다.
    → 비교는 항상 직전 SUCCESS run 기준 (ad_sync.synchronize_ad_status가
      기존 ads 테이블 상태를 그대로 diff 기준으로 쓰므로, FAILED/RUNNING run은
      애초에 ads 테이블을 건드리지 않아 자동으로 이 규칙을 만족한다).
  - STOPPED는 상태 "전환이 발생한 순간"에만 1건 기록한다 (반복 기록 금지).
  - 날짜는 KST(Asia/Seoul) 캘린더 기준으로 고정 저장 — 조회 시 TIMESTAMPTZ→DATE
    변환이나 substring 비교를 하지 않고 단순 동등비교만 하면 되도록 한다.
"""

import uuid
from collections import Counter
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from app.models import Ad, AdObservation, AdStatusEvent, CollectionRun, Competitor
from app.schemas import (
    AdChangeEventType,
    AdChangesResponse,
    AdChangeSummary,
    ChangedAdOut,
    CollectionStatus,
)

KST = timezone(timedelta(hours=9))


def today_kst() -> date:
    return datetime.now(KST).date()


def start_collection_run(db: Session, competitor_id: uuid.UUID, run_date: date | None = None) -> CollectionRun:
    """run_date를 명시적으로 넘기면 그 날짜로 기록한다 (테스트에서 여러 날짜를 시뮬레이션할 때 사용;
    운영 호출부는 항상 생략해 today_kst()를 그대로 쓴다)."""
    run = CollectionRun(competitor_id=competitor_id, run_date=run_date or today_kst(), status="RUNNING")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run


def fail_collection_run(db: Session, run: CollectionRun, error_message: str) -> None:
    run.status = "FAILED"
    run.completed_at = datetime.now(timezone.utc)
    run.error_message = error_message[:2000]
    db.commit()


def record_event(
    db: Session,
    *,
    ad_id: uuid.UUID,
    competitor_id: uuid.UUID,
    collection_run_id: uuid.UUID,
    event_type: str,
    event_date: date,
    previous_status: str | None,
    new_status: str,
) -> None:
    db.add(
        AdStatusEvent(
            ad_id=ad_id,
            competitor_id=competitor_id,
            collection_run_id=collection_run_id,
            event_type=event_type,
            event_date=event_date,
            previous_status=previous_status,
            new_status=new_status,
        )
    )


def record_observation(db: Session, *, collection_run_id: uuid.UUID, competitor_id: uuid.UUID, ad_id: uuid.UUID) -> None:
    db.add(AdObservation(collection_run_id=collection_run_id, competitor_id=competitor_id, ad_id=ad_id))


def complete_collection_run_success(db: Session, run: CollectionRun, fetched_ads_count: int) -> None:
    run.status = "SUCCESS"
    run.completed_at = datetime.now(timezone.utc)
    run.fetched_ads_count = fetched_ads_count


def _competitor_ids_for_scope(db: Session, project_id: uuid.UUID, competitor_id: uuid.UUID | None) -> list[uuid.UUID]:
    if competitor_id is not None:
        return [competitor_id]
    # 자사(own brand) 소재는 기존 dashboard 집계와 동일하게 제외한다.
    return list(
        db.scalars(
            select(Competitor.id).where(Competitor.project_id == project_id, Competitor.is_own_brand.is_(False))
        ).all()
    )


def get_ad_changes(
    db: Session,
    project_id: uuid.UUID,
    target_date: date,
    competitor_id: uuid.UUID | None,
) -> AdChangesResponse:
    competitor_ids = _competitor_ids_for_scope(db, project_id, competitor_id)

    if not competitor_ids:
        return AdChangesResponse(
            project_id=project_id,
            date=target_date,
            competitor_id=competitor_id,
            collection_status=CollectionStatus.NO_RECORD,
            history_available_from=None,
            summary=AdChangeSummary(started=0, reactivated=0, stopped=0),
            started_ads=[],
            reactivated_ads=[],
            stopped_ads=[],
            visual_pattern={},
        )

    # 1) 이 날짜의 수집 상태 (성공/실패/기록없음) — backend에서 날짜 필터링 처리.
    runs_today = db.scalars(
        select(CollectionRun).where(
            CollectionRun.competitor_id.in_(competitor_ids),
            CollectionRun.run_date == target_date,
        )
    ).all()
    if any(r.status == "SUCCESS" for r in runs_today):
        collection_status = CollectionStatus.SUCCESS
    elif any(r.status == "FAILED" for r in runs_today):
        collection_status = CollectionStatus.FAILED
    else:
        collection_status = CollectionStatus.NO_RECORD

    history_available_from = db.scalar(
        select(sa_func.min(CollectionRun.run_date)).where(CollectionRun.competitor_id.in_(competitor_ids))
    )

    # 2) 이 날짜에 발생한 이벤트 (STARTED / STOPPED / REACTIVATED) — DB에서 직접 필터링.
    rows = db.execute(
        select(AdStatusEvent, Ad, Competitor.name)
        .join(Ad, AdStatusEvent.ad_id == Ad.id)
        .join(Competitor, AdStatusEvent.competitor_id == Competitor.id)
        .where(
            AdStatusEvent.competitor_id.in_(competitor_ids),
            AdStatusEvent.event_date == target_date,
        )
        .order_by(Ad.first_seen_at.desc())
    ).all()

    started: list[ChangedAdOut] = []
    reactivated: list[ChangedAdOut] = []
    stopped: list[ChangedAdOut] = []
    visual_counter: Counter[str] = Counter()

    for event, ad, competitor_name in rows:
        changed = ChangedAdOut(
            id=ad.id,
            competitor_id=ad.competitor_id,
            ad_archive_id=ad.ad_archive_id,
            status=ad.status,
            visual_type=ad.visual_type,
            format=ad.format,
            image_url=ad.image_url,
            copy_text=ad.copy_text,
            cta_text=ad.cta_text,
            first_seen_at=ad.first_seen_at,
            last_seen_at=ad.last_seen_at,
            consecutive_inactive_days=ad.consecutive_inactive_days,
            is_archived=ad.is_archived,
            event_type=event.event_type,
            competitor_name=competitor_name,
        )
        if event.event_type == AdChangeEventType.STARTED.value:
            started.append(changed)
            if ad.visual_type:
                visual_counter[ad.visual_type] += 1
        elif event.event_type == AdChangeEventType.REACTIVATED.value:
            reactivated.append(changed)
            if ad.visual_type:
                visual_counter[ad.visual_type] += 1
        elif event.event_type == AdChangeEventType.STOPPED.value:
            stopped.append(changed)

    return AdChangesResponse(
        project_id=project_id,
        date=target_date,
        competitor_id=competitor_id,
        collection_status=collection_status,
        history_available_from=history_available_from,
        summary=AdChangeSummary(started=len(started), reactivated=len(reactivated), stopped=len(stopped)),
        started_ads=started,
        reactivated_ads=reactivated,
        stopped_ads=stopped,
        visual_pattern=dict(visual_counter),
    )

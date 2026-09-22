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
    AdChangesRangeResponse,
    AdChangesResponse,
    AdChangeSummary,
    AdHistoryEvent,
    ChangedAdOut,
    CollectionFreshness,
    CollectionRunSummary,
    CollectionStatus,
    CollectionStatusSummary,
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
    survival_days_at_event: int | None = None,
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
            survival_days_at_event=survival_days_at_event,
        )
    )


def record_observation(db: Session, *, collection_run_id: uuid.UUID, competitor_id: uuid.UUID, ad_id: uuid.UUID) -> None:
    db.add(AdObservation(collection_run_id=collection_run_id, competitor_id=competitor_id, ad_id=ad_id))


def complete_collection_run_success(db: Session, run: CollectionRun, fetched_ads_count: int) -> None:
    run.status = "SUCCESS"
    run.completed_at = datetime.now(timezone.utc)
    run.fetched_ads_count = fetched_ads_count


def complete_collection_run_partial(db: Session, run: CollectionRun, fetched_ads_count: int) -> None:
    """P0-02: max_ads 상한에 도달해 스냅샷이 잘렸을 수 있는 경우. STOPPED 판정에는 사용되지 않는다."""
    run.status = "PARTIAL"
    run.completed_at = datetime.now(timezone.utc)
    run.fetched_ads_count = fetched_ads_count


def _competitor_ids_for_scope(db: Session, project_id: uuid.UUID, competitor_id: uuid.UUID | None) -> list[uuid.UUID]:
    if competitor_id is not None:
        return [competitor_id]
    # P0-18/P0-19: Brand Model Simplification — Project 안의 모든 등록 브랜드는 동일하게 취급된다.
    # is_own_brand 기준 제외는 더 이상 하지 않는다.
    return list(db.scalars(select(Competitor.id).where(Competitor.project_id == project_id)).all())


def _collection_status_for_competitor_on_date(db: Session, competitor_id: uuid.UUID, target_date: date) -> CollectionStatus:
    statuses = db.scalars(
        select(CollectionRun.status).where(
            CollectionRun.competitor_id == competitor_id,
            CollectionRun.run_date == target_date,
        )
    ).all()
    if any(s == "SUCCESS" for s in statuses):
        return CollectionStatus.SUCCESS
    if any(s == "PARTIAL" for s in statuses):
        return CollectionStatus.PARTIAL
    if any(s == "FAILED" for s in statuses):
        return CollectionStatus.FAILED
    return CollectionStatus.NO_RECORD


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
            collection_summary=CollectionStatusSummary(success=0, partial=0, failed=0, no_record=0),
            history_available_from=None,
            baseline_discovered_count=0,
            summary=AdChangeSummary(started=0, reactivated=0, stopped=0),
            started_ads=[],
            reactivated_ads=[],
            stopped_ads=[],
            visual_pattern={},
        )

    # 1) 이 날짜의 수집 상태 — P0-15: 브랜드가 여럿일 때 "하나라도 SUCCESS면 전체 SUCCESS"로
    # 뭉개지 않는다. 브랜드별 상태를 먼저 구하고, 전부 같을 때만 그 상태로, 섞여 있으면 PARTIAL로 집계한다.
    per_competitor_status = [_collection_status_for_competitor_on_date(db, cid, target_date) for cid in competitor_ids]
    status_counts = Counter(per_competitor_status)
    total = len(per_competitor_status)
    collection_summary = CollectionStatusSummary(
        success=status_counts.get(CollectionStatus.SUCCESS, 0),
        partial=status_counts.get(CollectionStatus.PARTIAL, 0),
        failed=status_counts.get(CollectionStatus.FAILED, 0),
        no_record=status_counts.get(CollectionStatus.NO_RECORD, 0),
    )
    if collection_summary.success == total:
        collection_status = CollectionStatus.SUCCESS
    elif collection_summary.failed == total:
        collection_status = CollectionStatus.FAILED
    elif collection_summary.no_record == total:
        collection_status = CollectionStatus.NO_RECORD
    else:
        collection_status = CollectionStatus.PARTIAL

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
    baseline_count = 0
    visual_counter: Counter[str] = Counter()

    for event, ad, competitor_name in rows:
        # P0-03: baseline은 "오늘 켠 광고"가 아니므로 켠/끈 집계 및 visual pattern에서 제외한다.
        if event.event_type == AdChangeEventType.BASELINE_DISCOVERED.value:
            baseline_count += 1
            continue

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
            source_started_at=ad.source_started_at,
            consecutive_inactive_days=ad.consecutive_inactive_days,
            is_archived=ad.is_archived,
            event_type=event.event_type,
            competitor_name=competitor_name,
            survival_days_at_event=event.survival_days_at_event,
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
        collection_summary=collection_summary,
        history_available_from=history_available_from,
        baseline_discovered_count=baseline_count,
        summary=AdChangeSummary(started=len(started), reactivated=len(reactivated), stopped=len(stopped)),
        started_ads=started,
        reactivated_ads=reactivated,
        stopped_ads=stopped,
        visual_pattern=dict(visual_counter),
    )


def _changed_ad_out(ad: Ad, event: AdStatusEvent, competitor_name: str) -> ChangedAdOut:
    """이벤트 1건 + 그 시점 Ad row로 ChangedAdOut을 만든다. get_ad_changes()/get_ad_changes_range()가
    공유한다 — 두 함수 모두 캠페인 태그/미디어 필드까지 포함한 동일한 필드셋을 내려준다."""
    return ChangedAdOut(
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
        source_started_at=ad.source_started_at,
        consecutive_inactive_days=ad.consecutive_inactive_days,
        is_archived=ad.is_archived,
        event_type=event.event_type,
        competitor_name=competitor_name,
        survival_days_at_event=event.survival_days_at_event,
        event_date=event.event_date,
        campaign_tag_id=ad.campaign_tag_id,
        campaign_tag_confidence=ad.campaign_tag_confidence,
        campaign_tag_reason=ad.campaign_tag_reason,
        campaign_tag_assignment_source=ad.campaign_tag_assignment_source,
        campaign_tag_classified_at=ad.campaign_tag_classified_at,
        campaign_classification_status=ad.campaign_classification_status,
        video_url=ad.video_url,
        media_items=ad.media_items or [],
        keyframe_urls=ad.keyframe_urls or [],
        keyframe_status=ad.keyframe_status,
    )


def get_ad_changes_range(
    db: Session,
    project_id: uuid.UUID,
    start_date: date,
    end_date: date,
    competitor_id: uuid.UUID | None,
) -> AdChangesRangeResponse:
    """§6 — 기간(주간) 조회. 기존 get_ad_changes()는 건드리지 않는다(단일 날짜 계약 보존).

    collection_status를 (경쟁사×날짜) 그리드로 억지로 뭉개 단일 값으로 만들지 않는다 — "자동수집을
    켜지 않은 날"의 기록 없음이 "실패"처럼 보이는 것을 방지하기 위해, 실제 CollectionRun 시도만
    status별로 집계한 collection_run_summary + 시도가 있었던 날짜 목록(dates_with_collection)을
    반환한다. 프론트는 이 값과 기존 CollectionFreshness를 함께 보여준다.

    visual_pattern/campaign_mix는 unique 광고 기준으로 집계한다(동일 광고가 기간 내
    STARTED+REACTIVATED를 모두 가져도 1회만 카운트) — 변화 목록(started_ads 등)은 이벤트 기준으로
    그대로 나열해 event history 의미를 보존한다(동일 광고의 여러 이벤트를 dedupe하지 않는다).
    """
    competitor_ids = _competitor_ids_for_scope(db, project_id, competitor_id)

    if not competitor_ids:
        return AdChangesRangeResponse(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            competitor_id=competitor_id,
            collection_run_summary=CollectionRunSummary(success=0, partial=0, failed=0),
            dates_with_collection=[],
            latest_collection_at=None,
            history_available_from=None,
            baseline_discovered_count=0,
            summary=AdChangeSummary(started=0, reactivated=0, stopped=0),
            started_ads=[],
            reactivated_ads=[],
            stopped_ads=[],
            visual_pattern={},
            campaign_mix={},
        )

    # 1) "이 데이터를 믿어도 되는가" — 실제 시도한 CollectionRun만 집계(그리드 채우기 없음).
    runs = db.scalars(
        select(CollectionRun).where(
            CollectionRun.competitor_id.in_(competitor_ids),
            CollectionRun.run_date.between(start_date, end_date),
        )
    ).all()
    run_status_counts = Counter(r.status for r in runs)
    collection_run_summary = CollectionRunSummary(
        success=run_status_counts.get("SUCCESS", 0),
        partial=run_status_counts.get("PARTIAL", 0),
        failed=run_status_counts.get("FAILED", 0),
    )
    dates_with_collection = sorted({r.run_date for r in runs})
    completed_ats = [r.completed_at for r in runs if r.completed_at is not None]
    latest_collection_at = max(completed_ats) if completed_ats else None

    history_available_from = db.scalar(
        select(sa_func.min(CollectionRun.run_date)).where(CollectionRun.competitor_id.in_(competitor_ids))
    )

    # 2) 이 기간에 발생한 이벤트 — event_date 기준 범위 조회(양끝 inclusive).
    rows = db.execute(
        select(AdStatusEvent, Ad, Competitor.name)
        .join(Ad, AdStatusEvent.ad_id == Ad.id)
        .join(Competitor, AdStatusEvent.competitor_id == Competitor.id)
        .where(
            AdStatusEvent.competitor_id.in_(competitor_ids),
            AdStatusEvent.event_date.between(start_date, end_date),
        )
        .order_by(AdStatusEvent.event_date.desc(), Ad.first_seen_at.desc())
    ).all()

    started: list[ChangedAdOut] = []
    reactivated: list[ChangedAdOut] = []
    stopped: list[ChangedAdOut] = []
    baseline_count = 0
    # STARTED/REACTIVATED가 있었던 광고를 ad_id로 dedupe — visual_pattern/campaign_mix는 이 집합
    # 기준으로 unique하게 집계한다(이벤트 기준이 아님).
    unique_started_or_reactivated: dict[uuid.UUID, Ad] = {}

    for event, ad, competitor_name in rows:
        if event.event_type == AdChangeEventType.BASELINE_DISCOVERED.value:
            baseline_count += 1
            continue

        changed = _changed_ad_out(ad, event, competitor_name)
        if event.event_type == AdChangeEventType.STARTED.value:
            started.append(changed)
            unique_started_or_reactivated[ad.id] = ad
        elif event.event_type == AdChangeEventType.REACTIVATED.value:
            reactivated.append(changed)
            unique_started_or_reactivated[ad.id] = ad
        elif event.event_type == AdChangeEventType.STOPPED.value:
            stopped.append(changed)

    visual_counter: Counter[str] = Counter()
    campaign_counter: Counter[str] = Counter()
    for ad in unique_started_or_reactivated.values():
        if ad.visual_type:
            visual_counter[ad.visual_type] += 1
        if ad.campaign_tag_id and ad.campaign_classification_status == "SUCCESS":
            campaign_counter[str(ad.campaign_tag_id)] += 1
        else:
            campaign_counter["NEEDS_REVIEW"] += 1

    return AdChangesRangeResponse(
        project_id=project_id,
        start_date=start_date,
        end_date=end_date,
        competitor_id=competitor_id,
        collection_run_summary=collection_run_summary,
        dates_with_collection=dates_with_collection,
        latest_collection_at=latest_collection_at,
        history_available_from=history_available_from,
        baseline_discovered_count=baseline_count,
        summary=AdChangeSummary(started=len(started), reactivated=len(reactivated), stopped=len(stopped)),
        started_ads=started,
        reactivated_ads=reactivated,
        stopped_ads=stopped,
        visual_pattern=dict(visual_counter),
        campaign_mix=dict(campaign_counter),
    )


def get_ad_history(db: Session, ad_id: uuid.UUID) -> list[AdHistoryEvent]:
    """Part C-03 — 광고 1건의 STARTED/STOPPED/REACTIVATED/BASELINE_DISCOVERED 이력을
    오래된 순으로 반환한다. 기존 Daily Changes API(get_ad_changes)는 건드리지 않는다."""
    events = db.scalars(
        select(AdStatusEvent).where(AdStatusEvent.ad_id == ad_id).order_by(AdStatusEvent.event_date.asc())
    ).all()
    return [AdHistoryEvent.model_validate(e) for e in events]


def get_freshness_summary(db: Session, project_id: uuid.UUID) -> CollectionFreshness:
    """P0-09/P0-16: 프로젝트 헤더 근처에 표시할 데이터 신뢰도 요약 — 각 브랜드의 "가장 최근" 수집
    시도만 보고 판단한다 (오래된 실패 이력이 최신 성공을 가리지 않도록). P0-18/19: is_own_brand로
    제외하지 않고 프로젝트 내 모든 브랜드를 대상으로 한다.

    §13-4 성능 최적화: 경쟁사마다 개별 쿼리(N+1)를 날리는 대신, window function으로 경쟁사별
    "가장 최근 run"을 단일 쿼리로 조회한다(결과 값의 의미는 기존 구현과 동일)."""
    competitors = db.scalars(select(Competitor).where(Competitor.project_id == project_id)).all()
    if not competitors:
        return CollectionFreshness(
            project_id=project_id,
            latest_run_at=None,
            total_competitors=0,
            healthy_competitors=0,
            success_competitors=0,
            partial_competitors=0,
            partial_competitor_names=[],
            failed_competitor_names=[],
        )

    competitor_ids = [c.id for c in competitors]
    name_by_id = {c.id: c.name for c in competitors}

    row_number = sa_func.row_number().over(
        partition_by=CollectionRun.competitor_id, order_by=CollectionRun.started_at.desc()
    ).label("rn")
    ranked = (
        select(CollectionRun.competitor_id, CollectionRun.status, CollectionRun.completed_at, row_number)
        .where(CollectionRun.competitor_id.in_(competitor_ids))
        .subquery()
    )
    latest_by_competitor = {
        row.competitor_id: row
        for row in db.execute(
            select(ranked.c.competitor_id, ranked.c.status, ranked.c.completed_at).where(ranked.c.rn == 1)
        ).all()
    }

    latest_run_at: datetime | None = None
    success = 0
    partial = 0
    partial_names: list[str] = []
    failed_names: list[str] = []

    for cid in competitor_ids:
        name = name_by_id[cid]
        latest_run = latest_by_competitor.get(cid)
        if latest_run is None:
            failed_names.append(name)
            continue
        if latest_run.completed_at and (latest_run_at is None or latest_run.completed_at > latest_run_at):
            latest_run_at = latest_run.completed_at
        if latest_run.status == "SUCCESS":
            success += 1
        elif latest_run.status == "PARTIAL":
            partial += 1
            partial_names.append(name)
        else:
            failed_names.append(name)

    return CollectionFreshness(
        project_id=project_id,
        latest_run_at=latest_run_at,
        total_competitors=len(competitors),
        healthy_competitors=success + partial,
        success_competitors=success,
        partial_competitors=partial,
        partial_competitor_names=partial_names,
        failed_competitor_names=failed_names,
    )

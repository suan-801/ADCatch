"""광고 상태 동기화 — NEW / ACTIVE / INACTIVE 판정 + 생존일수 추적.

reference/marketing-os-course/02_competitor/_scripts/fetch_competitor_ads.py 는 매 실행마다
metadata.json을 통째로 덮어쓸 뿐 이전 실행과 비교하지 않는다 (신규/종료 감지 로직 없음, 조사 확인 완료).
ADCatcher는 PRD 3.2/3.3, collector_spec.py 의 synchronize_ad_status 설계에 따라 이 로직을 새로 구현한다.

규칙:
  - 이번 수집에서 처음 발견된 ad_archive_id → NEW, first_seen_at = last_seen_at = now
  - 기존에 추적 중이었고 이번에도 발견됨 → ACTIVE, last_seen_at = now, consecutive_inactive_days = 0
  - 기존에 추적 중이었으나 이번엔 미발견 → INACTIVE, consecutive_inactive_days += 1
  - consecutive_inactive_days >= archive_after_inactive_days → is_archived = True (다음 수집 대상에서 제외)
  - 아카이빙된 광고도 같은 ad_archive_id로 재등장하면 새 row를 만들지 않고 기존 row를 복원한다 (P0-04)

Daily Ad Change History (additive, 2026-09): 이 함수는 반드시 성공한 fetch 이후에만 호출되므로
(예외 발생 시 라우터/스케줄러가 애초에 이 함수를 호출하지 않음), 위 두 루프에서 일어나는 diff가
곧 "직전 SUCCESS/PARTIAL 상태 vs 이번 수집" 비교 그 자체다. 각 상태 "전환이 발생한 순간"에만
STARTED/STOPPED/REACTIVATED 이벤트를 1건씩 기록한다 (collection_run은 호출자가 미리 생성해서 넘긴다).

안정화(2026-09, Product Stabilization spec) 추가 규칙:
  - P0-02 snapshot_complete=False(=max_ads 상한 도달로 스냅샷이 잘렸을 가능성) 인 경우,
    "미발견 → STOPPED" 추론 자체를 건너뛴다. 발견된 소재의 STARTED/ACTIVE/REACTIVATED 갱신은
    그대로 유효하므로 정상 수행한다.
  - P0-03 이 경쟁사의 첫 성공/부분성공 수집(baseline)에서는 STARTED 대신 BASELINE_DISCOVERED를
    기록한다 — "오늘 갑자기 N개를 켰다"는 거짓 신호를 만들지 않기 위함.
  - P0-07 Gemini/썸네일 캐싱(enrichment) 실패가 수집(core data) 자체를 무효화해서는 안 된다.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad, CollectionRun
from app.schemas import AdChangeEventType, AdStatus, RawAdItem, SyncResult
from app.services import collection_history, media


def _is_baseline_collection(db: Session, competitor_id: uuid.UUID, current_run_id: uuid.UUID) -> bool:
    prior_success = db.scalar(
        select(CollectionRun.id)
        .where(
            CollectionRun.competitor_id == competitor_id,
            CollectionRun.status.in_(["SUCCESS", "PARTIAL"]),
            CollectionRun.id != current_run_id,
        )
        .limit(1)
    )
    return prior_success is None


def synchronize_ad_status(
    db: Session,
    competitor_id: uuid.UUID,
    fetched_ads: list[RawAdItem],
    collection_run: CollectionRun,
    tag_visual: bool = True,
    snapshot_complete: bool = True,
) -> SyncResult:
    now = datetime.now(timezone.utc)
    event_date = collection_run.run_date
    is_baseline = _is_baseline_collection(db, competitor_id, collection_run.id)

    # P0-04: 아카이빙된 광고도 ad_archive_id가 재등장할 수 있으므로, is_archived 필터 없이
    # 전부 불러와 "완전히 새로운 광고"와 "재등장한 기존 row"를 정확히 구분한다.
    existing_ads = db.scalars(select(Ad).where(Ad.competitor_id == competitor_id)).all()
    existing_by_archive_id = {ad.ad_archive_id: ad for ad in existing_ads}
    fetched_by_archive_id = {item.ad_archive_id: item for item in fetched_ads}

    new_count = 0
    kept_active_count = 0
    newly_inactive_count = 0
    newly_archived_count = 0

    # 1) 이번에 발견된 소재 → NEW 생성 또는 기존 소재(아카이빙 포함) ACTIVE 갱신
    for ad_archive_id, item in fetched_by_archive_id.items():
        existing = existing_by_archive_id.get(ad_archive_id)
        if existing is None:
            image_url = item.image_url
            visual_type = None
            analysis_status = "PENDING"
            analysis_error = None
            analyzed_at = None
            if tag_visual and item.image_url:
                # P0-07: enrichment(캐싱+Gemini)는 core data(수집)와 완전히 분리한다.
                # 여기서 어떤 예외가 나든 이 광고 row 생성과 나머지 처리는 계속돼야 한다.
                try:
                    image_url, visual_type = media.process_ad_image(competitor_id, ad_archive_id, item.image_url)
                    analysis_status = "SUCCESS" if visual_type else "PENDING"
                    analyzed_at = now
                except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 격리
                    image_url = item.image_url
                    visual_type = None
                    analysis_status = "FAILED"
                    analysis_error = str(e)[:500]
                    analyzed_at = now

            new_ad_id = uuid.uuid4()
            db.add(
                Ad(
                    id=new_ad_id,
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
                    source_started_at=item.start_date,
                    consecutive_inactive_days=0,
                    analysis_status=analysis_status,
                    analysis_error=analysis_error,
                    analyzed_at=analyzed_at,
                )
            )
            new_count += 1
            collection_history.record_event(
                db,
                ad_id=new_ad_id,
                competitor_id=competitor_id,
                collection_run_id=collection_run.id,
                event_type=(
                    AdChangeEventType.BASELINE_DISCOVERED.value if is_baseline else AdChangeEventType.STARTED.value
                ),
                event_date=event_date,
                previous_status=None,
                new_status=AdStatus.NEW.value,
            )
            collection_history.record_observation(
                db, collection_run_id=collection_run.id, competitor_id=competitor_id, ad_id=new_ad_id
            )
        else:
            previous_status = existing.status
            existing.status = AdStatus.ACTIVE.value
            existing.last_seen_at = now
            existing.consecutive_inactive_days = 0
            existing.is_archived = False  # P0-04: 재등장한 아카이빙 광고 복원 (신규 row 생성 안 함)
            kept_active_count += 1
            # INACTIVE(아카이빙된 광고 포함, is_archived=True는 항상 status=INACTIVE를 동반함)였던
            # 광고가 다시 발견된 경우에만 REACTIVATED. 계속 노출 중이던 광고는 새 이벤트 없음.
            if previous_status == AdStatus.INACTIVE.value:
                collection_history.record_event(
                    db,
                    ad_id=existing.id,
                    competitor_id=competitor_id,
                    collection_run_id=collection_run.id,
                    event_type=AdChangeEventType.REACTIVATED.value,
                    event_date=event_date,
                    previous_status=previous_status,
                    new_status=AdStatus.ACTIVE.value,
                )
            collection_history.record_observation(
                db, collection_run_id=collection_run.id, competitor_id=competitor_id, ad_id=existing.id
            )

    # 2) 기존에 추적 중이었으나 이번엔 미발견 → INACTIVE, 14일 연속 미노출 시 아카이빙.
    # P0-02: snapshot이 잘렸을 수 있는 경우(snapshot_complete=False)에는 이 추론 자체를 하지 않는다 —
    # "못 받아온 것"과 "광고주가 껐다"를 혼동하면 안 된다.
    if snapshot_complete:
        for ad_archive_id, existing in existing_by_archive_id.items():
            if existing.is_archived or ad_archive_id in fetched_by_archive_id:
                continue
            previous_status = existing.status
            existing.status = AdStatus.INACTIVE.value
            existing.consecutive_inactive_days += 1
            # P0-05: newly_inactive/STOPPED는 상태가 "이번에" 전환된 경우에만 센다.
            # 이미 INACTIVE였던 광고가 계속 없는 것은 새로운 사건이 아니다.
            if previous_status != AdStatus.INACTIVE.value:
                newly_inactive_count += 1
                collection_history.record_event(
                    db,
                    ad_id=existing.id,
                    competitor_id=competitor_id,
                    collection_run_id=collection_run.id,
                    event_type=AdChangeEventType.STOPPED.value,
                    event_date=event_date,
                    previous_status=previous_status,
                    new_status=AdStatus.INACTIVE.value,
                )
            if existing.consecutive_inactive_days >= settings.archive_after_inactive_days:
                existing.is_archived = True
                newly_archived_count += 1

    if snapshot_complete:
        collection_history.complete_collection_run_success(db, collection_run, fetched_ads_count=len(fetched_ads))
    else:
        collection_history.complete_collection_run_partial(db, collection_run, fetched_ads_count=len(fetched_ads))

    db.commit()

    return SyncResult(
        competitor_id=competitor_id,
        new_ads=new_count,
        reactivated_or_kept_active=kept_active_count,
        newly_inactive=newly_inactive_count,
        newly_archived=newly_archived_count,
        is_baseline=is_baseline,
        snapshot_complete=snapshot_complete,
    )

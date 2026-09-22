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
  - P0-07/P0-08 Baseline은 "첫 수집"이 아니라 "첫 COMPLETE SUCCESSFUL SNAPSHOT"이다.
    competitor.baseline_completed_at이 NULL인 동안은(=baseline pending) 어떤 이벤트도
    생성하지 않는다 — 발견된 소재는 저장하되(status=ACTIVE), STARTED/STOPPED/REACTIVATED는 물론
    BASELINE_DISCOVERED조차 "이 수집이 완전한 성공(snapshot_complete=True)"일 때만 기록한다.
    그 완전한 성공 run이 곧 baseline이 되며, 그 순간 baseline_completed_at을 확정 저장한다.
    그 다음 successful complete collection부터 정상적으로 STARTED/STOPPED/REACTIVATED를 생성한다.
  - P0-09 Baseline에서 발견된 소재는 "오늘 새로 시작한 광고(NEW)"가 아니라 "ADCatcher가 처음
    확인한 현재 집행 소재"이므로 status=ACTIVE로 생성한다(NEW 배지가 붙지 않도록).
  - P0-07 Gemini/썸네일 캐싱(enrichment) 실패가 수집(core data) 자체를 무효화해서는 안 된다.

성능(운영 중 실측 — 대량 소재 브랜드 첫 수집이 "무한 수집중"처럼 보이던 문제):
  - 신규 소재의 enrichment(이미지 다운로드 + Storage 캐싱 + Gemini 태깅)는 소재마다 네트워크 I/O가
    여러 번 발생한다. 이걸 소재 개수만큼 순차로 돌리면 소재가 많은 브랜드(예: 첫 baseline 수집)는
    한 번의 /collect 요청이 수 분~수십 분씩 걸려 사실상 멈춘 것처럼 보인다. 그래서 이 함수는
    DB에 쓰기 전에 신규 소재들의 enrichment를 ThreadPoolExecutor로 먼저 동시에 실행해둔다
    (SQLAlchemy Session 자체는 스레드 세이프하지 않으므로 DB 쓰기는 항상 메인 스레드에서 순차로 한다).
"""

import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Ad, Competitor, CollectionRun
from app.schemas import AdChangeEventType, AdFormat, AdStatus, CampaignTagOut, RawAdItem, SyncResult, VisualType
from app.services import campaign_tagging, collection_history, media
from app.services.campaign_tags import list_active_campaign_tags
from app.services.timing import stage_timer
from app.services.vision_tagging import GeminiQuotaExceeded


def _survival_days_at(source_started_at: datetime | None, first_seen_at: datetime, at: datetime) -> int:
    # SQLite(테스트 환경)는 DateTime(timezone=True) 컬럼도 naive datetime으로 되돌려주므로,
    # Postgres(운영)에서는 항상 aware인 값과 섞여도 안전하게 빼기 위해 naive로 정규화한다.
    def _naive(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt

    start = source_started_at or first_seen_at
    return max((_naive(at) - _naive(start)).days, 0)


class _Enrichment:
    __slots__ = (
        "image_url",
        "visual_type",
        "analysis_status",
        "analysis_error",
        # Campaign Tag 자동 분류 (additive, 2026-09) — 비주얼 분석과 완전히 독립된 결과.
        "campaign_tag_id",
        "campaign_tag_confidence",
        "campaign_tag_reason",
        "campaign_tag_assignment_source",
        "campaign_classification_status",
        "campaign_classification_error",
    )

    def __init__(
        self,
        image_url: str | None,
        visual_type: VisualType | None,
        analysis_status: str,
        analysis_error: str | None,
        campaign_tag_id: str | None = None,
        campaign_tag_confidence: float | None = None,
        campaign_tag_reason: str | None = None,
        campaign_tag_assignment_source: str | None = None,
        campaign_classification_status: str = "PENDING",
        campaign_classification_error: str | None = None,
    ):
        self.image_url = image_url
        self.visual_type = visual_type
        self.analysis_status = analysis_status
        self.analysis_error = analysis_error
        self.campaign_tag_id = campaign_tag_id
        self.campaign_tag_confidence = campaign_tag_confidence
        self.campaign_tag_reason = campaign_tag_reason
        self.campaign_tag_assignment_source = campaign_tag_assignment_source
        self.campaign_classification_status = campaign_classification_status
        self.campaign_classification_error = campaign_classification_error


def _classify_campaign_tag_isolated(
    image_url: str | None, copy_text: str | None, cta_text: str | None, active_tags: list[CampaignTagOut]
) -> tuple[str | None, float | None, str | None, str, str | None]:
    """(campaign_tag_id, confidence, reason, classification_status, classification_error)를 반환한다.
    비주얼 분석과 완전히 독립된 별도 try/except로 격리한다 — 하나가 실패해도 다른 하나에 영향 없음
    (P0-07과 동일한 enrichment 격리 원칙을 캠페인 분류에도 그대로 적용)."""
    if not active_tags:
        return None, None, None, "PENDING", None
    try:
        tag_id, confidence, reason = campaign_tagging.classify_campaign_tag(image_url, copy_text, cta_text, active_tags)
    except GeminiQuotaExceeded as e:
        return None, None, None, "PENDING", str(e)[:500]
    except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 격리
        return None, None, None, "PENDING", str(e)[:500]

    if tag_id is None and confidence is None and reason is None:
        # 완전한 실패(이미지 다운로드/Gemini 응답 파싱) — PENDING 유지, 이후 pending 배치가 재시도.
        return None, None, None, "PENDING", "신규 소재 분류 중 이미지 다운로드 또는 Gemini 응답 파싱 실패"
    if tag_id is not None and confidence is not None and confidence >= settings.campaign_tag_confidence_threshold:
        return tag_id, confidence, reason, "SUCCESS", None
    # Gemini는 응답했지만 확신이 낮거나 태그를 확정하지 못함 — 억지 분류 대신 검토 필요로 남긴다.
    return None, confidence, reason, "NEEDS_REVIEW", None


def _enrich_one(competitor_id: uuid.UUID, item: RawAdItem, active_tags: list[CampaignTagOut]) -> _Enrichment:
    # P0-07: enrichment(캐싱+Gemini)는 core data(수집)와 완전히 분리한다 — 어떤 예외가 나든
    # 이 함수는 예외를 밖으로 던지지 않고 FAILED로 기록만 남긴다(광고 row 생성은 항상 계속돼야 함).
    try:
        cached_url, visual_type = media.process_ad_image(competitor_id, item.ad_archive_id, item.image_url)
        analysis_status = "SUCCESS" if visual_type else "PENDING"
        analysis_error = None
    except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 격리
        cached_url, visual_type = item.image_url, None
        analysis_status = "FAILED"
        analysis_error = str(e)[:500]

    campaign_tag_id, campaign_confidence, campaign_reason, campaign_status, campaign_error = (
        _classify_campaign_tag_isolated(cached_url or item.image_url, item.copy_text, item.cta_text, active_tags)
    )
    campaign_source = "AI" if campaign_status in ("SUCCESS", "NEEDS_REVIEW") else None

    return _Enrichment(
        image_url=cached_url,
        visual_type=visual_type,
        analysis_status=analysis_status,
        analysis_error=analysis_error,
        campaign_tag_id=campaign_tag_id,
        campaign_tag_confidence=campaign_confidence,
        campaign_tag_reason=campaign_reason,
        campaign_tag_assignment_source=campaign_source,
        campaign_classification_status=campaign_status,
        campaign_classification_error=campaign_error,
    )


def _enrich_new_ads_concurrently(
    competitor_id: uuid.UUID, new_items: list[RawAdItem], active_tags: list[CampaignTagOut]
) -> dict[str, _Enrichment]:
    """신규 소재 중 image_url이 있는 것들의 enrichment를 동시에 실행해 결과를 모아 돌려준다.
    네트워크 I/O 대기 중 GIL이 풀리는 순수 blocking I/O(httpx)이므로 스레드풀로 충분하다.
    active_tags는 호출 전 메인 스레드에서 1회 조회한 읽기 전용 목록을 그대로 공유한다(DB 세션은
    스레드 안에서 쓰지 않는다는 기존 제약과 동일한 이유)."""
    targets = [item for item in new_items if item.image_url]
    if not targets:
        return {}
    results: dict[str, _Enrichment] = {}
    max_workers = min(settings.media_enrichment_concurrency, len(targets))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(_enrich_one, competitor_id, item, active_tags): item.ad_archive_id for item in targets
        }
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return results


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
    competitor = db.get(Competitor, competitor_id)
    # P0-07/P0-08: baseline_completed_at이 NULL이면 아직 "확정된 첫 완전 스냅샷"이 없는 상태.
    is_baseline_pending = competitor is not None and competitor.baseline_completed_at is None
    # SyncResult.is_baseline: 이번 run이 baseline 확립에 관여했는지(pending 중이었는지) 여부.
    # 프론트는 is_baseline && snapshot_complete 조합으로만 Baseline CTA를 노출하므로,
    # PARTIAL pending run(snapshot_complete=False)에 대해 True를 반환해도 CTA는 뜨지 않는다.
    is_baseline = is_baseline_pending
    # 이번 run이 실제로 baseline을 "확정"하는 run인가 — pending 상태에서 완전한 성공일 때만.
    establishes_baseline = is_baseline_pending and snapshot_complete

    # P0-04: 아카이빙된 광고도 ad_archive_id가 재등장할 수 있으므로, is_archived 필터 없이
    # 전부 불러와 "완전히 새로운 광고"와 "재등장한 기존 row"를 정확히 구분한다.
    existing_ads = db.scalars(select(Ad).where(Ad.competitor_id == competitor_id)).all()
    existing_by_archive_id = {ad.ad_archive_id: ad for ad in existing_ads}
    fetched_by_archive_id = {item.ad_archive_id: item for item in fetched_ads}

    # DB 쓰기 루프를 시작하기 전에, 신규 소재의 enrichment(이미지 다운로드+캐싱+Gemini 태깅)를
    # 먼저 동시에 실행해둔다 — 소재 개수만큼 순차로 돌리면 대량 소재 브랜드의 수집이 체감상
    # "무한 수집중"처럼 보일 만큼 느려진다.
    enrichment_results: dict[str, _Enrichment] = {}
    if tag_visual:
        new_items = [item for aid, item in fetched_by_archive_id.items() if aid not in existing_by_archive_id]
        # 활성 캠페인 태그는 메인 스레드에서 1회만 조회해 스레드풀에 읽기 전용으로 공유한다.
        active_campaign_tags = (
            [CampaignTagOut.model_validate(t) for t in list_active_campaign_tags(db, competitor.project_id)]
            if competitor is not None
            else []
        )
        with stage_timer("enrichment_concurrent_total", competitor_id=competitor_id, new_count=len(new_items)):
            enrichment_results = _enrich_new_ads_concurrently(competitor_id, new_items, active_campaign_tags)

    new_count = 0
    kept_active_count = 0
    newly_inactive_count = 0
    newly_archived_count = 0

    db_sync_start = time.perf_counter()

    # 1) 이번에 발견된 소재 → NEW 생성 또는 기존 소재(아카이빙 포함) ACTIVE 갱신
    for ad_archive_id, item in fetched_by_archive_id.items():
        existing = existing_by_archive_id.get(ad_archive_id)
        if existing is None:
            enrichment = enrichment_results.get(ad_archive_id)
            if enrichment is not None:
                image_url = enrichment.image_url
                visual_type = enrichment.visual_type
                analysis_status = enrichment.analysis_status
                analysis_error = enrichment.analysis_error
                analyzed_at = now
                campaign_tag_id = enrichment.campaign_tag_id
                campaign_tag_confidence = enrichment.campaign_tag_confidence
                campaign_tag_reason = enrichment.campaign_tag_reason
                campaign_tag_assignment_source = enrichment.campaign_tag_assignment_source
                campaign_classification_status = enrichment.campaign_classification_status
                campaign_classification_error = enrichment.campaign_classification_error
                campaign_tag_classified_at = now if campaign_tag_assignment_source else None
            else:
                # tag_visual=False였거나 image_url이 애초에 없던 경우 — enrichment 자체를 하지 않는다.
                image_url = item.image_url
                visual_type = None
                analysis_status = "PENDING"
                analysis_error = None
                analyzed_at = None
                campaign_tag_id = None
                campaign_tag_confidence = None
                campaign_tag_reason = None
                campaign_tag_assignment_source = None
                campaign_classification_status = "PENDING"
                campaign_classification_error = None
                campaign_tag_classified_at = None

            new_ad_id = uuid.uuid4()
            # P0-09: baseline(pending) 중에 발견된 소재는 "오늘 켠 광고"가 아니라 "처음 확인한
            # 현재 집행 소재"이므로 NEW가 아니라 ACTIVE로 생성한다(Gallery NEW 배지 방지).
            initial_status = AdStatus.ACTIVE.value if is_baseline_pending else AdStatus.NEW.value
            # VIDEO/CAROUSEL 미디어 — keyframe 추출은 여기서 절대 하지 않는다(§8, 별도 pending
            # 배치가 처리). VIDEO이고 video_url이 있으면 PENDING으로만 표시해둔다.
            keyframe_status = (
                "PENDING" if item.format.value == "VIDEO" and item.video_url else "NOT_APPLICABLE"
            )
            db.add(
                Ad(
                    id=new_ad_id,
                    competitor_id=competitor_id,
                    ad_archive_id=ad_archive_id,
                    status=initial_status,
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
                    campaign_tag_id=uuid.UUID(campaign_tag_id) if campaign_tag_id else None,
                    campaign_tag_confidence=campaign_tag_confidence,
                    campaign_tag_reason=campaign_tag_reason,
                    campaign_tag_assignment_source=campaign_tag_assignment_source,
                    campaign_tag_classified_at=campaign_tag_classified_at,
                    campaign_classification_status=campaign_classification_status,
                    campaign_classification_error=campaign_classification_error,
                    video_url=item.video_url,
                    media_items=[m.model_dump() for m in item.media_items] if item.media_items else None,
                    keyframe_status=keyframe_status,
                )
            )
            new_count += 1
            # P0-07/P0-08: baseline이 아직 pending인데 이번 run이 완전한 성공이 아니면(=PARTIAL),
            # 어떤 이벤트도 남기지 않는다 — "확정된 baseline"이 아닌 중간 관측치이기 때문이다.
            if not is_baseline_pending or establishes_baseline:
                collection_history.record_event(
                    db,
                    ad_id=new_ad_id,
                    competitor_id=competitor_id,
                    collection_run_id=collection_run.id,
                    event_type=(
                        AdChangeEventType.BASELINE_DISCOVERED.value
                        if is_baseline_pending
                        else AdChangeEventType.STARTED.value
                    ),
                    event_date=event_date,
                    previous_status=None,
                    new_status=initial_status,
                    survival_days_at_event=_survival_days_at(item.start_date, now, now),
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

            # format 교정(2026-09) — 과거에 잘못 판정된 format을 최신 raw 판정으로 바로잡는다.
            # raw evidence(video_url 또는 media_items)가 명확할 때만 교정하고, 애매하거나 비어
            # 있으면 기존 format을 절대 덮어쓰지 않는다(예: 일시적으로 빈 snapshot이 온 경우).
            has_clear_media_evidence = bool(item.video_url) or bool(item.media_items)
            if has_clear_media_evidence and item.format.value != existing.format:
                was_video = existing.format == AdFormat.VIDEO.value
                existing.format = item.format.value
                if item.video_url:
                    existing.video_url = item.video_url
                if item.media_items:
                    existing.media_items = [m.model_dump() for m in item.media_items]
                if item.format == AdFormat.VIDEO and existing.video_url and not existing.keyframe_urls:
                    # 새로 VIDEO로 교정됐고 아직 성공적으로 캐싱된 keyframe이 없으면 pending 배치
                    # 대상에 새로 넣는다(이미 SUCCESS인 keyframe은 불필요하게 초기화하지 않는다).
                    existing.keyframe_status = "PENDING"
                    existing.keyframe_retry_count = 0
                    existing.keyframe_error = None
                elif was_video and item.format != AdFormat.VIDEO:
                    # VIDEO → CAROUSEL/IMAGE로 교정된 경우 더 이상 keyframe 대상이 아니다. 이미
                    # Storage에 업로드된 keyframe 파일은 destructive cleanup 대상이 아니므로
                    # keyframe_urls 배열 자체는 건드리지 않고 상태만 NOT_APPLICABLE로 되돌린다.
                    existing.keyframe_status = "NOT_APPLICABLE"

            # VIDEO/CAROUSEL 미디어 backfill — 이 컬럼들이 생기기 전에 수집된 기존 소재가 재발견될
            # 때마다(format이 그대로인 경우) 빈 필드만 채운다(이미 캐싱된 값은 절대 덮어쓰지 않는다).
            # 별도 백필 스크립트 없이 다음 수집 사이클에서 자연스럽게 채워지게 한다.
            if existing.video_url is None and item.video_url:
                existing.video_url = item.video_url
            if not existing.media_items and item.media_items:
                existing.media_items = [m.model_dump() for m in item.media_items]
            if existing.format == AdFormat.VIDEO.value and existing.video_url and existing.keyframe_status == "NOT_APPLICABLE":
                existing.keyframe_status = "PENDING"
            # INACTIVE(아카이빙된 광고 포함, is_archived=True는 항상 status=INACTIVE를 동반함)였던
            # 광고가 다시 발견된 경우에만 REACTIVATED. 계속 노출 중이던 광고는 새 이벤트 없음.
            # P0-07/P0-08: baseline이 아직 pending인 동안은 이벤트를 만들지 않는다(위 새 소재 분기와 동일 원칙).
            if previous_status == AdStatus.INACTIVE.value and not is_baseline_pending:
                collection_history.record_event(
                    db,
                    ad_id=existing.id,
                    competitor_id=competitor_id,
                    collection_run_id=collection_run.id,
                    event_type=AdChangeEventType.REACTIVATED.value,
                    event_date=event_date,
                    previous_status=previous_status,
                    new_status=AdStatus.ACTIVE.value,
                    survival_days_at_event=_survival_days_at(existing.source_started_at, existing.first_seen_at, now),
                )
            collection_history.record_observation(
                db, collection_run_id=collection_run.id, competitor_id=competitor_id, ad_id=existing.id
            )

    # 2) 기존에 추적 중이었으나 이번엔 미발견 → INACTIVE, 14일 연속 미노출 시 아카이빙.
    # P0-02: snapshot이 잘렸을 수 있는 경우(snapshot_complete=False)에는 이 추론 자체를 하지 않는다 —
    # "못 받아온 것"과 "광고주가 껐다"를 혼동하면 안 된다.
    # P0-07/P0-08: baseline이 이번 run에서 막 확정되는 순간(establishes_baseline)에도 비교 기준이 될
    # "직전의 확정된 상태"가 아직 없으므로 STOPPED 추론을 하지 않는다 — STOPPED는 baseline이 이미
    # 확정된 이후의 수집부터 시작된다.
    if snapshot_complete and not is_baseline_pending:
        for ad_archive_id, existing in existing_by_archive_id.items():
            if existing.is_archived or ad_archive_id in fetched_by_archive_id:
                continue
            previous_status = existing.status
            # STOPPED 시점에 고정할 생존일수 — 이후 existing.last_seen_at이 REACTIVATED 등으로
            # 앞으로 밀려도 이 이벤트의 값은 바뀌지 않는다(P1-01). status 전환 전에 계산한다.
            survival_snapshot = _survival_days_at(existing.source_started_at, existing.first_seen_at, existing.last_seen_at)
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
                    survival_days_at_event=survival_snapshot,
                )
            if existing.consecutive_inactive_days >= settings.archive_after_inactive_days:
                existing.is_archived = True
                newly_archived_count += 1

    logging.getLogger("adcatcher.collection_timing").info(
        "stage=db_core_sync ms=%.0f competitor_id=%s new_count=%d",
        (time.perf_counter() - db_sync_start) * 1000,
        competitor_id,
        new_count,
    )

    if establishes_baseline:
        competitor.baseline_completed_at = now

    if snapshot_complete:
        collection_history.complete_collection_run_success(db, collection_run, fetched_ads_count=len(fetched_ads))
    else:
        collection_history.complete_collection_run_partial(db, collection_run, fetched_ads_count=len(fetched_ads))

    with stage_timer("db_final_commit", competitor_id=competitor_id):
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

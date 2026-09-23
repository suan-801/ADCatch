import uuid
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import false, func, or_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user, require_admin
from app.models import Ad, CampaignTag, Competitor, Project, User
from app.schemas import AdCampaignTagUpdate, AdHistoryResponse, AdOut, AdWithCompetitorOut, SyncResult
from app.services import collection_history
from app.services.ad_library_collector import ApifyRunError, fetch_live_ads
from app.services.ad_sync import synchronize_ad_status

router = APIRouter(prefix="/competitors/{competitor_id}/ads", tags=["ads"])
# Part C-03: 개별 광고 조회는 competitor_id 없이 ad_id만으로 이뤄지므로 별도 prefix를 쓴다.
# 기존 /competitors/{competitor_id}/ads 계약은 변경하지 않는다.
ad_detail_router = APIRouter(prefix="/ads", tags=["ads"])
# §13-1 성능 최적화: 프로젝트 전체 Ad를 1회 호출로 반환한다(브랜드별 listAds() N회 호출 대체용).
# 기존 GET /competitors/{competitor_id}/ads는 그대로 유지 — 이 라우터는 순수 추가다.
project_ads_router = APIRouter(prefix="/projects/{project_id}/ads", tags=["ads"])


def _get_owned_competitor(db: Session, competitor_id: uuid.UUID, user: User) -> Competitor:
    competitor = db.get(Competitor, competitor_id)
    if competitor is None or competitor.project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Competitor not found")
    return competitor


@router.get("", response_model=list[AdOut])
def list_ads(
    competitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """생존기간(첫 발견~마지막 발견) 긴 순으로 라이브 소재 갤러리를 반환한다 (PRD 시나리오 2)."""
    _get_owned_competitor(db, competitor_id, user)
    ads = db.scalars(
        select(Ad)
        .where(Ad.competitor_id == competitor_id, Ad.is_archived.is_(False))
        .order_by(Ad.first_seen_at.asc())
    ).all()
    return ads


@router.post("/collect", response_model=SyncResult)
def collect_now(
    competitor_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """해당 경쟁사에 대해 즉시 1회 수집 + 상태 동기화를 실행한다 (스케줄러 없이 수동 트리거용).

    Daily Ad Change History: collection_run을 fetch 전에 미리 생성해두고, 실패 시에는
    FAILED로 기록만 남긴 뒤 기존과 동일하게 502를 반환한다 (응답 계약 변경 없음) —
    "수집 실패"가 "광고가 전부 꺼짐"으로 오판되지 않게 하는 핵심 장치."""
    competitor = _get_owned_competitor(db, competitor_id, user)
    run = collection_history.start_collection_run(db, competitor_id)
    try:
        fetched = fetch_live_ads(
            competitor.ad_library_url,
            page_id=competitor.page_id or "",
            max_ads=settings.apify_max_ads,
        )
    except httpx.HTTPStatusError as e:
        collection_history.fail_collection_run(db, run, str(e))
        raise HTTPException(
            status_code=502,
            detail=f"Apify 요청 실패 ({e.response.status_code}): APIFY_TOKEN이 올바른지 확인하세요. {e.response.text[:200]}",
        ) from e
    except (ApifyRunError, httpx.HTTPError) as e:
        collection_history.fail_collection_run(db, run, str(e))
        raise HTTPException(status_code=502, detail=f"수집 실패: {e}") from e

    # P0-02: 상한에 도달했다면(=더 있을 수 있음) 이 스냅샷은 불완전한 것으로 간주한다.
    snapshot_complete = len(fetched) < settings.apify_max_ads
    return synchronize_ad_status(db, competitor_id, fetched, run, snapshot_complete=snapshot_complete)


@ad_detail_router.get("/{ad_id}/history", response_model=AdHistoryResponse)
def get_ad_history(
    ad_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Part C-03 — Ad Detail Drawer의 event history. 기존 Daily Changes API는 변경하지 않는다."""
    ad = db.get(Ad, ad_id)
    if ad is None or ad.competitor.project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ad not found")
    return AdHistoryResponse(ad_id=ad_id, events=collection_history.get_ad_history(db, ad_id))


@ad_detail_router.patch("/{ad_id}/campaign-tag", response_model=AdOut)
def update_ad_campaign_tag(
    ad_id: uuid.UUID,
    payload: AdCampaignTagUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    _admin: bool = Depends(require_admin),
):
    """사용자가 직접 캠페인 태그를 지정/수정한다 — AI 값보다 항상 우선한다.

    FK만으로는 "다른 프로젝트의 태그를 지정"하는 것을 막지 못하므로, ad가 속한 프로젝트와 태그가
    속한 프로젝트가 같은지 서버에서 반드시 재검증한다. 비활성화된 태그도 지정할 수 없다."""
    ad = db.get(Ad, ad_id)
    if ad is None or ad.competitor.project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Ad not found")

    tag = db.get(CampaignTag, payload.campaign_tag_id)
    if tag is None or not tag.is_active or tag.project_id != ad.competitor.project_id:
        raise HTTPException(status_code=400, detail="Invalid or inactive campaign tag for this project")

    ad.campaign_tag_id = tag.id
    ad.campaign_tag_assignment_source = "USER"
    ad.campaign_classification_status = "SUCCESS"
    # 사용자가 직접 지정하면 이전 AI confidence/reason은 의미가 없어지므로 항상 비운다 —
    # "사용자 지정 / AI 신뢰도 87%" 같은 모순된 화면을 방지한다.
    ad.campaign_tag_confidence = None
    ad.campaign_tag_reason = None
    ad.campaign_tag_classified_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(ad)
    return ad


@project_ads_router.get("", response_model=list[AdWithCompetitorOut])
def list_project_ads(
    project_id: uuid.UUID,
    competitor_id: uuid.UUID | None = Query(None),
    status: str | None = Query(None, description="NEW | ACTIVE | INACTIVE"),
    format: str | None = Query(None, description="IMAGE | VIDEO"),
    visual_type: str | None = Query(None, description="PERSON | PRODUCT | TEXT_HEAVY | GRAPHIC | UNANALYZED"),
    campaign_tag_id: str | None = Query(
        None, description="태그 UUID, 또는 미분류(태그 없음) 필터용 특수값 NEEDS_REVIEW"
    ),
    search: str | None = Query(None, description="copy_text/cta_text 부분 일치(대소문자 무시)"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """§13-1 성능 최적화 — 대시보드가 브랜드마다 listAds()를 N회 호출하던 것을 1회로 통합한다.
    값의 의미는 기존 조합(경쟁사별 조회 후 클라이언트에서 합치기)과 동일하다.

    §13(2026-09) — 모든 필터 파라미터는 additive/optional이다. 하나도 넘기지 않으면 기존과 동일하게
    프로젝트 전체(비아카이브)를 반환한다(하위 호환) — 프론트가 전체를 받아 클라이언트에서 필터링하던
    경로를 주요 경로로 쓰지 않고, WHERE 조건으로 서버에서 필터링한다."""
    project = db.get(Project, project_id)
    if project is None or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    conditions = [Competitor.project_id == project_id, Ad.is_archived.is_(False)]
    if competitor_id is not None:
        conditions.append(Ad.competitor_id == competitor_id)
    if status is not None:
        conditions.append(Ad.status == status)
    if format is not None:
        conditions.append(Ad.format == format)
    if visual_type is not None:
        if visual_type == "UNANALYZED":
            conditions.append(Ad.visual_type.is_(None))
        else:
            conditions.append(Ad.visual_type == visual_type)
    if campaign_tag_id is not None:
        if campaign_tag_id == "NEEDS_REVIEW":
            conditions.append(Ad.campaign_tag_id.is_(None))
        else:
            # campaign_tag_id 컬럼은 Uuid(as_uuid=True) 타입이라 plain str을 그대로 바인딩하면
            # SQLAlchemy의 UUID 프로세서가 실패한다("'str' object has no attribute 'hex'") — 명시적으로
            # uuid.UUID로 변환한다. 잘못된 형식이면 조용히 빈 결과로 처리한다(존재할 수 없는 값이므로).
            try:
                conditions.append(Ad.campaign_tag_id == uuid.UUID(campaign_tag_id))
            except ValueError:
                conditions.append(false())
    if search:
        like = f"%{search.lower()}%"
        conditions.append(or_(func.lower(Ad.copy_text).like(like), func.lower(Ad.cta_text).like(like)))

    rows = db.execute(
        select(Ad, Competitor.name)
        .join(Competitor, Ad.competitor_id == Competitor.id)
        .where(*conditions)
        .order_by(Ad.first_seen_at.asc())
    ).all()

    result: list[AdWithCompetitorOut] = []
    for ad, competitor_name in rows:
        data = AdOut.model_validate(ad).model_dump()
        data["competitor_name"] = competitor_name
        result.append(AdWithCompetitorOut(**data))
    return result

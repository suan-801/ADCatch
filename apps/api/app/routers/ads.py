import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models import Ad, Competitor, User
from app.schemas import AdHistoryResponse, AdOut, SyncResult
from app.services import collection_history
from app.services.ad_library_collector import ApifyRunError, fetch_live_ads
from app.services.ad_sync import synchronize_ad_status

router = APIRouter(prefix="/competitors/{competitor_id}/ads", tags=["ads"])
# Part C-03: 개별 광고 조회는 competitor_id 없이 ad_id만으로 이뤄지므로 별도 prefix를 쓴다.
# 기존 /competitors/{competitor_id}/ads 계약은 변경하지 않는다.
ad_detail_router = APIRouter(prefix="/ads", tags=["ads"])


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

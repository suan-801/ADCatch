"""Brand Model Simplification (P0-18~22) — "자사 vs 경쟁사" 구분 제거 검증.

is_own_brand=True로 등록된 과거 row도 새 business logic에서는 다른 브랜드와 완전히 동일하게
집계되어야 한다(컬럼 자체는 하위호환을 위해 남아있지만, dashboard/daily-changes/freshness
어디에서도 필터링에 사용되지 않는다)."""

from app.models import Competitor, Project, User
from app.routers.dashboard import get_dashboard
from app.schemas import AdFormat, AdStatus, CompetitorCreate, RawAdItem
from app.services import collection_history
from app.services.ad_sync import synchronize_ad_status


def _raw(archive_id: str) -> RawAdItem:
    return RawAdItem(ad_archive_id=archive_id, page_id="1", page_name="p", format=AdFormat.IMAGE)


def _own_brand_competitor(db, project_id: str) -> Competitor:
    own_brand = Competitor(
        project_id=project_id,
        name="자사(레거시 플래그)",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=9",
        page_id="9",
        is_own_brand=True,
    )
    db.add(own_brand)
    db.commit()
    db.refresh(own_brand)
    return own_brand


# TEST 17 — 과거 is_own_brand=true row도 Dashboard metrics에 포함된다
def test_own_brand_row_included_in_dashboard_metrics(db, competitor):
    own_brand = _own_brand_competitor(db, competitor.project_id)
    run = collection_history.start_collection_run(db, own_brand.id)
    synchronize_ad_status(db, own_brand.id, [_raw("OWN-1")], run, tag_visual=False)

    project = db.get(Project, competitor.project_id)
    owner = db.get(User, project.user_id)
    metrics = get_dashboard(competitor.project_id, db=db, user=owner)

    # baseline이라 ACTIVE로 생성됨(P0-09) — 어쨌든 dashboard 총합에는 포함되어야 한다.
    assert metrics.active_count + metrics.new_count == 1


# TEST 18 — 과거 is_own_brand=true row도 Daily Changes(프로젝트 전체 조회)에 포함된다
def test_own_brand_row_included_in_daily_changes(db, competitor):
    own_brand = _own_brand_competitor(db, competitor.project_id)

    synchronize_ad_status(
        db, own_brand.id, [_raw("OWN-1")], collection_history.start_collection_run(db, own_brand.id), tag_visual=False
    )  # baseline
    run2 = collection_history.start_collection_run(db, own_brand.id)
    synchronize_ad_status(db, own_brand.id, [_raw("OWN-1"), _raw("OWN-2")], run2, tag_visual=False)  # OWN-2: STARTED

    result = collection_history.get_ad_changes(db, competitor.project_id, run2.run_date, None)
    assert result.summary.started == 1


# TEST 19 — 과거 is_own_brand=true row도 Collection Freshness에 포함된다
def test_own_brand_row_included_in_freshness(db, competitor):
    own_brand = _own_brand_competitor(db, competitor.project_id)
    run = collection_history.start_collection_run(db, own_brand.id)
    synchronize_ad_status(db, own_brand.id, [_raw("OWN-1")], run, tag_visual=False)

    freshness = collection_history.get_freshness_summary(db, competitor.project_id)
    # own_brand competitor는 fixture의 competitor와 별개로 등록됐으므로 total에 둘 다 잡혀야 한다.
    assert freshness.total_competitors == 2
    assert freshness.success_competitors + freshness.partial_competitors >= 1


# TEST 20 — 신규 Brand 등록 API에서 is_own_brand 선택 없이도 생성 가능하다(default False, 무시됨)
def test_competitor_create_does_not_require_is_own_brand():
    payload = CompetitorCreate(name="새 브랜드", ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=3")
    assert payload.is_own_brand is False

"""§13 — GET /projects/{project_id}/ads의 additive query param 필터. 파라미터가 없으면 기존과
동일하게 전체(비아카이브) 결과를 반환해야 한다(하위 호환)."""

import uuid

from app.models import Ad, User
from app.routers.ads import list_project_ads
from app.services.campaign_tags import create_campaign_tag


def _make_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(competitor_id=competitor.id, ad_archive_id=archive_id, **kwargs)
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


def test_no_filters_returns_same_as_before(db, competitor):
    _make_ad(db, competitor, "A1", status="NEW", format="IMAGE")
    _make_ad(db, competitor, "A2", status="ACTIVE", format="VIDEO", is_archived=True)  # 아카이빙 제외
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, None, None, None, None, None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in result} == {"A1"}


def test_status_filter(db, competitor):
    _make_ad(db, competitor, "A1", status="NEW")
    _make_ad(db, competitor, "A2", status="ACTIVE")
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, None, "ACTIVE", None, None, None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in result} == {"A2"}


def test_format_filter(db, competitor):
    _make_ad(db, competitor, "A1", format="IMAGE")
    _make_ad(db, competitor, "A2", format="VIDEO")
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, None, None, "VIDEO", None, None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in result} == {"A2"}


def test_visual_type_filter_including_unanalyzed(db, competitor):
    _make_ad(db, competitor, "A1", visual_type="PERSON")
    _make_ad(db, competitor, "A2", visual_type=None)
    user = db.get(User, competitor.project.user_id)

    person_only = list_project_ads(
        competitor.project_id, None, None, None, "PERSON", None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in person_only} == {"A1"}

    unanalyzed_only = list_project_ads(
        competitor.project_id, None, None, None, "UNANALYZED", None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in unanalyzed_only} == {"A2"}


def test_campaign_tag_filter_including_needs_review(db, competitor):
    tag = create_campaign_tag(db, competitor.project_id, "굿즈", "정의")
    _make_ad(db, competitor, "A1", campaign_tag_id=tag.id, campaign_classification_status="SUCCESS")
    _make_ad(db, competitor, "A2", campaign_tag_id=None)
    user = db.get(User, competitor.project.user_id)

    by_tag = list_project_ads(
        competitor.project_id, None, None, None, None, str(tag.id), None, db=db, user=user
    )
    assert {r.ad_archive_id for r in by_tag} == {"A1"}

    needs_review = list_project_ads(
        competitor.project_id, None, None, None, None, "NEEDS_REVIEW", None, db=db, user=user
    )
    assert {r.ad_archive_id for r in needs_review} == {"A2"}


def test_search_filter_matches_copy_or_cta_case_insensitive(db, competitor):
    _make_ad(db, competitor, "A1", copy_text="정기후원 신청하기")
    _make_ad(db, competitor, "A2", copy_text="굿즈 구매하기", cta_text="Shop Now")
    _make_ad(db, competitor, "A3", copy_text="관련 없음")
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, None, None, None, None, None, "shop", db=db, user=user
    )
    assert {r.ad_archive_id for r in result} == {"A2"}


def test_campaign_tag_filter_invalid_uuid_returns_empty_not_error(db, competitor):
    _make_ad(db, competitor, "A1")
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, None, None, None, None, "not-a-uuid", None, db=db, user=user
    )
    assert result == []


def test_competitor_filter_combined_with_other_filters(db, competitor):
    from app.models import Competitor

    other = Competitor(
        project_id=competitor.project_id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=7", page_id="7",
    )
    db.add(other)
    db.commit()
    db.refresh(other)

    _make_ad(db, competitor, "A1", status="ACTIVE")
    _make_ad(db, other, "B1", status="ACTIVE")
    user = db.get(User, competitor.project.user_id)

    result = list_project_ads(
        competitor.project_id, competitor.id, "ACTIVE", None, None, None, None, db=db, user=user
    )
    assert {r.ad_archive_id for r in result} == {"A1"}


def test_rejects_project_not_owned_by_user(db, competitor):
    import pytest
    from fastapi import HTTPException

    intruder = User(id=uuid.uuid4(), email="intruder@adcather.local")
    db.add(intruder)
    db.commit()

    with pytest.raises(HTTPException) as exc_info:
        list_project_ads(competitor.project_id, None, None, None, None, None, None, db=db, user=intruder)
    assert exc_info.value.status_code == 404

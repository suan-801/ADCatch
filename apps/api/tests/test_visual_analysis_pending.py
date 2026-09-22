"""§9/§10 — 대시보드 "분석 업데이트" 버튼(POST /projects/{id}/visual-analysis/process-pending).
기존 process_pending_analysis()에 project_id 스코프를 추가한 것 — campaign-tags의
process-pending과 동일한 UX/격리 원칙(bounded batch, project 격리, quota graceful stop)."""

import uuid
from unittest.mock import patch

from app.models import Ad, Project, User
from app.routers.visual_analysis import process_pending_visual_analysis
from app.schemas import VisualAnalysisProcessPendingRequest, VisualType
from app.services import vision_tagging


def _make_ad(db, competitor, archive_id: str, **kwargs) -> Ad:
    ad = Ad(
        competitor_id=competitor.id,
        ad_archive_id=archive_id,
        image_url=f"https://cdn.example.com/{archive_id}.jpg",
        format="IMAGE",
        analysis_status=kwargs.pop("analysis_status", "PENDING"),
        **kwargs,
    )
    db.add(ad)
    db.commit()
    db.refresh(ad)
    return ad


class _FakeResponse:
    content = b"fake-bytes"
    headers = {"content-type": "image/jpeg"}

    def raise_for_status(self):
        pass


def test_process_pending_respects_batch_limit(db, competitor):
    for i in range(5):
        _make_ad(db, competitor, f"P{i}")
    user = db.get(User, competitor.project.user_id)

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=VisualType.PERSON
    ):
        result = process_pending_visual_analysis(
            competitor.project_id, VisualAnalysisProcessPendingRequest(limit=2), db=db, user=user
        )

    assert result.processed == 2
    assert result.succeeded == 2
    assert result.pending_remaining == 3


def test_process_pending_caps_limit_at_configured_max(db, competitor, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "visual_analysis_manual_batch_size", 3)
    for i in range(10):
        _make_ad(db, competitor, f"P{i}")
    user = db.get(User, competitor.project.user_id)

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type", return_value=VisualType.PERSON
    ):
        result = process_pending_visual_analysis(
            competitor.project_id, VisualAnalysisProcessPendingRequest(limit=100), db=db, user=user
        )

    assert result.processed == 3


def test_process_pending_quota_stop_is_graceful(db, competitor):
    ad = _make_ad(db, competitor, "P1")
    user = db.get(User, competitor.project.user_id)

    with patch("app.services.pending_analysis.httpx.get", return_value=_FakeResponse()), patch(
        "app.services.pending_analysis.vision_tagging.analyze_visual_type",
        side_effect=vision_tagging.GeminiQuotaExceeded("429"),
    ):
        result = process_pending_visual_analysis(
            competitor.project_id, VisualAnalysisProcessPendingRequest(limit=10), db=db, user=user
        )

    assert result.quota_stopped is True
    assert result.processed == 0
    db.refresh(ad)
    assert ad.analysis_status == "PENDING"
    assert ad.analysis_retry_count == 0


def test_process_pending_does_not_touch_other_project(db, competitor):
    from app.models import Competitor

    other_project = Project(id=uuid.uuid4(), user_id=competitor.project.user_id, name="다른 프로젝트")
    db.add(other_project)
    db.flush()
    other_competitor = Competitor(
        id=uuid.uuid4(), project_id=other_project.id, name="다른 브랜드",
        ad_library_url="https://www.facebook.com/ads/library/?view_all_page_id=5", page_id="5",
    )
    db.add(other_competitor)
    db.commit()

    other_ad = _make_ad(db, other_competitor, "O1")
    user = db.get(User, competitor.project.user_id)

    with patch("app.services.pending_analysis.httpx.get") as mocked_get:
        result = process_pending_visual_analysis(
            competitor.project_id, VisualAnalysisProcessPendingRequest(limit=10), db=db, user=user
        )

    mocked_get.assert_not_called()  # 대상 프로젝트에 PENDING 소재가 없으므로 호출 자체가 없어야 함
    assert result.processed == 0
    db.refresh(other_ad)
    assert other_ad.analysis_status == "PENDING"  # 다른 프로젝트 소재는 그대로

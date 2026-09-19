"""P0 TESTS — API Contract (항목 1~7).

FastAPI response_model serialization은 Pydantic model_dump()/model_dump_json()과 동일한
필드 집합을 만든다 — 여기서는 실제 HTTP 서버 없이 그 계약(필수 필드가 실제로 존재하는지,
enum 값이 정확히 직렬화되는지)을 직접 검증한다."""

import json
import uuid
from datetime import date, datetime

from app.schemas import (
    AdChangeEventType,
    AdChangesResponse,
    AdChangeSummary,
    ChangedAdOut,
    CollectionFreshness,
    CollectionStatus,
    CollectionStatusSummary,
    SyncResult,
)


# 1/2 — SyncResult JSON에 is_baseline / snapshot_complete가 존재한다
def test_sync_result_json_includes_baseline_fields():
    result = SyncResult(
        competitor_id=uuid.uuid4(),
        new_ads=3,
        reactivated_or_kept_active=0,
        newly_inactive=0,
        newly_archived=0,
        is_baseline=True,
        snapshot_complete=True,
    )
    dumped = json.loads(result.model_dump_json())
    assert dumped["is_baseline"] is True
    assert dumped["snapshot_complete"] is True


# 3 — BASELINE_DISCOVERED enum이 정확히 직렬화된다
def test_baseline_discovered_enum_serialization():
    changed = ChangedAdOut(
        id=uuid.uuid4(),
        competitor_id=uuid.uuid4(),
        ad_archive_id="A",
        status="ACTIVE",
        visual_type=None,
        format="IMAGE",
        image_url=None,
        copy_text=None,
        cta_text=None,
        first_seen_at=datetime.now(),
        last_seen_at=datetime.now(),
        source_started_at=None,
        consecutive_inactive_days=0,
        is_archived=False,
        event_type=AdChangeEventType.BASELINE_DISCOVERED,
        competitor_name="test",
    )
    dumped = json.loads(changed.model_dump_json())
    assert dumped["event_type"] == "BASELINE_DISCOVERED"
    assert "survival_days_at_event" in dumped  # None이어도 키는 존재해야 한다


# 4 — PARTIAL CollectionStatus가 정확히 직렬화된다
def test_partial_collection_status_serialization():
    resp = AdChangesResponse(
        project_id=uuid.uuid4(),
        date=date(2026, 9, 19),
        competitor_id=None,
        collection_status=CollectionStatus.PARTIAL,
        collection_summary=CollectionStatusSummary(success=1, partial=1, failed=0, no_record=0),
        history_available_from=None,
        baseline_discovered_count=0,
        summary=AdChangeSummary(started=0, reactivated=0, stopped=0),
        started_ads=[],
        reactivated_ads=[],
        stopped_ads=[],
        visual_pattern={},
    )
    dumped = json.loads(resp.model_dump_json())
    assert dumped["collection_status"] == "PARTIAL"
    # 5 — baseline_discovered_count가 response에 포함된다
    assert "baseline_discovered_count" in dumped
    assert "collection_summary" in dumped
    assert dumped["collection_summary"]["partial"] == 1


# 6 — source_started_at이 response에 포함된다
def test_source_started_at_in_response():
    changed = ChangedAdOut(
        id=uuid.uuid4(),
        competitor_id=uuid.uuid4(),
        ad_archive_id="A",
        status="ACTIVE",
        visual_type=None,
        format="IMAGE",
        image_url=None,
        copy_text=None,
        cta_text=None,
        first_seen_at=datetime.now(),
        last_seen_at=datetime.now(),
        source_started_at=datetime(2026, 8, 1),
        consecutive_inactive_days=0,
        is_archived=False,
        event_type=AdChangeEventType.STARTED,
        competitor_name="test",
    )
    dumped = json.loads(changed.model_dump_json())
    assert "source_started_at" in dumped
    assert dumped["source_started_at"] is not None


# 7 — CollectionFreshness endpoint schema validation (P0-16 확장 필드 포함)
def test_collection_freshness_schema_fields():
    freshness = CollectionFreshness(
        project_id=uuid.uuid4(),
        latest_run_at=None,
        total_competitors=3,
        healthy_competitors=2,
        success_competitors=1,
        partial_competitors=1,
        partial_competitor_names=["B"],
        failed_competitor_names=["C"],
    )
    dumped = json.loads(freshness.model_dump_json())
    for field in (
        "total_competitors",
        "healthy_competitors",
        "success_competitors",
        "partial_competitors",
        "partial_competitor_names",
        "failed_competitor_names",
    ):
        assert field in dumped

"""일일 수집 스케줄러 진입점.

Celery+Redis 대신 이 스크립트 하나를 GitHub Actions cron 또는 OS cron으로 매일 1회
실행하는 방식을 MVP 기본값으로 채택했다 (PRD 6장 스케줄러: "Celery+Redis 또는
GitHub Actions/Cloud Scheduler" 중 후자를 단순화 목적으로 선택).

실행 순서:
  1) apply_auto_pause() — 14일 미접속 프로젝트를 PAUSED로 전환, 이번 회차 스킵 대상 산출
  2) ACTIVE 프로젝트의 각 경쟁사에 대해 fetch_live_ads → synchronize_ad_status
  3) 프로젝트 단위로 Teams 알림 발송
  4) Part A — Pending Gemini Analysis Retry: 위 Daily Collection이 전부 끝난 뒤, 이전
     수집들에서 PENDING으로 남아있던 소재를 별도 step으로 재시도한다. 이 step은 Core
     Collection과 완전히 분리되어 있어(A-07), 실패해도 위 1~3단계 결과에 영향을 주지 않는다.
  5) Campaign Tag Pending Classification Retry (2026-09): 마찬가지로 완전히 독립된 step.

사용법:
  cd apps/api && python -m scripts.run_daily_collection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models import Competitor, Project
from app.services import collection_history, teams_alert
from app.services.ad_library_collector import ApifyRunError, fetch_live_ads
from app.services.ad_sync import synchronize_ad_status
from app.services.autopause import apply_auto_pause
from app.services.pending_analysis import process_pending_analysis
from app.services.pending_campaign_classification import process_pending_campaign_classification


def run() -> None:
    db = SessionLocal()
    try:
        skipped = apply_auto_pause(db)
        if skipped:
            print(f"[auto-pause] 14일 미접속으로 스킵된 프로젝트 {len(skipped)}개: "
                  f"{[p.name for p in skipped]}")

        # Baseline + Daily Catch Opt-in UX §5: status==ACTIVE 만으로는 부족하다 — 사용자가 명시적으로
        # 자동 추적을 켠(auto_collect_enabled=True) 프로젝트만 스케줄러가 건드린다. (auto_pause가
        # 이미 auto_collect_enabled를 반영해 status를 PAUSED로 내리긴 하지만, 두 개념을 혼동하지
        # 않도록 여기서도 명시적으로 다시 확인한다.)
        active_projects = db.scalars(
            select(Project).where(Project.status == "ACTIVE", Project.auto_collect_enabled.is_(True))
        ).all()
        for project in active_projects:
            results = []
            competitors = db.scalars(
                select(Competitor).where(Competitor.project_id == project.id)
            ).all()
            for competitor in competitors:
                run = collection_history.start_collection_run(db, competitor.id)
                try:
                    fetched = fetch_live_ads(
                        competitor.ad_library_url,
                        page_id=competitor.page_id or "",
                        max_ads=settings.apify_max_ads,
                    )
                    snapshot_complete = len(fetched) < settings.apify_max_ads
                    result = synchronize_ad_status(
                        db, competitor.id, fetched, run, snapshot_complete=snapshot_complete
                    )
                    results.append(result)
                    status_label = "SUCCESS" if snapshot_complete else "PARTIAL(상한 도달, STOPPED 판정 보류)"
                    print(f"[{project.name}/{competitor.name}] {status_label} "
                          f"신규={result.new_ads} 유지={result.reactivated_or_kept_active} "
                          f"종료={result.newly_inactive} 아카이빙={result.newly_archived}")
                except (ApifyRunError, httpx.HTTPError) as e:
                    collection_history.fail_collection_run(db, run, str(e))
                    print(f"[{project.name}/{competitor.name}] 수집 실패: {e}")

            if results:
                teams_alert.send_daily_summary(project.name, results)

        # A-07: Gemini는 enrichment다 — 이 step에서 어떤 예외가 나든 위 Daily Collection
        # 결과(이미 commit됨)를 무효화하지 않는다.
        try:
            summary = process_pending_analysis(db)
            print(
                f"[pending-analysis] processed={summary.processed} succeeded={summary.succeeded} "
                f"still_pending={summary.still_pending} failed={summary.failed} "
                f"quota_stopped={summary.quota_stopped}"
            )
        except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 격리 (A-07)
            print(f"[pending-analysis] 재시도 배치 실패(무시하고 계속): {e}")

        # 캠페인 태그 분류도 동일한 원칙(enrichment는 core와 완전히 분리)으로 독립된 step에서
        # 실행한다 — 실패해도 위 단계 결과에 영향을 주지 않는다.
        try:
            campaign_summary = process_pending_campaign_classification(db)
            print(
                f"[pending-campaign-classification] processed={campaign_summary.processed} "
                f"succeeded={campaign_summary.succeeded} needs_review={campaign_summary.needs_review} "
                f"still_pending={campaign_summary.still_pending} failed={campaign_summary.failed} "
                f"quota_stopped={campaign_summary.quota_stopped}"
            )
        except Exception as e:  # noqa: BLE001 - 의도적으로 광범위하게 격리
            print(f"[pending-campaign-classification] 재시도 배치 실패(무시하고 계속): {e}")
    finally:
        db.close()


if __name__ == "__main__":
    run()

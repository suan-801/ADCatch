"""일일 수집 스케줄러 진입점.

Celery+Redis 대신 이 스크립트 하나를 GitHub Actions cron 또는 OS cron으로 매일 1회
실행하는 방식을 MVP 기본값으로 채택했다 (PRD 6장 스케줄러: "Celery+Redis 또는
GitHub Actions/Cloud Scheduler" 중 후자를 단순화 목적으로 선택).

실행 순서:
  1) apply_auto_pause() — 14일 미접속 프로젝트를 PAUSED로 전환, 이번 회차 스킵 대상 산출
  2) ACTIVE 프로젝트의 각 경쟁사에 대해 fetch_live_ads → synchronize_ad_status
  3) 프로젝트 단위로 Teams 알림 발송

사용법:
  cd apps/api && python -m scripts.run_daily_collection
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import Competitor, Project
from app.services import collection_history, teams_alert
from app.services.ad_library_collector import ApifyRunError, fetch_live_ads
from app.services.ad_sync import synchronize_ad_status
from app.services.autopause import apply_auto_pause


def run() -> None:
    db = SessionLocal()
    try:
        skipped = apply_auto_pause(db)
        if skipped:
            print(f"[auto-pause] 14일 미접속으로 스킵된 프로젝트 {len(skipped)}개: "
                  f"{[p.name for p in skipped]}")

        active_projects = db.scalars(select(Project).where(Project.status == "ACTIVE")).all()
        for project in active_projects:
            results = []
            competitors = db.scalars(
                select(Competitor).where(Competitor.project_id == project.id)
            ).all()
            for competitor in competitors:
                run = collection_history.start_collection_run(db, competitor.id)
                try:
                    fetched = fetch_live_ads(competitor.ad_library_url, page_id=competitor.page_id or "")
                    result = synchronize_ad_status(db, competitor.id, fetched, run)
                    results.append(result)
                    print(f"[{project.name}/{competitor.name}] "
                          f"신규={result.new_ads} 유지={result.reactivated_or_kept_active} "
                          f"종료={result.newly_inactive} 아카이빙={result.newly_archived}")
                except ApifyRunError as e:
                    collection_history.fail_collection_run(db, run, str(e))
                    print(f"[{project.name}/{competitor.name}] 수집 실패: {e}")

            if results:
                teams_alert.send_daily_summary(project.name, results)
    finally:
        db.close()


if __name__ == "__main__":
    run()

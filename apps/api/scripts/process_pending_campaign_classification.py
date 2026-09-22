"""Campaign Tag PENDING 재분류 수동 실행 진입점.

Daily Scheduler(scripts/run_daily_collection.py)가 매 회차 마지막에 자동으로 이 배치를
실행하지만, 운영/개발 중 즉시 재시도하고 싶을 때(예: 재분류 API 직후) 수동으로도 실행할 수 있다.

사용법:
  cd apps/api && python -m scripts.process_pending_campaign_classification
  cd apps/api && python -m scripts.process_pending_campaign_classification --limit 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.pending_campaign_classification import process_pending_campaign_classification


def run(limit: int | None) -> None:
    db = SessionLocal()
    try:
        summary = process_pending_campaign_classification(db, limit=limit)
        print(
            f"[pending-campaign-classification] processed={summary.processed} "
            f"succeeded={summary.succeeded} needs_review={summary.needs_review} "
            f"still_pending={summary.still_pending} failed={summary.failed} "
            f"quota_stopped={summary.quota_stopped}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Campaign Tag PENDING 소재 재분류 배치 실행")
    parser.add_argument("--limit", type=int, default=None, help="이번 실행에서 처리할 최대 소재 수")
    args = parser.parse_args()
    run(args.limit)

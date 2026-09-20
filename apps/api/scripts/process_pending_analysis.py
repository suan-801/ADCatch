"""Gemini PENDING 재분석 수동 실행 진입점 (Part A).

Daily Scheduler(scripts/run_daily_collection.py)가 매 회차 마지막에 자동으로 이 배치를
실행하지만, 운영/개발 중 즉시 재시도하고 싶을 때 수동으로도 실행할 수 있다.

사용법:
  cd apps/api && python -m scripts.process_pending_analysis
  cd apps/api && python -m scripts.process_pending_analysis --limit 50
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.pending_analysis import process_pending_analysis


def run(limit: int | None) -> None:
    db = SessionLocal()
    try:
        summary = process_pending_analysis(db, limit=limit)
        print(
            f"[pending-analysis] processed={summary.processed} succeeded={summary.succeeded} "
            f"still_pending={summary.still_pending} failed={summary.failed} "
            f"quota_stopped={summary.quota_stopped}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Gemini PENDING 소재 재분석 배치 실행")
    parser.add_argument("--limit", type=int, default=None, help="이번 실행에서 처리할 최대 소재 수")
    args = parser.parse_args()
    run(args.limit)

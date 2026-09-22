"""VIDEO Keyframe PENDING 캐싱 수동 실행 진입점.

Daily Scheduler(scripts/run_daily_collection.py)가 매 회차 마지막에 자동으로 이 배치를
실행하지만, 운영/개발 중 즉시 재시도하고 싶을 때 수동으로도 실행할 수 있다. 시스템에 ffmpeg/
ffprobe가 없으면 모든 대상이 즉시 FAILED로 처리된다(무한 재시도 방지) — 로컬에서 실행하기 전에
`ffmpeg -version`으로 설치 여부를 먼저 확인하는 것을 권장한다.

사용법:
  cd apps/api && python -m scripts.process_pending_video_keyframes
  cd apps/api && python -m scripts.process_pending_video_keyframes --limit 20
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.pending_video_keyframes import process_pending_video_keyframes


def run(limit: int | None) -> None:
    db = SessionLocal()
    try:
        summary = process_pending_video_keyframes(db, limit=limit)
        print(
            f"[pending-video-keyframes] processed={summary.processed} succeeded={summary.succeeded} "
            f"still_pending={summary.still_pending} failed={summary.failed}"
        )
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VIDEO Keyframe PENDING 소재 캐싱 배치 실행")
    parser.add_argument("--limit", type=int, default=None, help="이번 실행에서 처리할 최대 소재 수")
    args = parser.parse_args()
    run(args.limit)

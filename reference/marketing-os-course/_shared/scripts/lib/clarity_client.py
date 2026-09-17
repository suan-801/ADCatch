"""Microsoft Clarity Data Export API 클라이언트.

한도: 일 10회/프로젝트. 1회 호출 = 모든 메트릭 한꺼번에 받음.
설계: 호출 카운터를 logs/clarity_calls_{YYYY-MM-DD}.json 에 저장하고 보호.

API 특성: 임의 날짜 ❌, numOfDays(1~3)만 가능 → 어제(D-1) 또는 최근 1~3일 단위.
"""
from __future__ import annotations

import json
import os
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import requests

ENDPOINT = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
LOGS_DIR = Path(__file__).resolve().parents[2] / "logs"
DAILY_LIMIT = 10
RESERVED_FOR_CRO = 5  # daily-etl 은 한 번에 하나만 — 일 5회는 cro 용으로 남김


def _call_log_path(today: date | None = None) -> Path:
    d = today or date.today()
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return LOGS_DIR / f"clarity_calls_{d.isoformat()}.json"


def _read_count(today: date | None = None) -> int:
    p = _call_log_path(today)
    if not p.exists():
        return 0
    try:
        return int(json.loads(p.read_text()).get("count", 0))
    except (json.JSONDecodeError, ValueError):
        return 0


def _inc_count(reason: str, today: date | None = None) -> int:
    p = _call_log_path(today)
    current = _read_count(today)
    new_count = current + 1
    p.write_text(json.dumps({
        "count": new_count,
        "last": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
    }, ensure_ascii=False), encoding="utf-8")
    return new_count


def remaining_quota(today: date | None = None) -> int:
    return max(DAILY_LIMIT - _read_count(today), 0)


def call(token: str, num_of_days: int = 1, dimension1: Optional[str] = None,
         reason: str = "manual", today: date | None = None,
         reserve_for_cro: bool = True) -> list[dict]:
    """Clarity API 호출 — 카운터 보호.

    reserve_for_cro=True 면 한도 5회 미만일 때 호출 거부 (CRO 리포트 보호).
    """
    used = _read_count(today)
    if reserve_for_cro and used >= (DAILY_LIMIT - RESERVED_FOR_CRO):
        raise RuntimeError(
            f"Clarity 호출 보호 — 오늘 이미 {used}회 사용. CRO 리포트용 {RESERVED_FOR_CRO}회 예약 유지. "
            f"reserve_for_cro=False 로 강제 호출 가능."
        )
    if used >= DAILY_LIMIT:
        raise RuntimeError(f"Clarity 일 한도 {DAILY_LIMIT} 도달 — 내일 다시.")

    params = {"numOfDays": num_of_days}
    if dimension1:
        params["dimension1"] = dimension1
    resp = requests.get(
        ENDPOINT,
        params=params,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    resp.raise_for_status()
    _inc_count(reason, today)
    return resp.json()


def _to_int(v, default: int = 0) -> int:
    if v is None or v == "":
        return default
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _to_float(v, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _metric(payload: list, name: str) -> dict | None:
    for m in payload:
        if m.get("metricName") == name:
            info = m.get("information") or []
            return info[0] if info else None
    return None


def _sessions_with(payload: list, name: str) -> int:
    info = _metric(payload, name)
    if not info:
        return 0
    total = _to_int(info.get("sessionsCount"))
    pct = _to_float(info.get("sessionsWithMetricPercentage"))
    return int(round(total * pct / 100))


def parse_daily(payload: list, target: date) -> dict:
    """ETL 한 행을 만든다."""
    total_sessions = _to_int((_metric(payload, "Traffic") or {}).get("totalSessionCount"))
    return {
        "date": target.isoformat(),
        "sessions": total_sessions,
        "dead_clicks": _sessions_with(payload, "DeadClickCount"),
        "rage_clicks": _sessions_with(payload, "RageClickCount"),
        "excessive_scroll": _sessions_with(payload, "ExcessiveScroll"),
        "quick_back": _sessions_with(payload, "QuickbackClick"),
        "top_dead_click_url": "",  # 정규 dimension1 호출 별도 (한도 보호 위해 기본 생략)
        "top_rage_click_url": "",
        "freshness": "t3_clarity",
        "updated_at": date.today().isoformat(),
    }

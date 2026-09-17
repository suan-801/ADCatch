#!/usr/bin/env python3
"""Overview 통합 대시보드 1페이지 — Meta·GA4·Clarity 를 한 화면에 모은 친근체 스토리텔링 대시보드.

데이터 소스:
  - outputs/etl/etl_payload_{YYYY-MM-DD}_*.json (디스크 캐시, API 호출 ❌)
  - config/brand_kpi.yml (목표값 + 임계값)
  - data/experiments.jsonl (실험 로그, 수동 편집)
  - outputs/recommendations/{brand}/*.json (피드백 누적, 자동 dump)

사용:
  python3 scripts/render_overview_dashboard.py [--brand sample_brand] [--date YYYY-MM-DD] [--range 7]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from lib.overview_data import build

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
OUT = ROOT.parent / "11_dashboard" / "dashboards"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--date", default=None, help="YYYY-MM-DD (기본: 어제)")
    p.add_argument("--range", type=int, default=30, dest="range_days", help="payload 적재 기간 (일) — 기간 선택기에 30d 포함되도록 기본 30")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    if args.date:
        target = date.fromisoformat(args.date)
    else:
        # 어제 — ETL 은 보통 어제까지의 데이터를 보유
        from datetime import timedelta
        target = date.today() - timedelta(days=1)

    print(f"[overview] brand={args.brand} target={target} range={args.range_days}d")
    data = build(args.brand, target, range_days=args.range_days)
    print(f"  payloads loaded: {data['payloads_loaded']}")
    print(f"  target resolved: {data['target']}")
    print(f"  recommendations: {len(data['recommendations'])}")
    print(f"  experiments: total={data['experiments']['total']}, "
          f"running={len(data['experiments']['running'])}, "
          f"trophies={len(data['experiments']['trophies'])}")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    tpl = env.get_template("overview_dashboard.html.j2")
    daily_data_json = json.dumps(data.get("daily_data") or {}, ensure_ascii=False, default=str)

    # 날짜 입력의 min/max — DAILY_DATA 에 들어간 모든 날짜 (Sheets + ETL JSON 합집합)
    daily_keys = sorted((data.get("daily_data") or {}).keys())
    if daily_keys:
        date_min = daily_keys[0]
        date_max = daily_keys[-1]
    else:
        date_min = date_max = data["target"]

    html = tpl.render(
        daily_data_json=daily_data_json,
        date_min=date_min,
        date_max=date_max,
        **data,
    )

    OUT.mkdir(parents=True, exist_ok=True)
    target_iso = data["target"]
    out_path = OUT / f"overview_{target_iso}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"[overview] wrote: {out_path.relative_to(ROOT.parent)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

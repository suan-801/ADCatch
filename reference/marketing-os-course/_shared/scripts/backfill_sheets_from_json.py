#!/usr/bin/env python3
"""백필된 etl_payload JSON(_shared/outputs/etl)을 읽어 구글시트에 UPSERT.

API 재호출 없이 디스크 JSON → 시트로 적재. 탭별로 전체 행을 모아 1회 upsert.
같은 키가 여러 날 반복되는 탭(meta_creatives: key=ad_id)은 키별 마지막 행만 유지.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.env_loader import load_env
from lib.sheet_client import SCHEMA, open_sheet, upsert_rows

ROOT = Path(__file__).resolve().parents[1]
ETL_DIR = ROOT / "outputs" / "etl"

SKIP_TABS = {"clarity_daily", "experiments_observed"}


def latest_payload_per_date() -> list[dict]:
    by_date: dict[str, Path] = {}
    for p in sorted(ETL_DIR.glob("etl_payload_*.json")):
        # etl_payload_2026-05-03_20260504T....json
        d = p.name.split("_")[2]
        by_date[d] = p  # sorted asc → last (latest ts) wins
    out = []
    for d in sorted(by_date):
        try:
            out.append(json.loads(by_date[d].read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def dedupe(rows: list[dict], key_cols: list[str]) -> list[dict]:
    """키별 마지막 행만 유지 (순서 보존)."""
    seen: dict[tuple, int] = {}
    for i, r in enumerate(rows):
        seen[tuple(str(r.get(c, "")) for c in key_cols)] = i
    keep = set(seen.values())
    return [r for i, r in enumerate(rows) if i in keep]


def main() -> int:
    env = load_env()
    if not env.get("GOOGLE_SHEETS_ID"):
        print("GOOGLE_SHEETS_ID 미설정"); return 1
    sh = open_sheet(env)

    payloads = latest_payload_per_date()
    print(f"payloads: {len(payloads)} days")

    for tab, spec in SCHEMA.items():
        if tab in SKIP_TABS:
            continue
        rows: list[dict] = []
        for p in payloads:
            rows.extend(p.get(tab) or [])
        if not rows:
            continue
        rows = dedupe(rows, spec["key_cols"])
        res = upsert_rows(sh, tab, rows)
        print(f"  {tab:22} upsert rows={len(rows):5} → {res}")
    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""
ETL 페이로드 81일치 → 탭별 CSV consolidate.
clarity_daily 제외 (11-monitor v2 스킬 범위에서 제외됨).

사용:
    python3 11_dashboard/sheets/_build_sheets.py
"""

import csv
import glob
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ETL_DIR = ROOT.parent / "etl"
OUT_DIR = ROOT

# 출력 대상 탭 (clarity_daily 제외)
TABS = [
    "meta_daily",
    "meta_breakdowns",
    "meta_demographics",
    "meta_creatives",
    "ga4_daily",
    "ga4_channel_daily",
    "ga4_device_daily",
    "ga4_landing_daily",
    "ga4_product_daily",
    "ga4_funnel_daily",
    "ga4_demo_daily",
    "ga4_geo_daily",
]


def main():
    payloads = sorted(glob.glob(str(ETL_DIR / "etl_payload_*.json")))
    print(f"ETL 페이로드 {len(payloads)}개 발견")

    rows_by_tab: dict[str, list[dict]] = {tab: [] for tab in TABS}

    for path in payloads:
        with open(path) as f:
            payload = json.load(f)
        for tab in TABS:
            if tab in payload and isinstance(payload[tab], list):
                rows_by_tab[tab].extend(payload[tab])

    for tab, rows in rows_by_tab.items():
        if not rows:
            print(f"  ⚠️  {tab}: 0 rows — skip")
            continue
        # 컬럼 순서 = 첫 행 기준
        cols = list(rows[0].keys())
        # 누락 키가 있을 수도 있어 union 으로 보강
        for r in rows:
            for k in r.keys():
                if k not in cols:
                    cols.append(k)

        out = OUT_DIR / f"{tab}.csv"
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"  ✅ {tab}.csv — {len(rows)} rows · {len(cols)} cols")


if __name__ == "__main__":
    main()

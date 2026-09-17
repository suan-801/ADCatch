#!/usr/bin/env python3
"""Clarity UX 1페이지 HTML 대시보드 — v8_clarity_analytics.

데이터 소스:
  1) Google Sheets (`clarity_daily` 탭) — 일별 UX 신호 시계열
  2) etl_payload_*.json (dry-run dump) — 시트 없이도 작동
  3) outputs/cro/{brand}/*-cro-v*.md (최신) — 가설·페인 페이지 흡수 (옵션)

API 호출 ❌ — Clarity 일 10회 한도 보호. 라이브 호출은 Clarity MCP에서 별도.

사용:
  python3 scripts/render_clarity_dashboard.py [--date YYYY-MM-DD] [--brand sample_brand]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from lib.env_loader import load_env
from cro_report import THRESHOLDS  # 신호등 임계값 재사용

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates" / "period_variants"
OUT = ROOT.parent / "11_dashboard" / "dashboards"
ETL_OUT = ROOT.parent / "11_dashboard" / "etl"
CRO_DIR = ROOT.parent / "11_dashboard" / "cro"

CLARITY_TAB = "clarity_daily"
NUMERIC_KEYS = ["sessions", "dead_clicks", "rage_clicks", "excessive_scroll", "quick_back"]


def _load_from_dry_run(target: date) -> list[dict] | None:
    candidates = sorted(ETL_OUT.glob(f"etl_payload_{target.isoformat()}_*.json"), reverse=True)
    if not candidates:
        return None
    data = json.loads(candidates[0].read_text(encoding="utf-8"))
    rows = data.get(CLARITY_TAB) or []
    if isinstance(rows, dict):
        rows = [rows]
    return rows


def _load_from_sheets(env: dict[str, str], target: date, trend_days: int = 30) -> list[dict] | None:
    try:
        from lib.sheet_client import open_sheet
    except Exception:
        return None
    if not env.get("GOOGLE_SHEETS_ID"):
        return None
    sh = open_sheet(env)
    iso = target.isoformat()
    trend_start = (target - timedelta(days=trend_days - 1)).isoformat()
    try:
        ws = sh.worksheet(CLARITY_TAB)
    except Exception:
        return []
    all_values = ws.get_all_values()
    if not all_values:
        return []
    headers = all_values[0]
    rows = []
    for row in all_values[1:]:
        r = dict(zip(headers, row))
        if trend_start <= r.get("date", "") <= iso:
            rows.append(r)
    return rows


def _coerce_numeric(rows: list[dict], numeric_keys: list[str]) -> list[dict]:
    out = []
    for r in rows:
        nr = dict(r)
        for k in numeric_keys:
            if k in nr and nr[k] != "":
                try:
                    nr[k] = float(nr[k]) if "." in str(nr[k]) else int(nr[k])
                except (ValueError, TypeError):
                    nr[k] = 0
        out.append(nr)
    return out


def latest_cro_markdown(brand: str) -> tuple[Path | None, str | None]:
    folder = CRO_DIR / brand
    if not folder.exists():
        return None, None
    files = sorted(folder.glob("*-cro-v*.md"))
    if not files:
        return None, None
    p = files[-1]
    return p, p.read_text(encoding="utf-8")


# 마크다운 파서 — cro_report.md.j2 가 생성하는 형식만 인식.
HYP_RE = re.compile(
    r"^### 가설 \d+: (?P<title>.+?)\n+"
    r"- \*\*근거\*\*: (?P<evidence>.+?)\n"
    r"- \*\*가설\*\*: (?P<hypothesis>.+?)\n"
    r"- \*\*다음 액션\*\*: (?P<action>.+?)\n",
    re.MULTILINE | re.DOTALL,
)


def parse_hypotheses(md: str) -> list[dict]:
    """## 4. 가설 ... 섹션에서 가설 블록 추출."""
    if not md:
        return []
    # 4 섹션 ~ 5 섹션 사이만 잘라내기
    m = re.search(r"## 4\. .*?(?=^## 5\.)", md, re.MULTILINE | re.DOTALL)
    chunk = m.group(0) if m else md
    out = []
    for hit in HYP_RE.finditer(chunk):
        d = hit.groupdict()
        # 첫 줄만 — 후속 줄(- **검증**: ...) 잘림 방지로 strip
        out.append({k: v.strip().split("\n")[0] for k, v in d.items()})
    return out[:3]


# TOP 페인 페이지 표 — `| URL | 세션 | rage% | dead% | scroll% | quick_back% | 페인 라벨 |`
PAIN_TABLE_HEADER_RE = re.compile(r"## 2\. TOP \d+ 페인 페이지.*?\n\| URL.*?\n\|[-\s|]+\n", re.DOTALL)
PAIN_ROW_RE = re.compile(r"^\| `([^`]+)` \| (\d+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([\d.]+) \| ([^|]*)\|", re.MULTILINE)


def _threshold_class(val: float, metric: str) -> str:
    t = THRESHOLDS[metric]
    if val >= t["red"]:
        return "red"
    if val >= t["yellow"]:
        return "yellow"
    return ""


def parse_pain_pages(md: str) -> list[dict]:
    if not md:
        return []
    header = PAIN_TABLE_HEADER_RE.search(md)
    if not header:
        return []
    body_start = header.end()
    body = md[body_start:]
    # 표가 끝나는 첫 빈 줄까지
    end = body.find("\n\n")
    if end > 0:
        body = body[:end]
    out = []
    for row in PAIN_ROW_RE.finditer(body):
        url, sessions, rage, dead, scroll, qb, _label = row.groups()
        out.append({
            "url": url,
            "sessions": int(sessions),
            "rage_pct": float(rage),
            "dead_pct": float(dead),
            "scroll_pct": float(scroll),
            "quickback_pct": float(qb),
            "rage_class": _threshold_class(float(rage), "rage"),
            "dead_class": _threshold_class(float(dead), "dead"),
            "scroll_class": _threshold_class(float(scroll), "scroll"),
            "quickback_class": _threshold_class(float(qb), "quickback"),
        })
    return out[:5]


def render(brand: str, target: date, rows: list[dict]) -> Path:
    daily = _coerce_numeric(rows, NUMERIC_KEYS)
    daily = sorted(daily, key=lambda r: r.get("date", ""))

    raw = {"daily": daily}
    raw_json = json.dumps(raw, ensure_ascii=False, default=str)

    all_dates = sorted({r.get("date", "") for r in daily if r.get("date")})
    date_min = all_dates[0] if all_dates else target.isoformat()
    date_max = all_dates[-1] if all_dates else target.isoformat()
    tier_raw = next((r.get("freshness") for r in reversed(daily) if r.get("freshness")), "t3_clarity")
    tier = str(tier_raw) if tier_raw else "t3_clarity"

    md_path, md_text = latest_cro_markdown(brand)
    hypotheses = parse_hypotheses(md_text or "")
    pain_pages = parse_pain_pages(md_text or "")
    cro_meta = {
        "label": md_path.name if md_path else "",
        "path": str(md_path.relative_to(ROOT)) if md_path else "",
    }

    env_j = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    tpl = env_j.get_template("v8_clarity_analytics.html.j2")

    nav = {
        "nav_overview_url": f"overview_{target.isoformat()}.html",
        "nav_ga4_url": f"ga4_dashboard_{target.isoformat()}_v6.html",
        "nav_clarity_url": f"clarity_dashboard_{target.isoformat()}.html",
        "nav_meta_url": f"meta_dashboard_{target.isoformat()}.html",
    }
    html = tpl.render(
        brand=brand,
        period_start=date_min,
        period_end=date_max,
        days=len(all_dates) or 1,
        tier=tier,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        date_min=date_min,
        date_max=date_max,
        raw_json=raw_json,
        thresholds=THRESHOLDS,
        thresholds_json=json.dumps(THRESHOLDS, ensure_ascii=False),
        hypotheses=hypotheses,
        pain_pages=pain_pages,
        cro_meta=cro_meta,
        **nav,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"clarity_dashboard_{target.isoformat()}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (기본: 어제)")
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--source", choices=["auto", "sheets", "dry_run"], default="auto")
    p.add_argument("--days", type=int, default=30, help="트렌드 차트 일수 (기본 30)")
    args = p.parse_args()

    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date else date.today() - timedelta(days=1)
    )
    env = load_env()

    rows: list[dict] | None = None
    if args.source in ("auto", "sheets"):
        try:
            rows = _load_from_sheets(env, target, trend_days=args.days)
            if rows:
                print(f"▶ 데이터 소스: Google Sheets ({env.get('GOOGLE_SHEETS_ID', '')[:8]}…) — {len(rows)}행")
            else:
                rows = None
        except Exception as e:
            print(f"  ⚠️ Sheets 읽기 실패: {e}")
            rows = None
    if rows is None and args.source in ("auto", "dry_run"):
        rows = _load_from_dry_run(target)
        if rows:
            print(f"▶ 데이터 소스: dry-run dump ({target})")
    if rows is None:
        print(f"✗ {target} Clarity 데이터 없음 — 먼저 etl_run.py 실행 필요")
        return 1

    out = render(args.brand, target, rows)
    print(f"✓ Clarity 대시보드: {out.relative_to(ROOT)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

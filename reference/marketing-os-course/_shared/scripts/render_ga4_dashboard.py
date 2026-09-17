#!/usr/bin/env python3
"""GA4 1페이지 HTML 대시보드 — v5_ga4_onepager.

데이터 소스:
  1) Google Sheets (GOOGLE_SHEETS_ID 있을 때) — 운영 적재 데이터
  2) 최근 etl_payload_*.json (dry-run dump) — 시트 없이도 작동

사용:
  python3 scripts/render_ga4_dashboard.py [--date YYYY-MM-DD] [--brand sample_brand]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader, StrictUndefined

from lib.env_loader import load_env

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates" / "period_variants"
OUT = ROOT.parent / "11_dashboard" / "dashboards"
ETL_OUT = ROOT.parent / "11_dashboard" / "etl"

GA4_TABS = [
    "ga4_daily", "ga4_channel_daily", "ga4_device_daily",
    "ga4_landing_daily", "ga4_product_daily", "ga4_funnel_daily",
    "ga4_demo_daily", "ga4_geo_daily",
]


def fmt_won(v):
    try:
        return f"{int(round(float(v))):,}원"
    except Exception:
        return "0원"


def _load_from_dry_run(target: date, trend_days: int = 30) -> dict[str, list[dict]] | None:
    """최근 trend_days 일의 dry-run dump 누적 (Sheets 없이 30일 트렌드). GA4 탭은 전부 date 보유 → 단순 누적."""
    out: dict[str, list[dict]] = {tab: [] for tab in GA4_TABS}
    found = False
    for i in range(trend_days):
        d = target - timedelta(days=i)
        candidates = sorted(ETL_OUT.glob(f"etl_payload_{d.isoformat()}_*.json"), reverse=True)
        if not candidates:
            continue
        data = json.loads(candidates[0].read_text(encoding="utf-8"))
        found = True
        for tab in GA4_TABS:
            rows = data.get(tab) or []
            if isinstance(rows, dict):
                rows = [rows]
            out[tab].extend(rows)
    return out if found else None


def _load_from_sheets(env: dict[str, str], target: date, trend_days: int = 30) -> dict[str, list[dict]] | None:
    """시트 7탭 중 trend_start ~ target 범위 행 전체 추출 (인터랙티브 필터링용 raw 데이터)."""
    try:
        from lib.sheet_client import SCHEMA, open_sheet
    except Exception:
        return None
    if not env.get("GOOGLE_SHEETS_ID"):
        return None
    sh = open_sheet(env)
    iso = target.isoformat()
    trend_start = (target - timedelta(days=trend_days - 1)).isoformat()
    out: dict[str, list[dict]] = {}
    for tab in GA4_TABS:
        try:
            ws = sh.worksheet(tab)
        except Exception:
            out[tab] = []
            continue
        all_values = ws.get_all_values()
        if not all_values:
            out[tab] = []
            continue
        headers = all_values[0]
        rows: list[dict] = []
        for row in all_values[1:]:
            r = dict(zip(headers, row))
            if trend_start <= r.get("date", "") <= iso:
                rows.append(r)
        out[tab] = rows
    return out


def _coerce_numeric(rows: list[dict], numeric_keys: list[str]) -> list[dict]:
    """시트에서 읽은 문자열 값을 숫자로 변환."""
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


def _build_kpi(daily: list[dict], devices: list[dict], trend: list[dict]) -> dict:
    """target 일 KPI 4개 + 직전 7일 평균 대비 WoW delta.

    trend 은 date 오름차순 N일치 ga4_daily. devices 는 target 일 디바이스 합 → 매출 산출.
    """
    if not daily:
        return {
            "sessions": 0, "purchases": 0, "cvr": 0.0, "revenue": 0,
            "sessions_delta": 0.0, "purchase_delta": 0, "cvr_delta": 0.0, "revenue_delta": 0.0,
        }
    d = daily[0]
    sessions = int(d.get("sessions", 0))
    purchases = int(d.get("conversions", 0))
    cvr = (purchases / sessions * 100) if sessions else 0.0
    revenue = sum(float(r.get("revenue", 0) or 0) for r in devices)

    # 직전 7일 평균 (target 제외)
    prior = [t for t in trend if t.get("date") != d.get("date")][-7:]
    if prior:
        prior_sessions = sum(int(t.get("sessions", 0) or 0) for t in prior) / len(prior)
        prior_purchases = sum(int(t.get("conversions", 0) or 0) for t in prior) / len(prior)
        prior_cvr = (prior_purchases / prior_sessions * 100) if prior_sessions else 0.0
        sessions_delta = ((sessions - prior_sessions) / prior_sessions * 100) if prior_sessions else 0.0
        purchase_delta = round(purchases - prior_purchases)
        cvr_delta = cvr - prior_cvr
        revenue_delta = 0.0  # 매출은 단일일 device 합계만 — 트렌드 비교는 ga4_daily 에 매출 없어 생략
    else:
        sessions_delta = purchase_delta = cvr_delta = revenue_delta = 0.0
    return {
        "sessions": sessions,
        "purchases": purchases,
        "cvr": cvr,
        "revenue": revenue,
        "sessions_delta": sessions_delta,
        "purchase_delta": purchase_delta,
        "cvr_delta": cvr_delta,
        "revenue_delta": revenue_delta,
    }


TEMPLATE_BY_VARIANT = {
    "v5": "v5_ga4_onepager.html.j2",
    "v6": "v6_ga4_analytics.html.j2",
}


def render(brand: str, target: date, payload: dict[str, list[dict]], variant: str = "v5") -> Path:
    trend_all = _coerce_numeric(payload.get("ga4_daily") or [], ["sessions", "users", "new_users", "returning_users", "active_users", "avg_session_duration", "conversions"])
    trend_all = sorted(trend_all, key=lambda r: r.get("date", ""))
    channels = _coerce_numeric(payload.get("ga4_channel_daily") or [], ["sessions", "new_users", "engaged_sessions", "conversions", "revenue"])
    devices = _coerce_numeric(payload.get("ga4_device_daily") or [], ["sessions", "users", "conversions", "cvr", "revenue"])
    landings = _coerce_numeric(payload.get("ga4_landing_daily") or [], ["sessions", "engaged_sessions", "bounce_rate", "conversions", "revenue"])
    products = _coerce_numeric(payload.get("ga4_product_daily") or [], ["item_views", "add_to_carts", "purchases", "revenue", "view_to_atc", "atc_to_purchase"])
    funnel_rows = _coerce_numeric(payload.get("ga4_funnel_daily") or [], ["page_view", "view_item", "add_to_cart", "view_cart", "purchase_total", "view_to_pdp", "pdp_to_atc", "atc_to_cart", "cart_to_purchase", "overall_cvr"])
    demos = _coerce_numeric(payload.get("ga4_demo_daily") or [], ["sessions", "users", "conversions", "revenue"])
    geos = _coerce_numeric(payload.get("ga4_geo_daily") or [], ["sessions", "users", "conversions", "revenue"])

    # raw 데이터 전체를 JSON 으로 임베드 — JS 가 날짜 필터링 + 집계 수행
    raw = {
        "trend": trend_all,
        "channels": channels,
        "devices": devices,
        "landings": landings,
        "products": products,
        "funnels": funnel_rows,
        "demos": demos,
        "geos": geos,
    }
    raw_json = json.dumps(raw, ensure_ascii=False, default=str)

    # 사용 가능한 날짜 범위
    all_dates = sorted({t.get("date", "") for t in trend_all if t.get("date")})
    date_min = all_dates[0] if all_dates else target.isoformat()
    date_max = all_dates[-1] if all_dates else target.isoformat()
    tier = "30d" if len(all_dates) >= 25 else ("partial" if all_dates else "empty")

    env = Environment(loader=FileSystemLoader(str(TEMPLATES)), undefined=StrictUndefined)
    env.globals["fmt_won"] = fmt_won
    template_name = TEMPLATE_BY_VARIANT.get(variant, TEMPLATE_BY_VARIANT["v5"])
    tpl = env.get_template(template_name)
    suffix = "" if variant == "v5" else f"_{variant}"
    nav = {
        "nav_overview_url": f"overview_{target.isoformat()}.html",
        "nav_ga4_url": f"ga4_dashboard_{target.isoformat()}{suffix}.html",
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
        **nav,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"ga4_dashboard_{target.isoformat()}{suffix}.html"
    out_path.write_text(html, encoding="utf-8")
    return out_path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (기본: 어제)")
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--source", choices=["auto", "sheets", "dry_run"], default="auto")
    p.add_argument("--days", type=int, default=30, help="트렌드 차트 일수 (기본 30)")
    p.add_argument("--variant", choices=list(TEMPLATE_BY_VARIANT.keys()), default="v5",
                   help="템플릿 변형 (v5=라이트 카드, v6=다크 네비+스파크라인)")
    args = p.parse_args()

    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date else date.today() - timedelta(days=1)
    )
    env = load_env()

    payload: dict[str, list[dict]] | None = None
    if args.source in ("auto", "sheets"):
        try:
            payload = _load_from_sheets(env, target, trend_days=args.days)
            if payload and any(payload.values()):
                print(f"▶ 데이터 소스: Google Sheets ({env.get('GOOGLE_SHEETS_ID', '')[:8]}…)")
            else:
                payload = None
        except Exception as e:
            print(f"  ⚠️ Sheets 읽기 실패: {e}")
            payload = None
    if payload is None and args.source in ("auto", "dry_run"):
        payload = _load_from_dry_run(target, trend_days=args.days)
        if payload:
            print(f"▶ 데이터 소스: dry-run dump ({target})")
    if payload is None:
        print(f"✗ {target} 데이터 없음 — 먼저 etl_run.py 실행 필요")
        return 1

    out = render(args.brand, target, payload, variant=args.variant)
    print(f"✓ HTML 대시보드: {out.relative_to(ROOT.parent)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

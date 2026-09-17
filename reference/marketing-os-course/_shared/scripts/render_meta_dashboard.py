#!/usr/bin/env python3
"""Meta Ads 1페이지 HTML 대시보드 — v7_meta_analytics.

데이터 소스 (auto):
  1) Google Sheets (`meta_daily` + `meta_breakdowns` 탭)
  2) 최근 etl_payload_*.json dry-run dump (시트 없이도 작동)

사용:
  python3 scripts/render_meta_dashboard.py [--date YYYY-MM-DD] [--brand sample_brand]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from jinja2 import Environment, FileSystemLoader

from lib.env_loader import load_env
from lib.kpi_config import load as load_kpi

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates" / "period_variants"
OUT = ROOT.parent / "11_dashboard" / "dashboards"
ETL_OUT = ROOT.parent / "11_dashboard" / "etl"
LOCAL_CREATIVES = ROOT.parent / "11_dashboard" / "creatives"

META_TABS = ["meta_daily", "meta_breakdowns", "meta_creatives", "meta_demographics"]

# 영상 우선 — 같은 ad_name 에 이미지+영상 모두 있으면 영상이 갤러리에 노출
LOCAL_VIDEO_EXTS = [".mp4", ".mov", ".webm"]
LOCAL_IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]
LOCAL_EXT_PRIORITY = LOCAL_VIDEO_EXTS + LOCAL_IMAGE_EXTS


def _normalize_ad_key(name: str) -> str:
    """ad_name 정규화 — 한 파일을 _FP/non-FP/공백 변형 시트행에 모두 매칭시키기 위함.

    규칙:
      - 소문자 + 공백 → _
      - 끝의 `_fp` / `_re` / `_revise` / `_1대1` 반복 제거
      - `meta\\d+` 첫 토큰을 3자리 zero-padding 으로 정규화 (meta51 → meta051)
    """
    import re
    s = name.strip().lower().replace(" ", "_")
    for _ in range(5):
        changed = False
        for suf in ("_fp", "_1대1", "_revise", "_re"):
            if s.endswith(suf):
                s = s[:-len(suf)]
                changed = True
        if not changed:
            break
    s = re.sub(r"^meta(\d{1,3})", lambda m: f"meta{int(m.group(1)):03d}", s)
    return s


def _scan_local_creatives() -> dict[str, dict]:
    """outputs/creatives/{ad_name}.{ext} 스캔 → {stem: {path, kind, norm_key}}.

    HTML 이 outputs/ 에 떨어지므로 상대경로 'creatives/{filename}' 로 임베드.
    같은 stem 에 여러 확장자 있으면 LOCAL_EXT_PRIORITY 순서로 1개만 선택.
    """
    if not LOCAL_CREATIVES.exists():
        return {}
    found: dict[str, dict[str, str]] = {}
    for f in LOCAL_CREATIVES.iterdir():
        if not f.is_file() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext not in LOCAL_EXT_PRIORITY:
            continue
        ad_name = f.stem
        found.setdefault(ad_name, {})[ext] = f.name
    out: dict[str, dict] = {}
    for ad_name, exts in found.items():
        for ext in LOCAL_EXT_PRIORITY:
            if ext in exts:
                kind = "video" if ext in LOCAL_VIDEO_EXTS else "image"
                out[ad_name] = {
                    "path": f"../creatives/{exts[ext]}",
                    "kind": kind,
                    "norm_key": _normalize_ad_key(ad_name),
                }
                break
    return out


def _meta_prefix(s: str) -> str:
    """`meta\\d+` 토큰만 추출 — 날짜·이니셜 변형 흡수용 최후 폴백."""
    import re
    m = re.match(r"^meta(\d{1,3})", s.lower())
    return f"meta{int(m.group(1)):03d}" if m else ""


def _match_ads_to_local(ad_names: list[str], local_by_stem: dict[str, dict]) -> dict[str, dict]:
    """시트 ad_name 별로 가장 적합한 로컬 파일 매핑 → {ad_name: asset}.

    매칭 우선순위:
      1) 정확 stem 일치
      2) 정규화 키 일치 (_FP/공백/`_re`/0패딩 변형 흡수)
      3) `meta\\d+` 프리픽스 일치 (날짜 오타·날짜 없는 단축 파일명 흡수)
    """
    norm_to_stem: dict[str, str] = {}
    for stem, data in local_by_stem.items():
        norm_to_stem.setdefault(data["norm_key"], stem)

    prefix_to_stem: dict[str, str] = {}
    for stem, data in local_by_stem.items():
        prefix = _meta_prefix(data["norm_key"])
        if prefix:
            prefix_to_stem.setdefault(prefix, stem)

    matched: dict[str, dict] = {}
    for ad_name in ad_names:
        if not ad_name:
            continue
        if ad_name in local_by_stem:
            matched[ad_name] = local_by_stem[ad_name]
            continue
        norm = _normalize_ad_key(ad_name)
        if norm in norm_to_stem:
            matched[ad_name] = local_by_stem[norm_to_stem[norm]]
            continue
        prefix = _meta_prefix(norm)
        if prefix and prefix in prefix_to_stem:
            matched[ad_name] = local_by_stem[prefix_to_stem[prefix]]
    return matched


def _load_from_dry_run(target: date, trend_days: int = 30) -> dict[str, list[dict]] | None:
    """최근 trend_days 일의 dry-run dump 누적 (Sheets 없이 30일 트렌드)."""
    out: dict[str, list[dict]] = {tab: [] for tab in META_TABS}
    seen_creative: set[str] = set()
    found = False
    for i in range(trend_days):
        d = target - timedelta(days=i)
        candidates = sorted(ETL_OUT.glob(f"etl_payload_{d.isoformat()}_*.json"), reverse=True)
        if not candidates:
            continue
        data = json.loads(candidates[0].read_text(encoding="utf-8"))
        found = True
        for tab in META_TABS:
            rows = data.get(tab) or []
            if isinstance(rows, dict):
                rows = [rows]
            if tab == "meta_creatives":
                # date 없는 캐시 — ad_id 중복 제거 (target 부터 역순이라 최신 유지)
                for r in rows:
                    aid = str(r.get("ad_id") or "")
                    if aid and aid not in seen_creative:
                        seen_creative.add(aid)
                        out[tab].append(r)
            else:
                out[tab].extend(rows)
    return out if found else None


def _load_from_sheets(env: dict[str, str], target: date, trend_days: int = 30) -> dict[str, list[dict]] | None:
    """시트 2탭 trend_start ~ target 범위 행 추출."""
    try:
        from lib.sheet_client import open_sheet
    except Exception:
        return None
    if not env.get("GOOGLE_SHEETS_ID"):
        return None
    sh = open_sheet(env)
    iso = target.isoformat()
    trend_start = (target - timedelta(days=trend_days - 1)).isoformat()
    out: dict[str, list[dict]] = {}
    for tab in META_TABS:
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
        # meta_creatives 는 date 컬럼이 없는 캐시 — 날짜 필터 우회
        skip_date_filter = "date" not in headers
        for row in all_values[1:]:
            r = dict(zip(headers, row))
            if skip_date_filter or trend_start <= r.get("date", "") <= iso:
                rows.append(r)
        out[tab] = rows
    return out


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


META_DAILY_NUMERIC = [
    "spend", "impressions", "clicks", "ctr", "cpm", "cpc",
    "purchases", "purchase_value", "roas", "cpa", "aov",
    "add_to_carts", "checkouts",
]
META_BREAKDOWN_NUMERIC = [
    "spend", "impressions", "reach", "frequency",
    "clicks", "link_clicks", "ctr", "cpm", "cpc",
    "landing_views", "cpa_landing",
    "add_to_carts", "cpa_atc",
    "checkouts", "cpa_checkout",
    "purchases", "purchase_value", "roas", "cpa",
]
META_DEMO_NUMERIC = [
    "spend", "impressions", "reach", "clicks",
    "purchases", "purchase_value", "roas",
]


def render(brand: str, target: date, payload: dict[str, list[dict]]) -> Path:
    daily = _coerce_numeric(payload.get("meta_daily") or [], META_DAILY_NUMERIC)
    daily = sorted(daily, key=lambda r: r.get("date", ""))
    breakdowns = _coerce_numeric(payload.get("meta_breakdowns") or [], META_BREAKDOWN_NUMERIC)

    campaigns = [r for r in breakdowns if r.get("level") == "campaign"]
    ads = [r for r in breakdowns if r.get("level") == "ad"]
    creatives = payload.get("meta_creatives") or []
    demographics = _coerce_numeric(payload.get("meta_demographics") or [], META_DEMO_NUMERIC)
    local_by_stem = _scan_local_creatives()
    ad_names = [r.get("ad_name", "") for r in ads]
    local_assets = _match_ads_to_local(ad_names, local_by_stem)

    campaign_names = sorted({r.get("campaign_name", "") for r in breakdowns if r.get("campaign_name")})
    adset_names = sorted({r.get("adset_name", "") for r in breakdowns if r.get("adset_name")})
    ad_name_options = sorted({r.get("ad_name", "") for r in ads if r.get("ad_name")})

    raw = {
        "daily": daily, "campaigns": campaigns, "ads": ads,
        "creatives": creatives, "local_assets": local_assets,
        "demographics": demographics,
        "filter_options": {
            "campaigns": campaign_names,
            "adsets": adset_names,
            "ads": ad_name_options,
        },
    }
    raw_json = json.dumps(raw, ensure_ascii=False, default=str)

    all_dates = sorted({r.get("date", "") for r in daily if r.get("date")})
    date_min = all_dates[0] if all_dates else target.isoformat()
    date_max = all_dates[-1] if all_dates else target.isoformat()
    tier_raw = next((r.get("freshness") for r in reversed(daily) if r.get("freshness")), "unknown")
    tier = str(tier_raw) if tier_raw else "unknown"

    thresholds = load_kpi(brand)

    env_j = Environment(loader=FileSystemLoader(str(TEMPLATES)))
    tpl = env_j.get_template("v7_meta_analytics.html.j2")

    nav = {
        "nav_overview_url": f"overview_{target.isoformat()}.html",
        "nav_ga4_url": f"ga4_dashboard_{target.isoformat()}.html",
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
        spend_min=thresholds.spend_min,
        roas_red=thresholds.roas_red,
        roas_green=thresholds.roas_green,
        **nav,
    )
    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"meta_dashboard_{target.isoformat()}.html"
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
        print(f"✗ {target} Meta 데이터 없음 — 먼저 etl_run.py 실행 필요")
        return 1

    out = render(args.brand, target, payload)
    print(f"✓ Meta 대시보드: {out.relative_to(ROOT.parent)} ({out.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

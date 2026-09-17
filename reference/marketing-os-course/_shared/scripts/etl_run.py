#!/usr/bin/env python3
"""
/11-monitor — Meta·GA4·Clarity → Google Sheets 5탭 ETL 오케스트레이터.

- Meta: meta_daily + meta_breakdowns (campaign/ad level)
- GA4: ga4_daily
- Clarity: clarity_daily (한도 보호, --skip-clarity 가능)

Sheets 키가 없으면 --dry-run 모드 — 페이로드를 outputs/etl/ 로 dump.

사용:
  python3 etl_run.py [--date YYYY-MM-DD] [--brand sample_brand] [--skip-clarity] [--dry-run]
"""
from __future__ import annotations

import argparse
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.env_loader import load_env, require
from lib.meta_client import MetaClient, aggregate, freshness_tier
from lib.sheet_client import SCHEMA, DryRunSink, open_sheet, upsert_rows

ROOT = Path(__file__).resolve().parents[1]
ETL_OUT = ROOT.parent / "11_dashboard" / "etl"


def build_meta_rows(env: dict, target: date) -> tuple[list[dict], list[dict]]:
    """Meta → meta_daily 1행 + meta_breakdowns N행."""
    client = MetaClient(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target)
    now = datetime.now().isoformat(timespec="seconds")

    campaigns = client.insights(s, s, level="campaign")
    ads = client.insights(s, s, level="ad")
    account_rows = client.insights(s, s, level="account")
    total = account_rows[0] if account_rows else aggregate(ads)

    aov = (total.purchase_value / total.purchases) if total.purchases else 0.0
    daily_row = {
        "date": s,
        "spend": round(total.spend, 2),
        "impressions": total.impressions,
        "clicks": total.clicks,
        "ctr": round(total.ctr, 4),
        "cpm": round(total.cpm, 2),
        "cpc": round(total.cpc, 2),
        "purchases": int(total.purchases),
        "purchase_value": round(total.purchase_value, 2),
        "roas": round(total.roas, 4),
        "cpa": round(total.cpa, 2),
        "aov": round(aov, 2),
        "add_to_carts": int(total.add_to_carts),
        "checkouts": int(total.checkouts),
        "freshness": tier,
        "updated_at": now,
    }

    def _funnel_cpa(spend: float, count: float) -> float:
        return round(spend / count, 2) if count > 0 else 0.0

    breakdowns: list[dict] = []
    for c in campaigns:
        breakdowns.append({
            "date": s, "level": "campaign", "id": c.raw.get("campaign_id", c.campaign_name),
            "campaign_name": c.campaign_name, "adset_name": "", "ad_name": "",
            "spend": round(c.spend, 2), "impressions": c.impressions,
            "reach": c.reach, "frequency": round(c.frequency, 4),
            "clicks": c.clicks, "link_clicks": int(c.link_clicks),
            "ctr": round(c.ctr, 4), "cpm": round(c.cpm, 2), "cpc": round(c.cpc, 2),
            "landing_views": int(c.landing_views), "cpa_landing": _funnel_cpa(c.spend, c.landing_views),
            "add_to_carts": int(c.add_to_carts), "cpa_atc": _funnel_cpa(c.spend, c.add_to_carts),
            "checkouts": int(c.checkouts), "cpa_checkout": _funnel_cpa(c.spend, c.checkouts),
            "purchases": int(c.purchases), "purchase_value": round(c.purchase_value, 2),
            "roas": round(c.roas, 4), "cpa": round(c.cpa, 2),
            "freshness": tier, "updated_at": now,
        })
    for a in ads:
        breakdowns.append({
            "date": s, "level": "ad", "id": a.ad_id or a.ad_name,
            "campaign_name": a.campaign_name, "adset_name": a.adset_name, "ad_name": a.ad_name,
            "spend": round(a.spend, 2), "impressions": a.impressions,
            "reach": a.reach, "frequency": round(a.frequency, 4),
            "clicks": a.clicks, "link_clicks": int(a.link_clicks),
            "ctr": round(a.ctr, 4), "cpm": round(a.cpm, 2), "cpc": round(a.cpc, 2),
            "landing_views": int(a.landing_views), "cpa_landing": _funnel_cpa(a.spend, a.landing_views),
            "add_to_carts": int(a.add_to_carts), "cpa_atc": _funnel_cpa(a.spend, a.add_to_carts),
            "checkouts": int(a.checkouts), "cpa_checkout": _funnel_cpa(a.spend, a.checkouts),
            "purchases": int(a.purchases), "purchase_value": round(a.purchase_value, 2),
            "roas": round(a.roas, 4), "cpa": round(a.cpa, 2),
            "freshness": tier, "updated_at": now,
        })
    return [daily_row], breakdowns


def build_meta_demographics(env: dict, target: date) -> list[dict]:
    """Meta Insights breakdowns=age,gender 호출 → meta_demographics 행 N개.

    ad 레벨로 받아 광고별 인구통계 단위로 적재. 한 ad 당 7 age × 3 gender = 최대 21행.
    """
    client = MetaClient(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target)
    now = datetime.now().isoformat(timespec="seconds")
    rows: list[dict] = []
    try:
        demo_rows = client.insights(
            s, s, level="ad",
            extra_params={"breakdowns": ["age", "gender"]},
        )
    except Exception as e:
        print(f"  ⚠️ meta_demographics skip: {e}")
        return rows
    for r in demo_rows:
        raw = r.raw
        rows.append({
            "date": s, "level": "ad", "id": r.ad_id or r.ad_name,
            "campaign_name": r.campaign_name,
            "adset_name": r.adset_name,
            "ad_name": r.ad_name,
            "gender": raw.get("gender", "") or "unknown",
            "age": raw.get("age", "") or "unknown",
            "spend": round(r.spend, 2),
            "impressions": r.impressions,
            "reach": r.reach,
            "clicks": r.clicks,
            "purchases": int(r.purchases),
            "purchase_value": round(r.purchase_value, 2),
            "roas": round(r.roas, 4),
            "freshness": tier, "updated_at": now,
        })
    return rows


def existing_creative_ad_ids(sh_or_sink, dry: bool) -> set[str]:
    """meta_creatives 시트의 기캐시 ad_id 목록 — dry-run 시 빈 집합."""
    if dry:
        return set()
    try:
        ws = sh_or_sink.worksheet("meta_creatives")
    except Exception:
        return set()
    rows = ws.get_all_values()
    if len(rows) < 2:
        return set()
    headers = rows[0]
    if "ad_id" not in headers:
        return set()
    idx = headers.index("ad_id")
    return {r[idx] for r in rows[1:] if len(r) > idx and r[idx]}


def build_creative_rows(client: "MetaClient", ad_breakdowns: list[dict], known_ids: set[str],
                        now_iso: str, max_fetch: int = 30) -> list[dict]:
    """meta_creatives 신규 행 — 캐시되지 않은 ad_id 만 Meta API 로 fetch.

    max_fetch 로 1회 ETL 당 fetch 호출 횟수를 캡 (대용량 계정 대비).
    """
    rows: list[dict] = []
    seen: set[str] = set()
    fetched = 0
    for a in ad_breakdowns:
        if a.get("level") != "ad":
            continue
        ad_id = str(a.get("id") or "")
        if not ad_id or ad_id in known_ids or ad_id in seen:
            continue
        seen.add(ad_id)
        if fetched >= max_fetch:
            break
        cr = client.fetch_creative(ad_id)
        fetched += 1
        if cr is None:
            continue
        rows.append({
            "ad_id": ad_id,
            "ad_name": a.get("ad_name", ""),
            "adset_name": a.get("adset_name", ""),
            "campaign_name": a.get("campaign_name", ""),
            "thumbnail_url": cr["thumbnail_url"],
            "image_url": cr["image_url"],
            "video_id": cr["video_id"],
            "title": cr["title"],
            "body": cr["body"],
            "call_to_action_type": cr["call_to_action_type"],
            "fetched_at": now_iso,
            "updated_at": now_iso,
        })
    return rows


def build_ga4_row(env: dict, target: date) -> dict | None:
    try:
        from lib.ga4_client import daily_summary
        return daily_summary(env, target)
    except Exception as e:
        print(f"  ⚠️ GA4 skip: {e}")
        return None


def build_ga4_breakdowns(env: dict, target: date) -> dict[str, list[dict] | dict | None]:
    """6탭 분해 데이터 — channel/device/landing/product/funnel/demo. 탭별 None 가능."""
    out: dict[str, list[dict] | dict | None] = {
        "ga4_channel_daily": None,
        "ga4_device_daily": None,
        "ga4_landing_daily": None,
        "ga4_product_daily": None,
        "ga4_funnel_daily": None,
        "ga4_demo_daily": None,
        "ga4_geo_daily": None,
    }
    try:
        from lib import ga4_client
    except Exception as e:
        print(f"  ⚠️ GA4 breakdowns skip (import): {e}")
        return out

    builders = [
        ("ga4_channel_daily", lambda: ga4_client.channel_rows(env, target)),
        ("ga4_device_daily", lambda: ga4_client.device_rows(env, target)),
        ("ga4_landing_daily", lambda: ga4_client.landing_rows(env, target)),
        ("ga4_product_daily", lambda: ga4_client.product_rows(env, target)),
        ("ga4_funnel_daily", lambda: ga4_client.funnel_row(env, target)),
        ("ga4_demo_daily", lambda: ga4_client.demo_rows(env, target)),
        ("ga4_geo_daily", lambda: ga4_client.geo_rows(env, target)),
    ]
    for tab, fn in builders:
        try:
            out[tab] = fn()
        except Exception as e:
            print(f"  ⚠️ {tab} skip: {e}")
    return out


def build_clarity_row(env: dict, target: date, reserve: bool = True) -> dict | None:
    try:
        from lib.clarity_client import call, parse_daily
        token = env.get("CLARITY_API_TOKEN")
        if not token:
            print("  ⚠️ Clarity skip: CLARITY_API_TOKEN 미설정")
            return None
        payload = call(token, num_of_days=1, reason="etl_daily", reserve_for_cro=reserve)
        return parse_daily(payload, target)
    except Exception as e:
        print(f"  ⚠️ Clarity skip: {e}")
        return None


def write(sh_or_sink, tab: str, rows: list[dict], dry: bool) -> dict:
    if dry:
        return sh_or_sink.upsert(tab, rows)
    return upsert_rows(sh_or_sink, tab, rows)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (기본: 어제)")
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--skip-clarity", action="store_true")
    p.add_argument("--dry-run", action="store_true", help="Sheets 키 없이 페이로드만 dump")
    args = p.parse_args()

    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date else date.today() - timedelta(days=1)
    )
    env = load_env()
    require(env, ["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"])

    has_sheets = bool(env.get("GOOGLE_SHEETS_ID")) and (
        env.get("GOOGLE_SERVICE_ACCOUNT_PATH") or env.get("GOOGLE_SERVICE_ACCOUNT_JSON")
        or (env.get("GOOGLE_SERVICE_ACCOUNT_EMAIL") and env.get("GOOGLE_PRIVATE_KEY"))
    )
    dry = args.dry_run or not has_sheets

    print(f"▶ etl_run — date={target} brand={args.brand} dry_run={dry}")
    sink = DryRunSink(ETL_OUT) if dry else open_sheet(env)

    results: dict[str, dict] = {}

    # Meta
    try:
        daily, breakdowns = build_meta_rows(env, target)
        results["meta_daily"] = write(sink, "meta_daily", daily, dry)
        results["meta_breakdowns"] = write(sink, "meta_breakdowns", breakdowns, dry)
        print(f"  ✓ Meta: daily=1 breakdowns={len(breakdowns)}")

        # 성별·연령 분해 (브레이크다운 1회 추가 호출)
        try:
            demo_rows = build_meta_demographics(env, target)
            if demo_rows:
                results["meta_demographics"] = write(sink, "meta_demographics", demo_rows, dry)
                print(f"  ✓ meta_demographics: rows={len(demo_rows)}")
            else:
                print(f"  · meta_demographics: 0 rows")
        except Exception as e:
            print(f"  ⚠️ meta_demographics skip: {e}")

        # 신규 ad_id 만 creative 메타데이터 fetch (썸네일·카피·CTA)
        try:
            from lib.meta_client import MetaClient
            client = MetaClient(env)
            known_ids = existing_creative_ad_ids(sink, dry)
            now_iso = datetime.now().isoformat(timespec="seconds")
            creative_rows = build_creative_rows(client, breakdowns, known_ids, now_iso)
            if creative_rows:
                results["meta_creatives"] = write(sink, "meta_creatives", creative_rows, dry)
                print(f"  ✓ meta_creatives: 신규 {len(creative_rows)}건 (캐시 {len(known_ids)}건 스킵)")
            else:
                print(f"  · meta_creatives: 신규 0건 (캐시 {len(known_ids)}건)")
        except Exception as e:
            print(f"  ⚠️ meta_creatives skip: {e}")
    except Exception as e:
        print(f"  ✗ Meta 실패: {e}")
        traceback.print_exc()

    # GA4 — 합계 1행 + 6탭 분해
    ga4_row = build_ga4_row(env, target)
    if ga4_row:
        results["ga4_daily"] = write(sink, "ga4_daily", [ga4_row], dry)
        print(f"  ✓ GA4: sessions={ga4_row['sessions']}")

    ga4_breakdowns = build_ga4_breakdowns(env, target)
    for tab, payload in ga4_breakdowns.items():
        if payload is None:
            continue
        rows = [payload] if isinstance(payload, dict) else payload
        if not rows:
            continue
        results[tab] = write(sink, tab, rows, dry)
        print(f"  ✓ {tab}: rows={len(rows)}")

    # Clarity
    if not args.skip_clarity:
        clarity_row = build_clarity_row(env, target)
        if clarity_row:
            results["clarity_daily"] = write(sink, "clarity_daily", [clarity_row], dry)
            print(f"  ✓ Clarity: sessions={clarity_row['sessions']}")

    if dry:
        out = sink.flush(target.isoformat())
        print(f"\n📄 dry-run dump: {out.relative_to(ROOT.parent)}")
    else:
        print(f"\n✓ Sheets 갱신 완료: {results}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

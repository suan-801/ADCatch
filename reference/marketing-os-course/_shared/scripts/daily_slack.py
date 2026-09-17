#!/usr/bin/env python3
"""
/10-daily-slack — Meta Ads 어제 데이터 → Slack 메시지 1통.

- 입력: 09_tracking/.env (META_*, SLACK_WEBHOOK_URL), config/brand_kpi.yml
- 산출: outputs/daily/{브랜드}/{YYYY-MM-DD}-slack.{txt,json} + Slack 발송
- 어트리뷰션: Meta 기본 (7d-click + 1d-view). GA4 utm 블록은 보조.

사용:
  python3 daily_slack.py [--date YYYY-MM-DD] [--brand sample_brand] [--no-slack]
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # lib 임포트
from jinja2 import Environment, FileSystemLoader, select_autoescape

from lib.env_loader import load_env, require
from lib.meta_client import MetaClient, aggregate, AdRow
from lib.slack_client import SlackClient
from lib.kpi_config import load as load_kpi, light, Thresholds

ROOT = Path(__file__).resolve().parents[1]  # _shared/
TEMPLATES = ROOT / "templates"
OUTPUTS = ROOT.parent / "10_daily"
OUTPUTS.mkdir(parents=True, exist_ok=True)


def fmt_won(v: float) -> str:
    v = float(v or 0)
    if abs(v) >= 100_000_000:
        return f"{v/100_000_000:.2f}억"
    if abs(v) >= 10_000:
        return f"{v/10_000:.1f}만"
    return f"{int(v):,}원"


def fmt_num(v) -> str:
    try:
        return f"{int(float(v)):,}"
    except (TypeError, ValueError):
        return "-"


def pct_arrow(curr: float, prev: float) -> str:
    if not prev:
        return "—"
    pct = (curr - prev) / prev * 100
    arrow = "▲" if pct > 0 else ("▼" if pct < 0 else "▶")
    return f"{arrow}{abs(pct):.1f}%"


def pct_arrow_avg(curr: float, avg: float) -> str:
    return pct_arrow(curr, avg)


def build_alerts(total: AdRow, prev: AdRow, thresholds: Thresholds) -> list[str]:
    alerts: list[str] = []
    if thresholds.daily_budget and total.spend > thresholds.daily_budget * 1.2:
        alerts.append(f"일 예산 *{fmt_won(thresholds.daily_budget)}* 의 120% 초과 — 실제 {fmt_won(total.spend)}")
    if prev.spend and total.spend > prev.spend * 1.5:
        alerts.append(f"지출 전일 대비 +50% 이상 급증 ({pct_arrow(total.spend, prev.spend)})")
    if total.spend >= thresholds.spend_min and total.roas < thresholds.roas_red:
        alerts.append(f"전체 ROAS {total.roas:.2f} < 경계 {thresholds.roas_red}")
    if total.ctr and total.ctr < thresholds.ctr_red_pct:
        alerts.append(f"전체 CTR {total.ctr:.2f}% < 경계 {thresholds.ctr_red_pct}%")
    return alerts


def select_top_ads(rows: list[AdRow], thresholds: Thresholds, n: int = 5, mode: str = "top") -> list[AdRow]:
    candidates = [r for r in rows if r.spend >= thresholds.spend_min]
    if mode == "top":
        # 구매가 1건 이상 발생한 소재만 TOP. 구매 0 인 소재는 효율 미검증 → bottom 으로
        candidates = [r for r in candidates if r.purchases >= 1]
        candidates.sort(key=lambda r: (-r.roas, -r.purchase_value))
    else:  # bottom — 구매 없거나 ROAS < red
        candidates = [r for r in candidates if r.purchases == 0 or r.roas < thresholds.roas_red]
        candidates.sort(key=lambda r: (r.roas, -r.spend))
    return candidates[:n]


def select_top_campaigns(rows: list[AdRow], n: int = 5) -> list[AdRow]:
    sorted_ = sorted(rows, key=lambda r: -r.spend)
    return sorted_[:n]


def render(target: date, brand: str, daily: dict, thresholds: Thresholds, ga4_block: str | None) -> str:
    rows: list[AdRow] = daily["ads"]
    total = daily["account"][0] if daily["account"] else aggregate(rows)
    prev = daily["previous"][0] if daily["previous"] else aggregate([])
    week_rows = daily["week"] or []
    week_total = aggregate(week_rows) if week_rows else None
    week_avg_spend = (week_total.spend / 7) if week_total else 0.0

    top_campaigns = select_top_campaigns(daily["campaigns"], n=5)
    top_ads = select_top_ads(rows, thresholds, n=5, mode="top")
    bottom_ads = select_top_ads(rows, thresholds, n=3, mode="bottom")
    alerts = build_alerts(total, prev, thresholds)

    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template("slack_daily.j2")
    return tmpl.render(
        date=target.strftime("%Y-%m-%d"),
        brand=brand,
        tier=daily["tier"],
        total=total,
        prev_total=prev,
        week_total=week_total,
        week_avg_spend=week_avg_spend,
        top_campaigns=top_campaigns,
        top_ads=top_ads,
        bottom_ads=bottom_ads,
        alerts=alerts,
        thresholds=thresholds,
        ga4_block=ga4_block,
        light_roas=light(total.roas, thresholds.roas_green, thresholds.roas_red, higher_is_better=True),
        light_cpa=light(total.cpa or 1e9, thresholds.cpa_red * 0.6, thresholds.cpa_red, higher_is_better=False) if total.cpa else "🟡",
        light_for_roas=lambda v: light(v, thresholds.roas_green, thresholds.roas_red, higher_is_better=True),
        fmt_won=fmt_won, fmt_num=fmt_num,
        pct_arrow=pct_arrow, pct_arrow_avg=pct_arrow_avg,
    )


def save(date_str: str, brand: str, message: str, daily: dict) -> tuple[Path, Path]:
    folder = OUTPUTS / brand
    folder.mkdir(parents=True, exist_ok=True)
    txt = folder / f"{date_str}-slack.txt"
    js = folder / f"{date_str}-slack.json"
    txt.write_text(message, encoding="utf-8")

    # JSON: AdRow 는 dataclass — asdict 가능, raw 빼고 직렬화
    def serialize(rows):
        return [{k: v for k, v in r.__dict__.items() if k != "raw"} for r in rows]

    js.write_text(json.dumps({
        "date": date_str,
        "brand": brand,
        "tier": daily["tier"],
        "account": serialize(daily["account"]),
        "campaigns": serialize(daily["campaigns"]),
        "ads": serialize(daily["ads"]),
        "previous": serialize(daily["previous"]),
        "week": serialize(daily["week"]),
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    return txt, js


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--date", help="YYYY-MM-DD (기본: 어제)")
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--no-slack", action="store_true", help="Slack 발송 skip — 로컬 검증·CI dry-run 용")
    args = p.parse_args()

    target = (
        datetime.strptime(args.date, "%Y-%m-%d").date()
        if args.date else date.today() - timedelta(days=1)
    )
    env = load_env()
    require(env, ["META_APP_ID", "META_APP_SECRET", "META_ACCESS_TOKEN", "META_AD_ACCOUNT_ID"])
    thresholds = load_kpi(args.brand)

    print(f"▶ daily_slack — date={target} brand={args.brand} no_slack={args.no_slack}")
    client = MetaClient(env)
    daily = client.daily(target)
    print(f"  Meta fetched: account={len(daily['account'])} campaigns={len(daily['campaigns'])} ads={len(daily['ads'])} tier={daily['tier']}")

    ga4_block = None  # Phase 2 ETL 의 GA4 결과를 읽도록 후속 연결

    message = render(target, args.brand, daily, thresholds, ga4_block)
    txt, js = save(target.strftime("%Y-%m-%d"), args.brand, message, daily)
    print(f"  📄 저장: {txt.relative_to(ROOT.parent)} / {js.relative_to(ROOT.parent)}")

    slack = SlackClient(env.get("SLACK_WEBHOOK_URL"), dry_run=args.no_slack)
    ok = slack.send(message)
    print(f"  📤 Slack: {'✓ 발송' if ok and not slack.dry_run else 'dry-run skip' if slack.dry_run else '✗ 실패'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

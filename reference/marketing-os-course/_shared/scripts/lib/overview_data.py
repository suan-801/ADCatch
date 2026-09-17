"""Overview 통합 대시보드용 데이터 어댑터.

입력:
  - outputs/etl/etl_payload_{YYYY-MM-DD}_*.json (1일 1~N파일)
  - data/experiments.jsonl
  - outputs/recommendations/{brand}/*.json (피드백 누적용 — 있으면)

출력 (build() dict):
  - kpi_summary: 어제 KPI 5종 + delta + 7일 sparkline
  - kpi_achievement: 월간 페이싱 4종 + 신호등
  - channel_mix: ga4 channel 도넛 데이터
  - funnel_meta / funnel_ga4: 5단 + 드롭오프 %
  - creatives_top3: ad 레벨 ROAS Top 3 + 로컬 썸네일
  - trends_7d: roas/sessions/purchases sparkline + WoW delta
  - feedback_log: 지난 7일 recommendations dump
  - experiments: data/experiments.jsonl 파싱 + 분류

API 호출 ❌ — 모든 데이터는 디스크 캐시(ETL JSON)에서.
"""
from __future__ import annotations

import json
import re
import subprocess
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from lib.kpi_config import load as load_kpi, targets as load_targets, light

ROOT = Path(__file__).resolve().parents[2]
# Meta·GA4·Clarity 렌더 스크립트와 동일한 dump 위치를 읽어 데이터 정합성 보장
# (과거엔 _shared/outputs/etl 을 읽어 11_dashboard/etl 의 최신 dump 와 어긋났음)
ETL_DIR = ROOT.parent / "11_dashboard" / "etl"
# HTML 출력 위치(11_dashboard/dashboards/)의 상대경로 `../creatives/` 와 일치시킴
CREATIVES_DIR = ROOT.parent / "11_dashboard" / "creatives"
RECO_DIR = ROOT / "outputs" / "recommendations"
EXP_PATH = ROOT / "data" / "experiments.jsonl"

LOCAL_VIDEO_EXTS = [".mp4", ".mov", ".webm"]
LOCAL_IMAGE_EXTS = [".png", ".jpg", ".jpeg", ".webp", ".gif"]


def _latest_payload_for(d: date) -> Path | None:
    files = sorted(ETL_DIR.glob(f"etl_payload_{d.isoformat()}_*.json"), reverse=True)
    return files[0] if files else None


def load_payloads(target: date, days: int = 7) -> dict[date, dict]:
    """최근 days 일의 ETL JSON 을 날짜 → payload dict 로 반환. 없는 날은 skip."""
    out: dict[date, dict] = {}
    for i in range(days):
        d = target - timedelta(days=i)
        p = _latest_payload_for(d)
        if not p:
            continue
        try:
            out[d] = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
    return out


def _safe_float(v: Any, default: float = 0.0) -> float:
    if v is None or v == "":
        return default
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def _series_by_date(payloads: dict[date, dict], tab: str, value_key: str,
                    sort_asc: bool = True) -> list[tuple[date, float]]:
    """각 날짜의 1행(또는 합계)에서 value_key 추출. tab 이 daily 면 1행, 그 외엔 sum."""
    rows = []
    for d in sorted(payloads.keys()):
        items = payloads[d].get(tab) or []
        if not items:
            continue
        if tab.endswith("_daily") and tab in ("meta_daily", "ga4_daily", "ga4_funnel_daily"):
            v = _safe_float(items[0].get(value_key))
        else:
            v = sum(_safe_float(r.get(value_key)) for r in items)
        rows.append((d, v))
    return rows if sort_asc else list(reversed(rows))


def _spark(series: list[tuple[date, float]]) -> list[float]:
    return [v for _, v in series]


def _delta(series: list[float]) -> dict:
    """직전 동기간 대비 변화율. series 의 마지막 절반 vs 첫 절반."""
    if len(series) < 2:
        return {"pct": 0, "direction": "flat"}
    mid = len(series) // 2
    first = sum(series[:mid]) / max(mid, 1)
    last = sum(series[mid:]) / max(len(series) - mid, 1)
    if first == 0:
        return {"pct": 0, "direction": "flat"}
    pct = (last - first) / abs(first) * 100
    direction = "up" if pct > 1 else ("down" if pct < -1 else "flat")
    return {"pct": round(pct, 1), "direction": direction}


def _build_kpi_summary(payloads: dict[date, dict], target: date) -> dict:
    """KPI 카드 6종 (어제 기준): 지출 / 방문자 / 세션 / 장바구니(메타) / 구매(메타) / ROAS(메타).

    sparkline + delta + 절대값.
    """
    days = sorted(payloads.keys())
    if not days:
        return {}
    today_p = payloads[target] if target in payloads else payloads[days[-1]]

    meta = (today_p.get("meta_daily") or [{}])[0]
    ga = (today_p.get("ga4_daily") or [{}])[0]

    new_u = int(_safe_float(ga.get("new_users")))
    ret_u = int(_safe_float(ga.get("returning_users")))
    visitors = new_u + ret_u

    sessions_series = _spark(_series_by_date(payloads, "ga4_daily", "sessions"))
    visitors_series = [
        _safe_float((payloads[d].get("ga4_daily") or [{}])[0].get("new_users"))
        + _safe_float((payloads[d].get("ga4_daily") or [{}])[0].get("returning_users"))
        for d in sorted(payloads.keys())
    ]
    spend_series = _spark(_series_by_date(payloads, "meta_daily", "spend"))
    atc_series = _spark(_series_by_date(payloads, "meta_daily", "add_to_carts"))
    purchases_series = _spark(_series_by_date(payloads, "meta_daily", "purchases"))
    roas_series = _spark(_series_by_date(payloads, "meta_daily", "roas"))

    return {
        "spend": {
            "value": int(_safe_float(meta.get("spend"))),
            "delta": _delta(spend_series),
            "spark": spend_series,
            "emoji": "💸",
            "label": "지출",
            "story": _story_money(int(_safe_float(meta.get("spend"))), "썼어요"),
        },
        "visitors": {
            "value": visitors,
            "delta": _delta(visitors_series),
            "spark": visitors_series,
            "emoji": "👥",
            "label": "방문자",
            "story": (f"신규 {new_u:,}명 · 재방문 {ret_u:,}명"
                      if visitors else "방문자 데이터가 없어요"),
        },
        "sessions": {
            "value": int(_safe_float(ga.get("sessions"))),
            "delta": _delta(sessions_series),
            "spark": sessions_series,
            "emoji": "👣",
            "label": "세션",
            "story": _story_sessions(int(_safe_float(ga.get("sessions")))),
        },
        "atc": {
            "value": int(_safe_float(meta.get("add_to_carts"))),
            "delta": _delta(atc_series),
            "spark": atc_series,
            "emoji": "🛍️",
            "label": "장바구니 (메타)",
            "story": (f"{int(_safe_float(meta.get('add_to_carts'))):,}건 담겼어요"
                      if _safe_float(meta.get("add_to_carts")) else "—"),
        },
        "purchases": {
            "value": int(_safe_float(meta.get("purchases"))),
            "delta": _delta(purchases_series),
            "spark": purchases_series,
            "emoji": "🎉",
            "label": "구매 (메타)",
            "story": (f"{int(_safe_float(meta.get('purchases'))):,}건 결제됐어요"
                      if _safe_float(meta.get("purchases")) else "—"),
        },
        "roas": {
            "value": round(_safe_float(meta.get("roas")), 2),
            "delta": _delta(roas_series),
            "spark": roas_series,
            "emoji": "🎯",
            "label": "ROAS (메타)",
            "story": _story_roas(_safe_float(meta.get("roas"))),
        },
    }


def _story_sessions(n: int) -> str:
    if n == 0:
        return "어제는 방문이 없었어요"
    return f"어제 {n:,}명이 다녀갔어요"


def _story_new_users(new: int, returning: int) -> str:
    total = new + returning
    if total == 0:
        return "유저 데이터가 아직 없어요"
    pct = int(new / total * 100) if total else 0
    return f"신규 {new:,}명 · 재방문 {returning:,}명 (신규 {pct}%)"


def _story_money(amount: int, verb: str) -> str:
    if amount == 0:
        return "—"
    if amount >= 10000:
        return f"{amount/10000:.1f}만원 {verb}"
    return f"{amount:,}원 {verb}"


def _story_roas(roas: float) -> str:
    if roas == 0:
        return "데이터 없음"
    if roas >= 3:
        return f"ROAS {roas:.2f} — 잘 벌고 있어요 🎉"
    if roas >= 2:
        return f"ROAS {roas:.2f} — 안정적이에요"
    if roas >= 1:
        return f"ROAS {roas:.2f} — 본전 근처"
    return f"ROAS {roas:.2f} — 손해 중"


def _build_achievement(payloads: dict[date, dict], target: date, targets_cfg) -> dict:
    """월간 평균 4종 (Meta) — 오늘 기준 해당월 평균: ROAS / AOV / CTR / CPM.

    합계 기반 평균 (sum(metric)/sum(divisor)) — 일별 단순 평균보다 가중치 정확.
    """
    month_start = date(target.year, target.month, 1)
    days_in_month = monthrange(target.year, target.month)[1]
    days_into_month = (target - month_start).days + 1

    spend_mtd = 0.0
    revenue_mtd = 0.0
    purchases_mtd = 0.0
    impressions_mtd = 0.0
    clicks_mtd = 0.0
    for d, p in payloads.items():
        if d < month_start or d > target:
            continue
        m = (p.get("meta_daily") or [{}])[0]
        spend_mtd += _safe_float(m.get("spend"))
        revenue_mtd += _safe_float(m.get("purchase_value"))
        purchases_mtd += _safe_float(m.get("purchases"))
        impressions_mtd += _safe_float(m.get("impressions"))
        clicks_mtd += _safe_float(m.get("clicks"))

    avg_roas = (revenue_mtd / spend_mtd) if spend_mtd else 0.0
    avg_aov = (revenue_mtd / purchases_mtd) if purchases_mtd else 0.0
    avg_ctr = (clicks_mtd / impressions_mtd * 100) if impressions_mtd else 0.0
    avg_cpm = (spend_mtd / impressions_mtd * 1000) if impressions_mtd else 0.0

    target_roas = getattr(targets_cfg, "target_roas", 0) or 0
    roas_emoji = light(avg_roas, target_roas, target_roas * 0.7) if target_roas else "—"
    if target_roas:
        roas_hint = f"목표 ROAS {target_roas:.2f} {'도달! 🎉' if avg_roas >= target_roas else '미달'}"
    else:
        roas_hint = "목표 미설정"

    return {
        "month_start": month_start.isoformat(),
        "days_into_month": days_into_month,
        "days_in_month": days_in_month,
        "items": [
            {
                "key": "roas",
                "label": "ROAS",
                "emoji": "🎯",
                "value_str": f"{avg_roas:.2f}",
                "value": round(avg_roas, 2),
                "hint": roas_hint,
                "light": roas_emoji,
            },
            {
                "key": "aov",
                "label": "AOV (객단가)",
                "emoji": "🛍️",
                "value_str": (f"{int(avg_aov):,}원" if avg_aov else "—"),
                "value": int(avg_aov),
                "hint": (f"매출 {int(revenue_mtd):,}원 ÷ 구매 {int(purchases_mtd):,}건"
                         if purchases_mtd else "구매 데이터 없음"),
                "light": "—",
            },
            {
                "key": "ctr",
                "label": "CTR",
                "emoji": "👆",
                "value_str": f"{avg_ctr:.2f}%",
                "value": round(avg_ctr, 2),
                "hint": (f"클릭 {int(clicks_mtd):,} ÷ 노출 {int(impressions_mtd):,}"
                         if impressions_mtd else "노출 데이터 없음"),
                "light": "—",
            },
            {
                "key": "cpm",
                "label": "CPM",
                "emoji": "💸",
                "value_str": f"{int(avg_cpm):,}원",
                "value": int(avg_cpm),
                "hint": (f"지출 {int(spend_mtd):,}원 ÷ 노출 {int(impressions_mtd):,} × 1000"
                         if impressions_mtd else "노출 데이터 없음"),
                "light": "—",
            },
        ],
        "_revenue_mtd": revenue_mtd,
        "_purchases_mtd": purchases_mtd,
        "_spend_mtd": spend_mtd,
        "_impressions_mtd": impressions_mtd,
        "_clicks_mtd": clicks_mtd,
    }


def _build_channel_mix(target_payload: dict) -> dict:
    """ga4_channel_daily 에서 channel_group 별 sessions 합계."""
    rows = target_payload.get("ga4_channel_daily") or []
    groups: dict[str, dict] = {}
    for r in rows:
        cg = r.get("channel_group") or "Other"
        if cg not in groups:
            groups[cg] = {"sessions": 0, "conversions": 0, "revenue": 0}
        groups[cg]["sessions"] += _safe_float(r.get("sessions"))
        groups[cg]["conversions"] += _safe_float(r.get("conversions"))
        groups[cg]["revenue"] += _safe_float(r.get("revenue"))

    total = sum(g["sessions"] for g in groups.values())
    if total == 0:
        return {"items": [], "total": 0}

    PALETTE = {
        "Paid Social": "#d97757",
        "Organic Search": "#5b3d8a",
        "Direct": "#1a1410",
        "Referral": "#4a8fbe",
        "Organic Social": "#c8a464",
        "Email": "#2f7a2f",
        "Other": "#9ca3af",
    }
    items = []
    for cg, vals in sorted(groups.items(), key=lambda kv: kv[1]["sessions"], reverse=True):
        pct = vals["sessions"] / total * 100
        items.append({
            "label": cg,
            "sessions": int(vals["sessions"]),
            "conversions": int(vals["conversions"]),
            "revenue": int(vals["revenue"]),
            "pct": round(pct, 1),
            "color": PALETTE.get(cg, "#9ca3af"),
        })
    return {"items": items, "total": int(total)}


def _build_channel_combined(target_payload: dict, top_n: int = 12) -> list[dict]:
    """ga4_channel_daily 를 (channel_group, campaign) 으로 묶어 단일 TOP 리스트 반환.

    §3 "어디서 오셨나요" — 채널/캠페인을 한 표에 같이 보여줌 (탭 분리 ❌).
    """
    rows = target_payload.get("ga4_channel_daily") or []
    bucket: dict[tuple, dict] = {}
    PALETTE = {
        "Paid Social": "#d97757", "Organic Search": "#5b3d8a",
        "Direct": "#1a1410", "Referral": "#4a8fbe",
        "Organic Social": "#c8a464", "Email": "#2f7a2f",
        "Other": "#9ca3af", "Unassigned": "#9ca3af",
    }
    for r in rows:
        cg = r.get("channel_group") or "Other"
        cmp_ = (r.get("campaign") or "(none)").strip() or "(none)"
        key = (cg, cmp_)
        if key not in bucket:
            bucket[key] = {"sessions": 0.0, "conversions": 0.0, "revenue": 0.0}
        bucket[key]["sessions"] += _safe_float(r.get("sessions"))
        bucket[key]["conversions"] += _safe_float(r.get("conversions"))
        bucket[key]["revenue"] += _safe_float(r.get("revenue"))
    total = sum(b["sessions"] for b in bucket.values()) or 1
    items = []
    for (cg, cmp_), v in sorted(bucket.items(), key=lambda kv: kv[1]["sessions"], reverse=True)[:top_n]:
        items.append({
            "channel": cg,
            "campaign": cmp_,
            "color": PALETTE.get(cg, "#9ca3af"),
            "sessions": int(v["sessions"]),
            "conversions": int(v["conversions"]),
            "revenue": int(v["revenue"]),
            "pct": round(v["sessions"] / total * 100, 1),
        })
    return items


def _build_utm_breakdowns(payloads: dict[date, dict], target: date, days: int) -> dict:
    """기간 내 ga4_channel_daily 를 source / medium / campaign 기준으로 집계.

    Returns:
        {"source": [{"name", "sessions", "conversions", "revenue", "pct"}, ...],
         "medium": [...], "campaign": [...]}
    """
    window_start = target - timedelta(days=days - 1)

    def _agg(group_key: str, top_n: int = 10) -> list[dict]:
        bucket: dict[str, dict] = {}
        for d, p in payloads.items():
            if d < window_start or d > target:
                continue
            for r in (p.get("ga4_channel_daily") or []):
                key = (r.get(group_key) or "(none)").strip() or "(none)"
                if key not in bucket:
                    bucket[key] = {"sessions": 0.0, "conversions": 0.0, "revenue": 0.0}
                bucket[key]["sessions"] += _safe_float(r.get("sessions"))
                bucket[key]["conversions"] += _safe_float(r.get("conversions"))
                bucket[key]["revenue"] += _safe_float(r.get("revenue"))
        total = sum(b["sessions"] for b in bucket.values()) or 1
        items = []
        for name, vals in sorted(bucket.items(), key=lambda kv: kv[1]["sessions"], reverse=True)[:top_n]:
            items.append({
                "name": name,
                "sessions": int(vals["sessions"]),
                "conversions": int(vals["conversions"]),
                "revenue": int(vals["revenue"]),
                "pct": round(vals["sessions"] / total * 100, 1),
            })
        return items

    return {
        "source": _agg("source"),
        "medium": _agg("medium"),
        "campaign": _agg("campaign"),
    }


def _aggregate_period_kpi(payloads: dict[date, dict], target: date, days: int) -> dict:
    """기간 내 KPI 합계/평균 + 직전 동기간 비교."""
    window_start = target - timedelta(days=days - 1)
    prev_end = window_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)

    def _sum_window(start_d: date, end_d: date, tab: str, key: str) -> float:
        total = 0.0
        for d, p in payloads.items():
            if d < start_d or d > end_d:
                continue
            items = p.get(tab) or []
            if not items:
                continue
            if tab in ("meta_daily", "ga4_daily", "ga4_funnel_daily"):
                total += _safe_float(items[0].get(key))
            else:
                total += sum(_safe_float(r.get(key)) for r in items)
        return total

    sessions = int(_sum_window(window_start, target, "ga4_daily", "sessions"))
    new_users = int(_sum_window(window_start, target, "ga4_daily", "new_users"))
    returning = int(_sum_window(window_start, target, "ga4_daily", "returning_users"))
    spend = int(_sum_window(window_start, target, "meta_daily", "spend"))
    revenue = int(_sum_window(window_start, target, "meta_daily", "purchase_value"))
    purchases = int(_sum_window(window_start, target, "meta_daily", "purchases"))
    roas = (revenue / spend) if spend else 0.0

    p_sessions = _sum_window(prev_start, prev_end, "ga4_daily", "sessions")
    p_new_users = _sum_window(prev_start, prev_end, "ga4_daily", "new_users")
    p_spend = _sum_window(prev_start, prev_end, "meta_daily", "spend")
    p_revenue = _sum_window(prev_start, prev_end, "meta_daily", "purchase_value")
    p_roas = (p_revenue / p_spend) if p_spend else 0.0

    def _pct(curr, prev):
        if not prev:
            return {"pct": 0.0, "direction": "flat"}
        pct = (curr - prev) / abs(prev) * 100
        return {"pct": round(pct, 1), "direction": "up" if pct > 1 else ("down" if pct < -1 else "flat")}

    sparks_window_dates = sorted([d for d in payloads.keys() if window_start <= d <= target])
    spark_sessions = [_safe_float((payloads[d].get("ga4_daily") or [{}])[0].get("sessions")) for d in sparks_window_dates]
    spark_spend = [_safe_float((payloads[d].get("meta_daily") or [{}])[0].get("spend")) for d in sparks_window_dates]
    spark_revenue = [_safe_float((payloads[d].get("meta_daily") or [{}])[0].get("purchase_value")) for d in sparks_window_dates]
    spark_new_users = [_safe_float((payloads[d].get("ga4_daily") or [{}])[0].get("new_users")) for d in sparks_window_dates]
    spark_roas = [_safe_float((payloads[d].get("meta_daily") or [{}])[0].get("roas")) for d in sparks_window_dates]

    new_pct = int(new_users / (new_users + returning) * 100) if (new_users + returning) else 0

    return {
        "sessions": {"value": sessions, "delta": _pct(sessions, p_sessions), "spark": spark_sessions,
                     "emoji": "👣", "label": "세션",
                     "story": f"{sessions:,}명이 다녀갔어요" if sessions else "방문이 없었어요"},
        "new_users": {"value": new_users, "delta": _pct(new_users, p_new_users), "spark": spark_new_users,
                      "emoji": "✨", "label": "신규 유저",
                      "story": f"신규 {new_users:,}명 · 재방문 {returning:,}명 (신규 {new_pct}%)"},
        "spend": {"value": spend, "delta": _pct(spend, p_spend), "spark": spark_spend,
                  "emoji": "💸", "label": "지출",
                  "story": _story_money(spend, "썼어요")},
        "revenue": {"value": revenue, "delta": _pct(revenue, p_revenue), "spark": spark_revenue,
                    "emoji": "💰", "label": "매출",
                    "story": _story_money(revenue, "벌었어요")},
        "roas": {"value": round(roas, 2), "delta": _pct(roas, p_roas), "spark": spark_roas,
                 "emoji": "🎯", "label": "ROAS",
                 "story": _story_roas(roas)},
        "_purchases": purchases,
    }


def _aggregate_period_funnel(payloads: dict[date, dict], target: date, days: int) -> dict:
    """기간 내 퍼널 합계 (Meta + GA4)."""
    window_start = target - timedelta(days=days - 1)

    def _sum(tab: str, key: str) -> float:
        total = 0.0
        for d, p in payloads.items():
            if d < window_start or d > target:
                continue
            items = p.get(tab) or []
            if not items:
                continue
            total += _safe_float(items[0].get(key))
        return total

    def stage(label: str, emoji: str, value: float, prev: float | None) -> dict:
        drop = None
        if prev and prev > 0 and value > 0:
            drop = round((1 - value / prev) * 100, 1)
        return {"label": label, "emoji": emoji, "value": int(value), "drop_pct": drop}

    meta_impr = _sum("meta_daily", "impressions")
    meta_clicks = _sum("meta_daily", "clicks")
    meta_atc = _sum("meta_daily", "add_to_carts")
    meta_checkout = _sum("meta_daily", "checkouts")
    meta_purchases = _sum("meta_daily", "purchases")

    meta_line = [
        stage("노출", "👁️", meta_impr, None),
        stage("클릭", "👆", meta_clicks, meta_impr),
        stage("장바구니", "🛍️", meta_atc, meta_clicks),
        stage("결제 시작", "💳", meta_checkout, meta_atc),
        stage("구매", "🎉", meta_purchases, meta_checkout),
    ]

    ga_pv = _sum("ga4_funnel_daily", "page_view")
    ga_vi = _sum("ga4_funnel_daily", "view_item")
    ga_atc = _sum("ga4_funnel_daily", "add_to_cart")
    ga_vc = _sum("ga4_funnel_daily", "view_cart")
    ga_purchase = _sum("ga4_funnel_daily", "purchase_total") or _sum("ga4_daily", "conversions")

    ga_line = [
        stage("페이지뷰", "📄", ga_pv, None),
        stage("상품 조회", "🔎", ga_vi, ga_pv),
        stage("장바구니", "🛒", ga_atc, ga_vi),
        stage("결제 페이지", "🧾", ga_vc, ga_atc),
        stage("구매 완료", "✅", ga_purchase, ga_vc),
    ]

    story = ""
    if ga_pv > 0 and ga_purchase > 0:
        rate = ga_purchase / ga_pv * 1000
        story = f"1,000번 페이지를 봐서 {rate:.1f}건 구매로 이어졌어요"

    return {"meta": meta_line, "ga4": ga_line, "story": story}


def _slim_day(meta: dict, ga: dict, funnel: dict, channels: list[dict]) -> dict:
    """DAILY_DATA 한 날짜 entry 의 공통 셰이프 — Sheets·ETL 두 소스에서 재사용."""
    return {
        "meta": {k: _safe_float(meta.get(k)) for k in
                 ("spend", "purchase_value", "purchases", "impressions",
                  "clicks", "link_clicks", "landing_views",
                  "add_to_carts", "checkouts", "roas", "ctr", "cpm", "cpa")},
        "ga4": {k: _safe_float(ga.get(k)) for k in
                ("sessions", "new_users", "returning_users", "conversions")},
        "funnel": {k: _safe_float(funnel.get(k)) for k in
                   ("page_view", "view_item", "add_to_cart", "view_cart", "purchase_total")},
        "channels": [
            {"source": (r.get("source") or "(none)"),
             "medium": (r.get("medium") or "(none)"),
             "campaign": (r.get("campaign") or "(none)"),
             "channel_group": (r.get("channel_group") or "Other"),
             "sessions": _safe_float(r.get("sessions")),
             "conversions": _safe_float(r.get("conversions")),
             "revenue": _safe_float(r.get("revenue"))}
            for r in channels
        ],
    }


def _build_daily_data(payloads: dict[date, dict]) -> dict:
    """ETL JSON 디스크 캐시 → DAILY_DATA 슬림 dump."""
    out = {}
    for d, p in payloads.items():
        out[d.isoformat()] = _slim_day(
            (p.get("meta_daily") or [{}])[0],
            (p.get("ga4_daily") or [{}])[0],
            (p.get("ga4_funnel_daily") or [{}])[0],
            p.get("ga4_channel_daily") or [],
        )
    return out


def _load_daily_data_from_sheets(target: date, days: int = 30) -> dict:
    """Sheets 4탭 (meta_daily, ga4_daily, ga4_funnel_daily, ga4_channel_daily)
    에서 trend_start ~ target 범위 행을 날짜별로 묶어 DAILY_DATA 슬림 dump 로 반환.

    Sheets 미설정 / 에러 시 빈 dict — 호출부에서 ETL fallback.
    """
    try:
        from lib.env_loader import load_env
        from lib.sheet_client import open_sheet
    except Exception:
        return {}
    try:
        env = load_env()
    except Exception:
        return {}
    if not env.get("GOOGLE_SHEETS_ID"):
        return {}
    try:
        sh = open_sheet(env)
    except Exception:
        return {}

    iso_end = target.isoformat()
    iso_start = (target - timedelta(days=days - 1)).isoformat()

    def _read(tab: str) -> list[dict]:
        try:
            ws = sh.worksheet(tab)
        except Exception:
            return []
        all_values = ws.get_all_values()
        if not all_values:
            return []
        headers = all_values[0]
        rows = []
        for row in all_values[1:]:
            r = dict(zip(headers, row))
            if iso_start <= r.get("date", "") <= iso_end:
                rows.append(r)
        return rows

    meta_rows = _read("meta_daily")
    ga4_rows = _read("ga4_daily")
    funnel_rows = _read("ga4_funnel_daily")
    channel_rows = _read("ga4_channel_daily")

    by_date: dict[str, dict] = {}
    for r in meta_rows:
        d = r.get("date") or ""
        if d:
            by_date.setdefault(d, {"meta": {}, "ga": {}, "funnel": {}, "channels": []})["meta"] = r
    for r in ga4_rows:
        d = r.get("date") or ""
        if d:
            by_date.setdefault(d, {"meta": {}, "ga": {}, "funnel": {}, "channels": []})["ga"] = r
    for r in funnel_rows:
        d = r.get("date") or ""
        if d:
            by_date.setdefault(d, {"meta": {}, "ga": {}, "funnel": {}, "channels": []})["funnel"] = r
    for r in channel_rows:
        d = r.get("date") or ""
        if d:
            by_date.setdefault(d, {"meta": {}, "ga": {}, "funnel": {}, "channels": []})["channels"].append(r)

    out = {}
    for d, parts in by_date.items():
        out[d] = _slim_day(parts["meta"], parts["ga"], parts["funnel"], parts["channels"])
    return out


def _build_funnel(target_payload: dict) -> dict:
    """Meta 라인 + GA4 라인 2줄 퍼널."""
    meta = (target_payload.get("meta_daily") or [{}])[0]
    ga_funnel = (target_payload.get("ga4_funnel_daily") or [{}])[0]
    ga_daily = (target_payload.get("ga4_daily") or [{}])[0]

    def stage(label: str, emoji: str, value: float, prev: float | None) -> dict:
        drop = None
        if prev and prev > 0 and value > 0:
            drop = round((1 - value / prev) * 100, 1)
        return {"label": label, "emoji": emoji, "value": int(value), "drop_pct": drop}

    meta_impr = _safe_float(meta.get("impressions"))
    meta_clicks = _safe_float(meta.get("clicks"))
    meta_atc = _safe_float(meta.get("add_to_carts"))
    meta_checkout = _safe_float(meta.get("checkouts"))
    meta_purchases = _safe_float(meta.get("purchases"))

    meta_line = [
        stage("노출", "👁️", meta_impr, None),
        stage("클릭", "👆", meta_clicks, meta_impr),
        stage("장바구니", "🛍️", meta_atc, meta_clicks),
        stage("결제 시작", "💳", meta_checkout, meta_atc),
        stage("구매", "🎉", meta_purchases, meta_checkout),
    ]

    ga_pv = _safe_float(ga_funnel.get("page_view"))
    ga_vi = _safe_float(ga_funnel.get("view_item"))
    ga_atc = _safe_float(ga_funnel.get("add_to_cart"))
    ga_vc = _safe_float(ga_funnel.get("view_cart"))
    ga_purchase = _safe_float(ga_funnel.get("purchase_total")) or _safe_float(ga_daily.get("conversions"))

    ga_line = [
        stage("페이지뷰", "📄", ga_pv, None),
        stage("상품 조회", "🔎", ga_vi, ga_pv),
        stage("장바구니", "🛒", ga_atc, ga_vi),
        stage("결제 페이지", "🧾", ga_vc, ga_atc),
        stage("구매 완료", "✅", ga_purchase, ga_vc),
    ]

    # 친근 카피
    story = ""
    if ga_pv > 0 and ga_purchase > 0:
        rate = ga_purchase / ga_pv * 1000  # per 1000 pv
        story = f"1,000번 페이지를 봐서 {rate:.1f}건 구매로 이어졌어요"

    return {"meta": meta_line, "ga4": ga_line, "story": story}


def _extract_video_thumb(video_path: Path, thumb_path: Path) -> bool:
    """ffmpeg 로 영상 첫 프레임(0.5초 지점) 추출 → thumb_path 에 jpg 저장.

    fade-in 이 있는 영상이 검은 화면으로 잡히지 않도록 0.5초 시점 사용.
    영상이 0.5초 미만이면 0초 fallback. ffmpeg 미설치/실패 시 False.
    """
    thumb_path.parent.mkdir(parents=True, exist_ok=True)
    for ss in ("0.5", "0"):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error",
                 "-ss", ss, "-i", str(video_path),
                 "-vframes", "1", "-q:v", "3", str(thumb_path)],
                check=True, timeout=15,
            )
            if thumb_path.exists() and thumb_path.stat().st_size > 0:
                return True
        except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
            continue
    return False


def _scan_creatives() -> dict[str, str]:
    """outputs/creatives/{stem}.{ext} 스캔 → {stem: relative_path}.

    이미지: 그대로 반환.
    영상: ffmpeg 로 첫 프레임을 `_thumbs/{stem}.jpg` 에 캐싱한 후 jpg 경로 반환.
    추출 실패 시 영상 경로 그대로 반환 (템플릿이 placeholder 표시).
    """
    if not CREATIVES_DIR.exists():
        return {}
    thumbs_dir = CREATIVES_DIR / "_thumbs"
    found: dict[str, dict] = {}
    for f in CREATIVES_DIR.iterdir():
        if not f.is_file() or f.name.startswith("."):
            continue
        ext = f.suffix.lower()
        if ext not in LOCAL_VIDEO_EXTS + LOCAL_IMAGE_EXTS:
            continue
        stem = f.stem
        found.setdefault(stem, {})[ext] = f.name
    out = {}
    for stem, exts in found.items():
        # 1) 이미지가 있으면 그대로 (HTML 은 outputs/dashboards/ 에 떨어지므로 ../ 로 한 단계 올라감)
        img_picked = next((exts[e] for e in LOCAL_IMAGE_EXTS if e in exts), None)
        if img_picked:
            out[stem] = f"../creatives/{img_picked}"
            continue
        # 2) 영상만 있으면 첫 프레임 추출 시도
        vid_picked = next((exts[e] for e in LOCAL_VIDEO_EXTS if e in exts), None)
        if not vid_picked:
            continue
        thumb_path = thumbs_dir / f"{stem}.jpg"
        if not thumb_path.exists():
            _extract_video_thumb(CREATIVES_DIR / vid_picked, thumb_path)
        if thumb_path.exists() and thumb_path.stat().st_size > 0:
            out[stem] = f"../creatives/_thumbs/{stem}.jpg"
        else:
            out[stem] = f"../creatives/{vid_picked}"
    return out


def _norm_creative_key(name: str) -> str:
    """meta008_260327_hj_FP → meta008_260327_hj 매칭용 정규화."""
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


def _build_creatives_top3(target_payload: dict, thresholds) -> list[dict]:
    """meta_breakdowns level=ad ROAS Top 3 + 로컬 썸네일."""
    rows = [r for r in (target_payload.get("meta_breakdowns") or [])
            if r.get("level") == "ad" and _safe_float(r.get("spend")) >= thresholds.spend_min]
    rows.sort(key=lambda r: _safe_float(r.get("roas")), reverse=True)
    top = rows[:3]
    creatives = _scan_creatives()
    norm_creatives = {_norm_creative_key(k): v for k, v in creatives.items()}
    # 로컬 파일이 없을 때 폴백 — Meta 크리에이티브 썸네일 URL (ad_id 매칭)
    cre_by_id = {str(c.get("ad_id")): c for c in (target_payload.get("meta_creatives") or [])}

    MEDALS = ["🥇", "🥈", "🥉"]
    out = []
    for i, r in enumerate(top):
        ad_name = r.get("ad_name", "")
        ad_id = str(r.get("id") or "")
        key = _norm_creative_key(ad_name)
        thumb = creatives.get(ad_name) or norm_creatives.get(key)
        is_video = bool((thumb or "").lower().endswith(tuple(LOCAL_VIDEO_EXTS)))
        if not thumb:
            mc = cre_by_id.get(ad_id)
            if mc:
                # Meta CDN 썸네일/이미지 URL — 썸네일은 jpg 라 <img> 로 렌더 (동영상이어도 포스터 프레임)
                thumb = (mc.get("image_url") or mc.get("thumbnail_url")) or None
                if thumb:
                    is_video = False
        spend = int(_safe_float(r.get("spend")))
        purchases = int(_safe_float(r.get("purchases")))
        revenue = _safe_float(r.get("purchase_value"))
        impressions = _safe_float(r.get("impressions"))
        clicks = int(_safe_float(r.get("clicks")))
        landing_views = int(_safe_float(r.get("landing_views")))
        ctr = _safe_float(r.get("ctr"))
        if not ctr and impressions:
            ctr = clicks / impressions * 100
        cpm = _safe_float(r.get("cpm"))
        if not cpm and impressions:
            cpm = spend / impressions * 1000
        aov = (revenue / purchases) if purchases else 0
        out.append({
            "medal": MEDALS[i] if i < 3 else "•",
            "ad_name": ad_name,
            "campaign": r.get("campaign_name", ""),
            "roas": round(_safe_float(r.get("roas")), 2),
            "spend": spend,
            "cpm": int(cpm),
            "clicks": clicks,
            "landing_views": landing_views,
            "ctr": round(ctr, 2),
            "purchases": purchases,
            "cpa": int(_safe_float(r.get("cpa"))),
            "aov": int(aov),
            "thumb": thumb,
            "is_video": is_video,
        })
    return out


def _build_trends_7d(payloads: dict[date, dict]) -> dict:
    """ROAS · 세션 · 구매 3개 sparkline + WoW delta."""
    roas_s = _series_by_date(payloads, "meta_daily", "roas")
    sess_s = _series_by_date(payloads, "ga4_daily", "sessions")
    purch_s = _series_by_date(payloads, "meta_daily", "purchases")

    def to_card(series, label, emoji, fmt: str):
        values = _spark(series)
        d = _delta(values)
        if values:
            latest = values[-1]
        else:
            latest = 0
        return {
            "label": label,
            "emoji": emoji,
            "spark": values,
            "dates": [str(s[0]) for s in series],
            "latest": fmt.format(latest),
            "delta_pct": d["pct"],
            "direction": d["direction"],
            "caption": _trend_caption(d, label),
        }

    return {
        "roas": to_card(roas_s, "ROAS", "🎯", "{:.2f}"),
        "sessions": to_card(sess_s, "세션", "👣", "{:.0f}"),
        "purchases": to_card(purch_s, "구매", "🛒", "{:.0f}"),
    }


def _trend_caption(d: dict, label: str) -> str:
    pct = d["pct"]
    direction = d["direction"]
    if direction == "up":
        return f"이번 주 {label} ↑ {pct:+.1f}%"
    if direction == "down":
        return f"이번 주 {label} ↓ {pct:+.1f}%"
    return f"이번 주 {label} 보합"


def _load_feedback_log(brand: str, target: date, days: int = 7) -> list[dict]:
    """outputs/recommendations/{brand}/{YYYY-MM-DD}.json 누적 (지난 days 일)."""
    folder = RECO_DIR / brand
    if not folder.exists():
        return []
    out = []
    for i in range(1, days + 1):
        d = target - timedelta(days=i)
        p = folder / f"{d.isoformat()}.json"
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            for r in data.get("recommendations", []):
                r["_date"] = d.isoformat()
                out.append(r)
        except json.JSONDecodeError:
            continue
    return out


def _load_experiments(brand: str) -> dict:
    """data/experiments.jsonl 파싱 + 상태별 분류."""
    if not EXP_PATH.exists():
        return {"running": [], "planned": [], "done": [], "trophies": [],
                "timeline_start": "", "timeline_end": "", "total": 0}
    items = []
    for line in EXP_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if r.get("brand") != brand:
            continue
        items.append(r)

    running = [r for r in items if r.get("status") == "running"]
    planned = [r for r in items if r.get("status") == "planned"]
    done = [r for r in items if r.get("status") == "done"]
    trophies = sorted(
        [r for r in done if r.get("result") == "win" and r.get("adopted")],
        key=lambda r: r.get("ended_at", ""), reverse=True,
    )[:5]

    # Gantt-lite 용 날짜 범위
    all_dates = [r.get("started_at") for r in items if r.get("started_at")] + \
                [r.get("ended_at") for r in items if r.get("ended_at")]
    timeline_start = min(all_dates) if all_dates else ""
    timeline_end = max(all_dates) if all_dates else ""

    return {
        "running": running,
        "planned": planned,
        "done": done,
        "trophies": trophies,
        "timeline_start": timeline_start,
        "timeline_end": timeline_end,
        "total": len(items),
    }


def build(brand: str, target: date, range_days: int = 7) -> dict:
    """Overview 대시보드의 모든 데이터를 한 번에 빌드."""
    from lib import recommendations as reco_mod

    payloads = load_payloads(target, days=max(range_days, 7))
    # 데이터가 아예 없으면 fallback — 최근 30일 중 가장 최신
    if not payloads:
        any_payloads = load_payloads(target, days=30)
        if any_payloads:
            target = max(any_payloads.keys())
            payloads = any_payloads
    if target not in payloads and payloads:
        target = max(payloads.keys())

    target_payload = payloads.get(target) or {}
    thresholds = load_kpi(brand)
    targets_cfg = load_targets(brand)

    kpi_summary = _build_kpi_summary(payloads, target)
    achievement = _build_achievement(payloads, target, targets_cfg)
    channel_mix = _build_channel_mix(target_payload)
    channel_combined = _build_channel_combined(target_payload)
    funnel = _build_funnel(target_payload)
    creatives_top3 = _build_creatives_top3(target_payload, thresholds)
    trends_7d = _build_trends_7d(payloads)
    # Sheets 가 우선 — 30일 풀 커버리지. ETL JSON 은 Sheets 에 없는 날짜만 보충.
    daily_data = _build_daily_data(payloads)
    sheets_daily = _load_daily_data_from_sheets(target, days=max(range_days, 30))
    if sheets_daily:
        # Sheets 에 있는 날짜는 Sheets 값으로 덮어씀 (운영 데이터 우선)
        daily_data = {**daily_data, **sheets_daily}

    # 룰엔진 호출
    meta_daily_series = [(payloads[d].get("meta_daily") or [{}])[0] for d in sorted(payloads.keys())]
    ga4_daily_series = [(payloads[d].get("ga4_daily") or [{}])[0] for d in sorted(payloads.keys())]
    ga4_channel_target = target_payload.get("ga4_channel_daily") or []
    meta_breakdowns_target = target_payload.get("meta_breakdowns") or []
    clarity_series = []  # ETL JSON 에는 clarity 미포함 — 향후 추가 시 연결

    recs = reco_mod.run(
        meta_daily=meta_daily_series,
        ga4_daily=ga4_daily_series,
        ga4_channel=ga4_channel_target,
        meta_breakdowns=meta_breakdowns_target,
        clarity_daily=clarity_series,
        thresholds=thresholds,
        targets=targets_cfg,
        target_date=target,
        revenue_mtd=achievement["_revenue_mtd"],
        purchases_mtd=achievement["_purchases_mtd"],
        days_into_month=achievement["days_into_month"],
        days_in_month=achievement["days_in_month"],
    )
    recs_json = reco_mod.to_jsonable(recs)

    # 디스크에 dump (피드백 루프 누적용)
    folder = RECO_DIR / brand
    folder.mkdir(parents=True, exist_ok=True)
    (folder / f"{target.isoformat()}.json").write_text(
        json.dumps({"date": target.isoformat(), "recommendations": recs_json},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    feedback_log = _load_feedback_log(brand, target, days=7)
    experiments = _load_experiments(brand)

    # freshness
    meta_freshness = (target_payload.get("meta_daily") or [{}])[0].get("freshness", "t3_meta")
    ga4_freshness = (target_payload.get("ga4_daily") or [{}])[0].get("freshness", "t2_ga4")

    return {
        "brand": brand,
        "target": target.isoformat(),
        "range_days": range_days,
        "payloads_loaded": len(payloads),
        "kpi_summary": kpi_summary,
        "achievement": achievement,
        "channel_mix": channel_mix,
        "channel_combined": channel_combined,
        "funnel": funnel,
        "creatives_top3": creatives_top3,
        "trends_7d": trends_7d,
        "daily_data": daily_data,
        "recommendations": recs_json,
        "feedback_log": feedback_log,
        "experiments": experiments,
        "meta_freshness": meta_freshness,
        "ga4_freshness": ga4_freshness,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

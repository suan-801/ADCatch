"""GA4 Data API 클라이언트 — 4-4 ingest_ga4 패턴 + service account 전용.

env 키:
- GA4_PROPERTY_ID (필수)
- GA4_SERVICE_ACCOUNT_PATH 또는 GA4_SERVICE_ACCOUNT_JSON

ROAS·매출 ❌ — utm 유입·신규/재방문·전환만 본다 (메모리 룰 feedback_roas_methodology).
"""
from __future__ import annotations

import json
from datetime import date

# Cafe24 + 네이버페이 분리 이벤트 보정: 표준 `purchase` + 네이버페이 클릭 이벤트
# `click_npay_purchase` 는 네이버 도메인 리다이렉트로 완료 콜백이 안 돌아와서
# GA4 표준 `purchase` 이벤트가 아닌 클릭 시점 이벤트로 잡힘.
PURCHASE_EVENT_NAMES = ("purchase", "click_npay_purchase")

# 퍼널 단계별 GA4 표준 이벤트명 (default). cafe24/GTM 가 표준명을 안 쏘면
# `GA4_*_ALIASES` 환경변수에 콤마구분으로 실제 이벤트명을 추가 → 합산.
# 예: GA4_ADDTOCART_ALIASES="addToCart,cart_add,ec_addToCart"
DEFAULT_PAGE_VIEW_EVENTS = ("page_view",)
DEFAULT_VIEW_ITEM_EVENTS = ("view_item",)
DEFAULT_ADD_TO_CART_EVENTS = ("add_to_cart",)
DEFAULT_VIEW_CART_EVENTS = ("view_cart",)


def _env_event_aliases(env: dict[str, str], key: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
    """env[key] 콤마 구분 alias 추가. 표준명은 항상 포함, 중복 제거."""
    raw = (env or {}).get(key, "").strip() if env else ""
    extras = tuple(x.strip() for x in raw.split(",") if x.strip()) if raw else ()
    seen: set = set()
    out: list[str] = []
    for n in tuple(defaults) + extras:
        if n not in seen:
            out.append(n)
            seen.add(n)
    return tuple(out)


def _resolve_funnel_stages(env: dict[str, str]) -> list[tuple[str, tuple[str, ...]]]:
    """런타임 env 기반 퍼널 단계 — alias 합산."""
    return [
        ("page_view", _env_event_aliases(env, "GA4_PAGEVIEW_ALIASES", DEFAULT_PAGE_VIEW_EVENTS)),
        ("view_item", _env_event_aliases(env, "GA4_VIEWITEM_ALIASES", DEFAULT_VIEW_ITEM_EVENTS)),
        ("add_to_cart", _env_event_aliases(env, "GA4_ADDTOCART_ALIASES", DEFAULT_ADD_TO_CART_EVENTS)),
        ("view_cart", _env_event_aliases(env, "GA4_VIEWCART_ALIASES", DEFAULT_VIEW_CART_EVENTS)),
        ("purchase_total", PURCHASE_EVENT_NAMES),
    ]


def _credentials(env: dict[str, str]):
    from google.oauth2.service_account import Credentials
    sa_path = env.get("GA4_SERVICE_ACCOUNT_PATH") or env.get("GOOGLE_APPLICATION_CREDENTIALS")
    sa_json = env.get("GA4_SERVICE_ACCOUNT_JSON")
    scopes = ["https://www.googleapis.com/auth/analytics.readonly"]
    if sa_path:
        return Credentials.from_service_account_file(sa_path, scopes=scopes)
    if sa_json:
        return Credentials.from_service_account_info(json.loads(sa_json), scopes=scopes)
    # 로컬 dev fallback — gcloud OAuth ADC (analytics-mcp 와 동일 경로)
    try:
        from google.auth import default as google_auth_default
        creds, _ = google_auth_default(scopes=scopes)
        return creds
    except Exception as e:
        raise RuntimeError(
            "GA4 인증 미설정 — GA4_SERVICE_ACCOUNT_PATH/_JSON 또는 gcloud ADC 필요"
        ) from e


def freshness_tier(target: date, today: date) -> str:
    return "t1_preview" if (today - target).days <= 1 else "t2_stable"


def _purchase_event_filter():
    from google.analytics.data_v1beta.types import Filter, FilterExpression
    return FilterExpression(filter=Filter(
        field_name="eventName",
        in_list_filter=Filter.InListFilter(values=list(PURCHASE_EVENT_NAMES)),
    ))


def _purchase_count(client, prop: str, start: str, end: str, extra_filter=None) -> int:
    from google.analytics.data_v1beta.types import (
        DateRange, FilterExpression, FilterExpressionList, Metric, RunReportRequest,
    )
    event_filter = _purchase_event_filter()
    if extra_filter is not None:
        dim_filter = FilterExpression(and_group=FilterExpressionList(
            expressions=[event_filter, extra_filter],
        ))
    else:
        dim_filter = event_filter
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        metrics=[Metric(name="eventCount")],
        dimension_filter=dim_filter,
    )
    resp = client.run_report(req)
    if not resp.rows:
        return 0
    return int(float(resp.rows[0].metric_values[0].value))


def _purchase_breakdown(client, prop: str, start: str, end: str, dim_names, extra_filter=None) -> dict:
    """dim 조합별 purchase 카운트·매출. purchase + click_npay_purchase 합산."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, FilterExpression, FilterExpressionList, Metric, RunReportRequest,
    )
    event_filter = _purchase_event_filter()
    if extra_filter is not None:
        dim_filter = FilterExpression(and_group=FilterExpressionList(
            expressions=[event_filter, extra_filter],
        ))
    else:
        dim_filter = event_filter
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name=d) for d in dim_names],
        metrics=[Metric(name="eventCount"), Metric(name="purchaseRevenue")],
        dimension_filter=dim_filter,
    )
    resp = client.run_report(req)
    out: dict = {}
    for r in resp.rows or []:
        key = tuple(v.value for v in r.dimension_values)
        cnt = int(float(r.metric_values[0].value))
        rev = float(r.metric_values[1].value)
        # 동일 키가 purchase/click_npay_purchase 양쪽에서 들어와도 합산되지만,
        # 차원에 eventName 이 없으므로 키는 차원조합만으로 유일 → cnt 가 이미 합산값.
        prev = out.get(key, {"count": 0, "revenue": 0.0})
        out[key] = {"count": prev["count"] + cnt, "revenue": prev["revenue"] + rev}
    return out


def daily_summary(env: dict[str, str], target: date) -> dict:
    """ga4_daily 한 행을 만든다."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = BetaAnalyticsDataClient(credentials=_credentials(env))
    date_str = target.strftime("%Y-%m-%d")

    # 1) 합계 — sessions, users, newUsers, activeUsers, averageSessionDuration
    s_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
        metrics=[
            Metric(name="sessions"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="activeUsers"),
            Metric(name="averageSessionDuration"),
        ],
    )
    s_resp = client.run_report(s_req)
    if s_resp.rows:
        v = [m.value for m in s_resp.rows[0].metric_values]
        sessions = int(float(v[0])); users = int(float(v[1]))
        new_users = int(float(v[2]))
        active_users = int(float(v[3]))
        avg_session_duration = round(float(v[4]), 2)
    else:
        sessions = users = new_users = active_users = 0
        avg_session_duration = 0.0
    returning = max(users - new_users, 0)

    # 1-2) 구매 이벤트 — purchase + click_npay_purchase 합산
    conversions = _purchase_count(client, prop, date_str, date_str)
    conv_rate = (conversions / sessions * 100) if sessions else 0.0

    # 2) 채널 TOP 1
    t_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=date_str, end_date=date_str)],
        dimensions=[Dimension(name="sessionSource"), Dimension(name="sessionMedium"), Dimension(name="sessionCampaignName")],
        metrics=[Metric(name="sessions")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=1,
    )
    t_resp = client.run_report(t_req)
    if t_resp.rows:
        top_source = t_resp.rows[0].dimension_values[0].value
        top_medium = t_resp.rows[0].dimension_values[1].value
        top_campaign = t_resp.rows[0].dimension_values[2].value
    else:
        top_source = top_medium = top_campaign = ""

    return {
        "date": date_str,
        "sessions": sessions,
        "users": users,
        "new_users": new_users,
        "returning_users": returning,
        "active_users": active_users,
        "avg_session_duration": avg_session_duration,
        "conversions": conversions,
        "conversion_rate": round(conv_rate, 2),
        "top_source": top_source,
        "top_medium": top_medium,
        "top_campaign": top_campaign,
        "freshness": freshness_tier(target, date.today()),
        "updated_at": date.today().isoformat(),
    }


def paid_social_utm_top(env: dict[str, str], since: date, until: date, limit: int = 5) -> list[dict]:
    """sessionMedium=paid_social 의 utm_content TOP — daily-slack GA4 블록용."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, FilterExpressionList,
        Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = BetaAnalyticsDataClient(credentials=_credentials(env))
    start, end = since.isoformat(), until.isoformat()
    paid_social_filter = FilterExpression(filter=Filter(
        field_name="sessionMedium",
        string_filter=Filter.StringFilter(value="paid_social"),
    ))

    # 1) sessions + users — utm_content × campaign 단위
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionManualAdContent"), Dimension(name="sessionCampaignName")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        dimension_filter=paid_social_filter,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(req)
    rows = []
    for r in resp.rows or []:
        rows.append({
            "utm_content": r.dimension_values[0].value,
            "campaign": r.dimension_values[1].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
            "conversions": 0,
        })

    # 2) 구매 이벤트 — utm_content × campaign 별 합산 (purchase + click_npay_purchase)
    conv_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=start, end_date=end)],
        dimensions=[Dimension(name="sessionManualAdContent"), Dimension(name="sessionCampaignName")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=FilterExpression(and_group=FilterExpressionList(expressions=[
            paid_social_filter,
            _purchase_event_filter(),
        ])),
    )
    conv_resp = client.run_report(conv_req)
    conv_lookup = {
        (r.dimension_values[0].value, r.dimension_values[1].value): int(float(r.metric_values[0].value))
        for r in (conv_resp.rows or [])
    }
    for row in rows:
        row["conversions"] = conv_lookup.get((row["utm_content"], row["campaign"]), 0)
    return rows


# ── 확장 빌더 (v2) — 6탭 분해 적재 ──────────────────────────────────────────

def _bav_client(env: dict[str, str]):
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    return BetaAnalyticsDataClient(credentials=_credentials(env))


def channel_rows(env: dict[str, str], target: date, limit: int = 15) -> list[dict]:
    """채널그룹 × source × medium × campaign 분해. TOP {limit}."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    dim_names = ["sessionDefaultChannelGroup", "sessionSource", "sessionMedium", "sessionCampaignName"]
    traffic_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name=d) for d in dim_names],
        metrics=[
            Metric(name="sessions"),
            Metric(name="newUsers"),
            Metric(name="engagedSessions"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(traffic_req)
    rows: list[dict] = []
    for r in resp.rows or []:
        rows.append({
            "date": s,
            "channel_group": r.dimension_values[0].value,
            "source": r.dimension_values[1].value,
            "medium": r.dimension_values[2].value,
            "campaign": r.dimension_values[3].value,
            "sessions": int(float(r.metric_values[0].value)),
            "new_users": int(float(r.metric_values[1].value)),
            "engaged_sessions": int(float(r.metric_values[2].value)),
            "conversions": 0,
            "revenue": 0.0,
            "freshness": tier,
            "updated_at": now,
        })
    breakdown = _purchase_breakdown(client, prop, s, s, dim_names)
    for row in rows:
        key = (row["channel_group"], row["source"], row["medium"], row["campaign"])
        m = breakdown.get(key)
        if m:
            row["conversions"] = m["count"]
            row["revenue"] = round(m["revenue"], 2)
    return rows


def device_rows(env: dict[str, str], target: date) -> list[dict]:
    """deviceCategory 별 1일 합계."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    traffic_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name="deviceCategory")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
    )
    resp = client.run_report(traffic_req)
    rows: list[dict] = []
    for r in resp.rows or []:
        sessions = int(float(r.metric_values[0].value))
        rows.append({
            "date": s,
            "device_category": r.dimension_values[0].value,
            "sessions": sessions,
            "users": int(float(r.metric_values[1].value)),
            "conversions": 0,
            "cvr": 0.0,
            "revenue": 0.0,
            "freshness": tier,
            "updated_at": now,
        })
    breakdown = _purchase_breakdown(client, prop, s, s, ["deviceCategory"])
    for row in rows:
        m = breakdown.get((row["device_category"],))
        if m:
            row["conversions"] = m["count"]
            row["revenue"] = round(m["revenue"], 2)
        row["cvr"] = round((row["conversions"] / row["sessions"] * 100), 2) if row["sessions"] else 0.0
    return rows


def landing_rows(env: dict[str, str], target: date, limit: int = 20) -> list[dict]:
    """랜딩페이지 TOP {limit} (세션 기준)."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    traffic_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name="landingPagePlusQueryString")],
        metrics=[
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="bounceRate"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(traffic_req)
    rows: list[dict] = []
    for r in resp.rows or []:
        rows.append({
            "date": s,
            "landing_path": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "engaged_sessions": int(float(r.metric_values[1].value)),
            "bounce_rate": round(float(r.metric_values[2].value), 4),
            "conversions": 0,
            "revenue": 0.0,
            "freshness": tier,
            "updated_at": now,
        })
    breakdown = _purchase_breakdown(client, prop, s, s, ["landingPagePlusQueryString"])
    for row in rows:
        m = breakdown.get((row["landing_path"],))
        if m:
            row["conversions"] = m["count"]
            row["revenue"] = round(m["revenue"], 2)
    return rows


def product_rows(env: dict[str, str], target: date, limit: int = 20) -> list[dict]:
    """상품(item) 단위 — view → ATC → purchase + 매출. itemScope metric 사용."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name="itemName"), Dimension(name="itemId")],
        metrics=[
            Metric(name="itemsViewed"),
            Metric(name="itemsAddedToCart"),
            Metric(name="itemsPurchased"),
            Metric(name="itemRevenue"),
        ],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="itemsViewed"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(req)
    rows: list[dict] = []
    for r in resp.rows or []:
        views = int(float(r.metric_values[0].value))
        atcs = int(float(r.metric_values[1].value))
        purchases = int(float(r.metric_values[2].value))
        rev = float(r.metric_values[3].value)
        rows.append({
            "date": s,
            "item_name": r.dimension_values[0].value,
            "item_id": r.dimension_values[1].value,
            "item_views": views,
            "add_to_carts": atcs,
            "purchases": purchases,
            "revenue": round(rev, 2),
            "view_to_atc": round((atcs / views * 100), 2) if views else 0.0,
            "atc_to_purchase": round((purchases / atcs * 100), 2) if atcs else 0.0,
            "freshness": tier,
            "updated_at": now,
        })
    return rows


def funnel_row(env: dict[str, str], target: date) -> dict:
    """퍼널 5단계 카운트 + 단계 전환율. eventName 별 eventCount.

    각 단계 이벤트명은 `_resolve_funnel_stages(env)` 로 런타임 결정 → cafe24 가
    표준 GA4 이벤트명을 안 쏘는 경우 `GA4_ADDTOCART_ALIASES` 등 env 로 alias 추가.
    """
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Filter, FilterExpression, Metric, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    stages = _resolve_funnel_stages(env)
    all_events = []
    for _, names in stages:
        all_events.extend(names)
    req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name="eventName")],
        metrics=[Metric(name="eventCount")],
        dimension_filter=FilterExpression(filter=Filter(
            field_name="eventName",
            in_list_filter=Filter.InListFilter(values=list(set(all_events))),
        )),
    )
    resp = client.run_report(req)
    raw: dict[str, int] = {}
    for r in resp.rows or []:
        raw[r.dimension_values[0].value] = int(float(r.metric_values[0].value))

    stage_counts: dict[str, int] = {}
    for label, names in stages:
        stage_counts[label] = sum(raw.get(n, 0) for n in names)

    def pct(num: int, den: int) -> float:
        return round((num / den * 100), 2) if den else 0.0

    return {
        "date": s,
        "page_view": stage_counts["page_view"],
        "view_item": stage_counts["view_item"],
        "add_to_cart": stage_counts["add_to_cart"],
        "view_cart": stage_counts["view_cart"],
        "purchase_total": stage_counts["purchase_total"],
        "view_to_pdp": pct(stage_counts["view_item"], stage_counts["page_view"]),
        "pdp_to_atc": pct(stage_counts["add_to_cart"], stage_counts["view_item"]),
        "atc_to_cart": pct(stage_counts["view_cart"], stage_counts["add_to_cart"]),
        "cart_to_purchase": pct(stage_counts["purchase_total"], stage_counts["view_cart"]),
        "overall_cvr": pct(stage_counts["purchase_total"], stage_counts["view_item"]),
        "freshness": tier,
        "updated_at": now,
    }


def geo_rows(env: dict[str, str], target: date, limit: int = 15) -> list[dict]:
    """지역(region = 시/도) 별 1일 합계 TOP {limit}."""
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    traffic_req = RunReportRequest(
        property=f"properties/{prop}",
        date_ranges=[DateRange(start_date=s, end_date=s)],
        dimensions=[Dimension(name="region")],
        metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        limit=limit,
    )
    resp = client.run_report(traffic_req)
    rows: list[dict] = []
    for r in resp.rows or []:
        rows.append({
            "date": s,
            "region": r.dimension_values[0].value or "(not set)",
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
            "conversions": 0,
            "revenue": 0.0,
            "freshness": tier,
            "updated_at": now,
        })
    breakdown = _purchase_breakdown(client, prop, s, s, ["region"])
    for row in rows:
        m = breakdown.get((row["region"],))
        if m:
            row["conversions"] = m["count"]
            row["revenue"] = round(m["revenue"], 2)
    return rows


def demo_rows(env: dict[str, str], target: date) -> list[dict]:
    """인구통계 — `userGender`, `userAgeBracket` 을 **각각 단일 차원**으로 쿼리.

    이전: `userAgeBracket × userGender` 교차 쿼리 → cardinality 폭증으로 GA4
    thresholds 가 강하게 걸려 대부분 `(other)` 로 떨어짐 (Looker 가 잘 잡히는 이유와
    동일한 원인). 차원 분리로 thresholds 표면적 최소화.

    스키마는 그대로 유지 (date, age_bracket, gender, sessions, users, conversions,
    revenue, thresholds_applied, freshness, updated_at). 한 행은 둘 중 한 차원만
    값이 있고 나머지는 빈 문자열. 대시보드 JS 는 빈 차원 행을 필터 후 집계.
    """
    from google.analytics.data_v1beta.types import (
        DateRange, Dimension, Metric, OrderBy, RunReportRequest,
    )
    prop = env["GA4_PROPERTY_ID"]
    client = _bav_client(env)
    s = target.strftime("%Y-%m-%d")
    tier = freshness_tier(target, date.today())
    now = date.today().isoformat()

    def _single_dim(dim_name: str):
        req = RunReportRequest(
            property=f"properties/{prop}",
            date_ranges=[DateRange(start_date=s, end_date=s)],
            dimensions=[Dimension(name=dim_name)],
            metrics=[Metric(name="sessions"), Metric(name="totalUsers")],
            order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="sessions"), desc=True)],
        )
        resp = client.run_report(req)
        thresholded = bool(getattr(resp.metadata, "subject_to_thresholding", False))
        return resp, thresholded

    g_resp, g_thr = _single_dim("userGender")
    a_resp, a_thr = _single_dim("userAgeBracket")
    thresholded = g_thr or a_thr

    rows: list[dict] = []
    for r in g_resp.rows or []:
        rows.append({
            "date": s,
            "age_bracket": "",
            "gender": r.dimension_values[0].value,
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
            "conversions": 0,
            "revenue": 0.0,
            "thresholds_applied": "true" if thresholded else "false",
            "freshness": tier,
            "updated_at": now,
        })
    for r in a_resp.rows or []:
        rows.append({
            "date": s,
            "age_bracket": r.dimension_values[0].value,
            "gender": "",
            "sessions": int(float(r.metric_values[0].value)),
            "users": int(float(r.metric_values[1].value)),
            "conversions": 0,
            "revenue": 0.0,
            "thresholds_applied": "true" if thresholded else "false",
            "freshness": tier,
            "updated_at": now,
        })

    # 매출/전환 brkdown — 차원별로 분리 호출
    g_breakdown = _purchase_breakdown(client, prop, s, s, ["userGender"])
    a_breakdown = _purchase_breakdown(client, prop, s, s, ["userAgeBracket"])
    for row in rows:
        if row["gender"] and not row["age_bracket"]:
            m = g_breakdown.get((row["gender"],))
        elif row["age_bracket"] and not row["gender"]:
            m = a_breakdown.get((row["age_bracket"],))
        else:
            m = None
        if m:
            row["conversions"] = m["count"]
            row["revenue"] = round(m["revenue"], 2)
    return rows

"""Meta Marketing API 클라이언트.

4-3_daily_report 패턴 흡수 + freshness tier·정렬·집계 헬퍼.
어트리뷰션은 Meta 기본값 (7d-click + 1d-view) 사용. ROAS·매출은 이 클라이언트 결과를 진실값으로 본다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Iterable

PURCHASE_KEYS = (
    "purchase",
    "omni_purchase",
    "offsite_conversion.fb_pixel_purchase",
)
ATC_KEYS = ("add_to_cart", "omni_add_to_cart", "offsite_conversion.fb_pixel_add_to_cart")
CHECKOUT_KEYS = ("initiate_checkout", "omni_initiated_checkout")
LANDING_PAGE_VIEW_KEYS = ("landing_page_view",)


def _pick(actions, keys: tuple[str, ...]) -> float:
    if not actions:
        return 0.0
    for a in actions:
        if a.get("action_type") in keys:
            try:
                return float(a.get("value", 0))
            except (TypeError, ValueError):
                return 0.0
    return 0.0


def freshness_tier(target_date: date, today: date | None = None) -> str:
    """Meta 데이터 안정성 tier — t1_preview ~ t28_meta_final."""
    today = today or date.today()
    age = (today - target_date).days
    if age < 1:
        return "t0_realtime"
    if age == 1:
        return "t1_preview"
    if age <= 6:
        return "t2_stable"
    if age <= 27:
        return "t7_meta_refresh"
    return "t28_meta_final"


@dataclass
class AdRow:
    campaign_name: str
    adset_name: str
    ad_name: str
    ad_id: str
    spend: float
    impressions: int
    reach: int
    frequency: float
    clicks: int
    link_clicks: float
    purchases: float
    purchase_value: float
    add_to_carts: float
    checkouts: float
    landing_views: float
    ctr: float
    cpm: float
    cpc: float
    roas: float
    cpa: float
    raw: dict = field(default_factory=dict)


def parse_insight(insight) -> AdRow:
    d = dict(insight)
    spend = float(d.get("spend") or 0)
    impressions = int(float(d.get("impressions") or 0))
    reach = int(float(d.get("reach") or 0))
    frequency = float(d.get("frequency") or 0)
    clicks = int(float(d.get("clicks") or 0))
    actions = d.get("actions") or []
    action_values = d.get("action_values") or []
    purchases = _pick(actions, PURCHASE_KEYS)
    purchase_value = _pick(action_values, PURCHASE_KEYS)
    add_to_carts = _pick(actions, ATC_KEYS)
    checkouts = _pick(actions, CHECKOUT_KEYS)
    link_clicks = _pick(actions, ("link_click",))
    landing_views = _pick(actions, LANDING_PAGE_VIEW_KEYS)
    ctr = float(d.get("ctr") or 0)
    cpm = float(d.get("cpm") or 0)
    if cpm == 0 and impressions > 0:
        cpm = spend / impressions * 1000
    cpc = float(d.get("cpc") or 0)
    if cpc == 0 and clicks > 0:
        cpc = spend / clicks
    roas = 0.0
    for pr in d.get("purchase_roas") or []:
        try:
            roas = float(pr.get("value") or 0)
        except (TypeError, ValueError):
            roas = 0.0
        if roas:
            break
    if roas == 0 and spend > 0:
        roas = purchase_value / spend
    cpa = spend / purchases if purchases > 0 else 0.0
    return AdRow(
        campaign_name=d.get("campaign_name") or "",
        adset_name=d.get("adset_name") or "",
        ad_name=d.get("ad_name") or "",
        ad_id=d.get("ad_id") or "",
        spend=spend,
        impressions=impressions,
        reach=reach,
        frequency=frequency,
        clicks=clicks,
        link_clicks=link_clicks,
        purchases=purchases,
        purchase_value=purchase_value,
        add_to_carts=add_to_carts,
        checkouts=checkouts,
        landing_views=landing_views,
        ctr=ctr,
        cpm=cpm,
        cpc=cpc,
        roas=roas,
        cpa=cpa,
        raw=d,
    )


class MetaClient:
    """facebook-business SDK 얇은 래퍼. ad_account_id, app_id/secret/token 필수."""

    BASE_FIELDS = [
        "campaign_name", "adset_name", "ad_name", "ad_id",
        "spend", "impressions", "clicks", "ctr", "cpm", "cpc",
        "actions", "action_values", "purchase_roas",
        "frequency", "reach",
    ]

    def __init__(self, env: dict[str, str]):
        from facebook_business.api import FacebookAdsApi
        from facebook_business.adobjects.adaccount import AdAccount

        FacebookAdsApi.init(env["META_APP_ID"], env["META_APP_SECRET"], env["META_ACCESS_TOKEN"])
        self.account = AdAccount(env["META_AD_ACCOUNT_ID"])

    def insights(self, since: str, until: str, level: str = "ad", fields: list[str] | None = None,
                 limit: int = 500, extra_params: dict | None = None) -> list[AdRow]:
        params = {
            "time_range": {"since": since, "until": until},
            "level": level,
            "limit": limit,
        }
        if extra_params:
            params.update(extra_params)
        rows: list[AdRow] = []
        for ins in self.account.get_insights(fields=fields or self.BASE_FIELDS, params=params):
            rows.append(parse_insight(ins))
        return rows

    def fetch_creative(self, ad_id: str) -> dict | None:
        """ad_id → AdCreative 메타데이터 (thumbnail/image URL + 카피).

        4-4_marketing_dashboard 의 _fetch_creative 포팅.
        실패 시 None — Meta CDN URL 은 갱신 시 만료되므로 별도 리프레시 작업이 필요할 수 있음.
        """
        from facebook_business.adobjects.ad import Ad
        from facebook_business.adobjects.adcreative import AdCreative
        try:
            ad = Ad(ad_id).api_get(fields=["creative"])
            creative_ref = ad.get("creative")
            if not creative_ref:
                return None
            creative_id = creative_ref.get("id")
            if not creative_id:
                return None
            cr = AdCreative(creative_id).api_get(fields=[
                "thumbnail_url", "image_url", "video_id",
                "title", "body", "call_to_action_type", "object_story_spec",
            ])
            body = cr.get("body") or ""
            title = cr.get("title") or ""
            cta = cr.get("call_to_action_type") or ""
            oss = cr.get("object_story_spec") or {}
            for sub_key in ("link_data", "video_data", "photo_data"):
                sub = oss.get(sub_key) or {}
                if not body:
                    body = sub.get("message") or sub.get("description") or ""
                if not title:
                    title = sub.get("name") or sub.get("title") or ""
                if not cta:
                    cta_obj = sub.get("call_to_action") or {}
                    cta = cta_obj.get("type") or ""
            return {
                "thumbnail_url": cr.get("thumbnail_url") or "",
                "image_url": cr.get("image_url") or "",
                "video_id": cr.get("video_id") or "",
                "title": title,
                "body": body,
                "call_to_action_type": cta,
            }
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️  creative fetch 실패 ad_id={ad_id}: {e}")
            return None

    def daily(self, target: date) -> dict:
        """4-3 daily 와 동일한 묶음 — 계정·캠페인·광고·전일·7일 평균."""
        s = target.strftime("%Y-%m-%d")
        prev = (target - timedelta(days=1)).strftime("%Y-%m-%d")
        week_start = (target - timedelta(days=7)).strftime("%Y-%m-%d")
        week_end = (target - timedelta(days=1)).strftime("%Y-%m-%d")
        return {
            "date": s,
            "tier": freshness_tier(target),
            "account": self.insights(s, s, level="account"),
            "campaigns": self.insights(s, s, level="campaign"),
            "ads": self.insights(s, s, level="ad"),
            "previous": self.insights(prev, prev, level="account"),
            "week": self.insights(week_start, week_end, level="account"),
        }


def aggregate(rows: Iterable[AdRow]) -> AdRow:
    """합산 — KPI 카드용. 가중 평균은 spend 기준."""
    total = AdRow(
        campaign_name="TOTAL", adset_name="", ad_name="", ad_id="",
        spend=0.0, impressions=0, reach=0, frequency=0.0,
        clicks=0, link_clicks=0,
        purchases=0, purchase_value=0, add_to_carts=0, checkouts=0, landing_views=0,
        ctr=0, cpm=0, cpc=0, roas=0, cpa=0,
    )
    for r in rows:
        total.spend += r.spend
        total.impressions += r.impressions
        total.reach += r.reach
        total.clicks += r.clicks
        total.link_clicks += r.link_clicks
        total.purchases += r.purchases
        total.purchase_value += r.purchase_value
        total.add_to_carts += r.add_to_carts
        total.checkouts += r.checkouts
        total.landing_views += r.landing_views
    if total.impressions:
        total.ctr = total.clicks / total.impressions * 100
        total.cpm = total.spend / total.impressions * 1000
    if total.clicks:
        total.cpc = total.spend / total.clicks
    if total.spend:
        total.roas = total.purchase_value / total.spend
    if total.purchases:
        total.cpa = total.spend / total.purchases
    if total.reach:
        total.frequency = total.impressions / total.reach
    return total

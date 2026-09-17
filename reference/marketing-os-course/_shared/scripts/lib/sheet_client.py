"""Google Sheets 클라이언트 — 4-4_marketing_dashboard 패턴 흡수 + dry-run 모드.

env 키 (우선순위):
- GOOGLE_SHEETS_ID (필수)
- GOOGLE_SERVICE_ACCOUNT_PATH (서비스 계정 JSON 파일 경로) 또는
- GOOGLE_SERVICE_ACCOUNT_JSON (JSON 전체 문자열, GitHub Secrets 친화) 또는
- GOOGLE_SERVICE_ACCOUNT_EMAIL + GOOGLE_PRIVATE_KEY (4-4 호환)
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.readonly",
]

# 5탭 + meta_creatives — 4-4 와 동일 스키마 사용
SCHEMA: dict[str, dict] = {
    "meta_daily": {
        "key_cols": ["date"],
        "headers": [
            "date", "spend", "impressions", "clicks", "ctr", "cpm", "cpc",
            "purchases", "purchase_value", "roas", "cpa", "aov",
            "add_to_carts", "checkouts", "freshness", "updated_at",
        ],
    },
    "meta_breakdowns": {
        "key_cols": ["date", "level", "id"],
        "headers": [
            "date", "level", "id", "campaign_name", "adset_name", "ad_name",
            "spend", "impressions", "reach", "frequency",
            "clicks", "link_clicks", "ctr", "cpm", "cpc",
            "landing_views", "cpa_landing",
            "add_to_carts", "cpa_atc",
            "checkouts", "cpa_checkout",
            "purchases", "purchase_value", "roas", "cpa",
            "freshness", "updated_at",
        ],
    },
    # 성별·연령 분해 — ad level 1일 호출 (breakdowns=['age','gender'])
    "meta_demographics": {
        "key_cols": ["date", "id", "gender", "age"],
        "headers": [
            "date", "level", "id", "campaign_name", "adset_name", "ad_name",
            "gender", "age",
            "spend", "impressions", "reach", "clicks",
            "purchases", "purchase_value", "roas",
            "freshness", "updated_at",
        ],
    },
    # 광고 소재 메타데이터 캐시 — 4-4_marketing_dashboard 동일 스키마
    # 신규 ad_id 만 1회 fetch (Meta CDN URL 만료 시 별도 리프레시)
    "meta_creatives": {
        "key_cols": ["ad_id"],
        "headers": [
            "ad_id", "ad_name", "adset_name", "campaign_name",
            "thumbnail_url", "image_url", "video_id",
            "title", "body", "call_to_action_type",
            "fetched_at", "updated_at",
        ],
    },
    "ga4_daily": {
        "key_cols": ["date"],
        "headers": [
            "date", "sessions", "users", "new_users", "returning_users",
            "active_users", "avg_session_duration",
            "conversions", "conversion_rate",
            "top_source", "top_medium", "top_campaign",
            "freshness", "updated_at",
        ],
    },
    "ga4_channel_daily": {
        "key_cols": ["date", "channel_group", "source", "medium", "campaign"],
        "headers": [
            "date", "channel_group", "source", "medium", "campaign",
            "sessions", "new_users", "engaged_sessions",
            "conversions", "revenue",
            "freshness", "updated_at",
        ],
    },
    "ga4_device_daily": {
        "key_cols": ["date", "device_category"],
        "headers": [
            "date", "device_category",
            "sessions", "users", "conversions", "cvr", "revenue",
            "freshness", "updated_at",
        ],
    },
    "ga4_landing_daily": {
        "key_cols": ["date", "landing_path"],
        "headers": [
            "date", "landing_path",
            "sessions", "engaged_sessions", "bounce_rate",
            "conversions", "revenue",
            "freshness", "updated_at",
        ],
    },
    "ga4_product_daily": {
        "key_cols": ["date", "item_id"],
        "headers": [
            "date", "item_name", "item_id",
            "item_views", "add_to_carts", "purchases", "revenue",
            "view_to_atc", "atc_to_purchase",
            "freshness", "updated_at",
        ],
    },
    "ga4_funnel_daily": {
        "key_cols": ["date"],
        "headers": [
            "date",
            "page_view", "view_item", "add_to_cart", "view_cart", "purchase_total",
            "view_to_pdp", "pdp_to_atc", "atc_to_cart", "cart_to_purchase", "overall_cvr",
            "freshness", "updated_at",
        ],
    },
    "ga4_demo_daily": {
        "key_cols": ["date", "age_bracket", "gender"],
        "headers": [
            "date", "age_bracket", "gender",
            "sessions", "users", "conversions", "revenue",
            "thresholds_applied",
            "freshness", "updated_at",
        ],
    },
    "ga4_geo_daily": {
        "key_cols": ["date", "region"],
        "headers": [
            "date", "region",
            "sessions", "users", "conversions", "revenue",
            "freshness", "updated_at",
        ],
    },
    "clarity_daily": {
        "key_cols": ["date"],
        "headers": [
            "date", "sessions", "dead_clicks", "rage_clicks",
            "excessive_scroll", "quick_back",
            "top_dead_click_url", "top_rage_click_url",
            "freshness", "updated_at",
        ],
    },
    "experiments_observed": {
        "key_cols": ["date", "exp_id"],
        "headers": [
            "date", "exp_id", "title", "status", "days_running",
            "primary_metric", "primary_value", "primary_baseline",
            "primary_threshold", "primary_signal",
            "updated_at",
        ],
    },
}


def _credentials(env: dict[str, str]):
    from google.oauth2.service_account import Credentials
    sa_path = env.get("GOOGLE_SERVICE_ACCOUNT_PATH")
    sa_json = env.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    sa_email = env.get("GOOGLE_SERVICE_ACCOUNT_EMAIL")
    sa_key = env.get("GOOGLE_PRIVATE_KEY")
    if sa_path:
        return Credentials.from_service_account_file(sa_path, scopes=SCOPES)
    if sa_json:
        return Credentials.from_service_account_info(json.loads(sa_json), scopes=SCOPES)
    if sa_email and sa_key:
        return Credentials.from_service_account_info({
            "type": "service_account",
            "client_email": sa_email,
            "private_key": sa_key.replace("\\n", "\n"),
            "token_uri": "https://oauth2.googleapis.com/token",
        }, scopes=SCOPES)
    raise RuntimeError("Google 서비스 계정 키 미설정 — PATH / JSON / EMAIL+KEY 중 하나 필요")


def open_sheet(env: dict[str, str]):
    """gspread 시트 객체 반환. 환경변수에 GOOGLE_SHEETS_ID 필요."""
    import gspread
    sheet_id = env.get("GOOGLE_SHEETS_ID")
    if not sheet_id:
        raise RuntimeError("GOOGLE_SHEETS_ID env 누락")
    gc = gspread.authorize(_credentials(env))
    return gc.open_by_key(sheet_id)


def ensure_headers(sh, tab_name: str) -> list[str]:
    import gspread
    if tab_name not in SCHEMA:
        raise ValueError(f"알 수 없는 탭: {tab_name}")
    headers = SCHEMA[tab_name]["headers"]
    try:
        ws = sh.worksheet(tab_name)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=tab_name, rows=1000, cols=max(20, len(headers)))
    existing = ws.row_values(1)
    if existing != headers:
        ws.update(values=[headers], range_name="A1")
    return headers


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, (int, float)):
        return v
    return str(v)


def upsert_rows(sh, tab_name: str, rows: list[dict]) -> dict:
    if not rows:
        return {"updated": 0, "appended": 0}
    spec = SCHEMA[tab_name]
    headers = spec["headers"]
    key_cols = spec["key_cols"]
    ensure_headers(sh, tab_name)
    ws = sh.worksheet(tab_name)

    all_values = ws.get_all_values()
    key_to_rownum: dict[tuple, int] = {}
    for i, row in enumerate(all_values[1:], start=2):
        key = tuple(row[headers.index(c)] if headers.index(c) < len(row) else "" for c in key_cols)
        key_to_rownum[key] = i

    updates: list[tuple[int, list]] = []
    appends: list[list] = []
    for r in rows:
        key = tuple(str(r.get(c, "")) for c in key_cols)
        row_values = [_cell(r.get(h, "")) for h in headers]
        if key in key_to_rownum:
            updates.append((key_to_rownum[key], row_values))
        else:
            appends.append(row_values)
    if updates:
        body = [{"range": f"A{rn}", "values": [vals]} for rn, vals in updates]
        ws.batch_update(body, value_input_option="USER_ENTERED")
    if appends:
        ws.append_rows(appends, value_input_option="USER_ENTERED")
    return {"updated": len(updates), "appended": len(appends)}


class DryRunSink:
    """Sheets 키 없을 때 — 페이로드를 JSON 파일로 dump."""

    def __init__(self, out_dir: Path):
        self.out_dir = out_dir
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.tabs: dict[str, list[dict]] = {}

    def upsert(self, tab_name: str, rows: list[dict]) -> dict:
        self.tabs.setdefault(tab_name, []).extend(rows)
        return {"updated": 0, "appended": len(rows)}

    def flush(self, label: str) -> Path:
        ts = datetime.now().strftime("%Y%m%dT%H%M%S")
        p = self.out_dir / f"etl_payload_{label}_{ts}.json"
        p.write_text(json.dumps(self.tabs, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        return p

#!/usr/bin/env python3
"""Meta 광고 크리에이티브 썸네일을 로컬에 영구 저장.

시트(meta_creatives 탭) 또는 payload 에서 ad_id·ad_name 을 읽고,
Meta API 로 fresh 썸네일/이미지 URL 을 받아 _shared/outputs/creatives/{ad_name}.jpg 로 저장.
overview 의 _scan_creatives() 가 이 로컬 파일을 우선 사용 → Meta CDN URL 만료와 무관.

사용: python3 _shared/scripts/download_creatives.py
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.env_loader import load_env
from lib.meta_client import MetaClient
from lib.sheet_client import open_sheet

ROOT = Path(__file__).resolve().parents[1]
# overview HTML 의 `../creatives/` 가 가리키는 위치 (11_dashboard/creatives/)
CREATIVES_DIR = ROOT.parent / "11_dashboard" / "creatives"


def safe_name(name: str) -> str:
    """파일명용 — 경로 구분자만 제거 (stem == ad_name 매칭 유지)."""
    return re.sub(r"[/\\]+", "_", (name or "").strip())


def hires_creative_thumb(ad_id: str, w: int = 1080, h: int = 1080) -> str | None:
    """AdCreative.thumbnail_url 을 큰 사이즈로 요청 (ads_read 권한으로 가능).

    동영상 광고도 64px 기본 대신 최대 w×h 에 맞춘 포스터 프레임을 받음.
    AdVideo.get_thumbnails 는 ads_read 권한 밖(#10)이라 이 경로를 사용.
    """
    try:
        from facebook_business.adobjects.ad import Ad
        from facebook_business.adobjects.adcreative import AdCreative
        ad = Ad(ad_id).api_get(fields=["creative"])
        cid = (ad.get("creative") or {}).get("id")
        if not cid:
            return None
        cr = AdCreative(cid).api_get(
            fields=["thumbnail_url"],
            params={"thumbnail_width": w, "thumbnail_height": h},
        )
        return cr.get("thumbnail_url")
    except Exception as e:
        print(f"    (hi-res thumb 실패 {ad_id}: {e})")
        return None


def ad_list_from_sheet(env: dict) -> list[tuple[str, str]]:
    """meta_creatives 탭에서 (ad_id, ad_name) 유니크 목록."""
    sh = open_sheet(env)
    ws = sh.worksheet("meta_creatives")
    vals = ws.get_all_values()
    if len(vals) < 2:
        return []
    headers = vals[0]
    i_id = headers.index("ad_id")
    i_name = headers.index("ad_name")
    seen: dict[str, str] = {}
    for r in vals[1:]:
        if len(r) <= max(i_id, i_name):
            continue
        ad_id = r[i_id].strip()
        if ad_id and ad_id not in seen:
            seen[ad_id] = r[i_name].strip()
    return list(seen.items())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--force", action="store_true", help="기존 파일도 재다운로드 (동영상 고해상도 갱신용)")
    args = p.parse_args()

    env = load_env()
    client = MetaClient(env)
    CREATIVES_DIR.mkdir(parents=True, exist_ok=True)

    ads = ad_list_from_sheet(env)
    print(f"크리에이티브 대상: {len(ads)}개 (시트 meta_creatives) · force={args.force}")

    saved = skipped = failed = 0
    for ad_id, ad_name in ads:
        if not ad_name:
            ad_name = ad_id
        out = CREATIVES_DIR / f"{safe_name(ad_name)}.jpg"
        if not args.force and out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        cr = client.fetch_creative(ad_id)
        if not cr:
            print(f"  ✗ {ad_name}: fetch_creative None")
            failed += 1
            continue
        # 이미지 광고 → image_url (고해상도). 동영상 → AdVideo 최대 썸네일, 폴백 thumbnail_url
        url = cr.get("image_url")
        kind = "image"
        if not url:
            url = hires_creative_thumb(ad_id)
            kind = "hi-thumb"
        if not url:
            url = cr.get("thumbnail_url")
            kind = "thumb-fallback"
        if not url:
            print(f"  ✗ {ad_name}: URL 없음")
            failed += 1
            continue
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            out.write_bytes(resp.content)
            saved += 1
            print(f"  ✓ {ad_name}.jpg [{kind}] ({len(resp.content):,} bytes)")
        except Exception as e:
            print(f"  ✗ {ad_name}: 다운로드 실패 {e}")
            failed += 1

    print(f"\n완료 — 저장 {saved} · 스킵(기존) {skipped} · 실패 {failed}")
    print(f"위치: {CREATIVES_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

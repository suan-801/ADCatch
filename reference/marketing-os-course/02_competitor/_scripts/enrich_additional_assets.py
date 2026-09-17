"""
메타 광고 라이브러리 "이 광고의 추가 자산" 섹션 보강 스크래퍼.

Apify 액터(curious_coder/facebook-ads-library-scraper)는 메인 카드 자산만 가져오고,
"이 광고의 추가 자산(Additional ad assets)" 섹션의 링크·이미지·영상은 누락한다.
이 스크립트는 ad_id 단위로 https://www.facebook.com/ads/library/?id={ad_id} 에 직접 진입해
해당 섹션을 펼치고 추가 자산 URL 을 긁어 dashboard.json 에 머지한다.

기본 동작:
- dashboard.json 에서 domain == 'fb.com' 인 광고만 골라 후처리 (Instant Experience 캔버스 광고)
- --all 옵션을 주면 전체 광고 대상

사용 예:
    python3 enrich_additional_assets.py
    python3 enrich_additional_assets.py --headed         # UI 띄우고 디버깅
    python3 enrich_additional_assets.py --ad-ids 1234567890123456,1234567890123457
    python3 enrich_additional_assets.py --all            # 모든 광고
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

SCRIPT_DIR = Path(__file__).resolve().parent
DASHBOARD_DIR = SCRIPT_DIR.parent / "dashboard"
DASHBOARD_JSON = DASHBOARD_DIR / "dashboard.json"
RAW_OUTPUT = DASHBOARD_DIR / "additional_assets_raw.json"

ADLIB_URL_TPL = "https://www.facebook.com/ads/library/?id={ad_id}"

# 페이지에 렌더된 모든 광고 카드를 ad_id 별로 묶어서 외부 링크·이미지·영상을 일괄 추출.
# Meta 광고 라이브러리는 SPA 라 카드 내 "이 광고의 추가 자산" disclosure 가 닫혀있을 수 있는데,
# 그래도 메인 캔버스 / 단축링크 / 히어로 자산은 카드 DOM 안에 렌더되어 있어 긁을 수 있다.
# 아래 JS 는 모든 카드를 traverse 해서 카드별 dict 를 반환.
EXTRACT_PAGE_JS = r"""
() => {
  // facebook.com l.php redirect 의 u 파라미터를 까서 실제 외부 URL 만 반환.
  // 페이스북·메타 도메인은 canvas_doc 만 통과.
  const unwrap = (href) => {
    if (!href || href.startsWith('javascript:') || href.startsWith('#')) return null;
    try {
      const u = new URL(href);
      const h = u.hostname || '';
      if (h.endsWith('facebook.com') && u.pathname === '/l.php') {
        const target = u.searchParams.get('u');
        return target ? unwrap(target) : null;
      }
      if (h.endsWith('facebook.com') || h.endsWith('messenger.com') || h.endsWith('meta.com')) {
        if (u.pathname.includes('canvas_doc') || u.pathname.includes('/canvas/')) return href;
        return null;
      }
      if (h === 'fb.com' || h.endsWith('.fb.com')) {
        if (u.pathname.includes('canvas_doc') || u.pathname.includes('/canvas/')) return href;
        return null;
      }
      return href;
    } catch (e) { return null; }
  };

  const isAssetImg = (src) =>
    src && src.startsWith('http') && !src.includes('emoji') &&
    !src.includes('rsrc.php') && !src.includes('static.xx.fbcdn');

  // 1) "라이브러리 ID: {id}" 노드를 모두 찾아서 각 카드 root 정의
  const allSpans = Array.from(document.querySelectorAll('span, div'));
  const idMarkers = [];
  for (const el of allSpans) {
    const t = (el.innerText || el.textContent || '').trim();
    const m = t.match(/^라이브러리\s*ID:\s*(\d{6,})$|^Library\s*ID:\s*(\d{6,})$/);
    if (m) idMarkers.push({ el, ad_id: m[1] || m[2] });
  }

  // 2) 각 마커의 카드 root 결정 (부모로 올라가며, 다른 라이브러리 ID 가 포함되지 않는 한계까지)
  const cards = [];
  for (const { el, ad_id } of idMarkers) {
    let root = el;
    while (root.parentElement) {
      const parentText = (root.parentElement.innerText || '');
      const matches = parentText.match(/라이브러리\s*ID|Library\s*ID/g) || [];
      if (matches.length > 1) break;
      const rect = root.parentElement.getBoundingClientRect();
      if (rect.height > 3500) break;
      root = root.parentElement;
    }
    cards.push({ ad_id, root });
  }

  // 3) 각 카드별 자산 수집
  const result = {};
  for (const { ad_id, root } of cards) {
    if (result[ad_id]) continue;
    const links = new Set();
    const images = new Set();
    const videos = new Set();

    root.querySelectorAll('a[href]').forEach(a => {
      const u = unwrap(a.href);
      if (u) links.add(u);
    });
    root.querySelectorAll('img').forEach(img => {
      if (isAssetImg(img.src)) images.add(img.src);
    });
    root.querySelectorAll('video').forEach(v => {
      if (v.src && v.src.startsWith('http')) videos.add(v.src);
      v.querySelectorAll('source').forEach(s => {
        if (s.src && s.src.startsWith('http')) videos.add(s.src);
      });
    });

    result[ad_id] = {
      links: Array.from(links),
      images: Array.from(images),
      videos: Array.from(videos),
      card_text_length: (root.innerText || '').length,
    };
  }

  return {
    n_cards: cards.length,
    n_unique_ad_ids: Object.keys(result).length,
    cards: result,
  };
}
"""

# 페이지 전체에서 외부 랜딩 도메인을 모두 긁는 백업 JS (섹션 헤더를 못 찾았을 때).
PAGE_FALLBACK_JS = r"""
() => {
  const links = new Set();
  const unwrap = (href) => {
    if (!href || href.startsWith('javascript:') || href.startsWith('#')) return null;
    try {
      const u = new URL(href);
      const h = u.hostname || '';
      if (h.endsWith('facebook.com') && u.pathname === '/l.php') {
        const target = u.searchParams.get('u');
        return target ? unwrap(target) : null;
      }
      if (h.endsWith('facebook.com') || h.endsWith('messenger.com') || h.endsWith('meta.com')) {
        if (u.pathname.includes('canvas_doc') || u.pathname.includes('/canvas/')) return href;
        return null;
      }
      if (h === 'fb.com' || h.endsWith('.fb.com')) {
        if (u.pathname.includes('canvas_doc') || u.pathname.includes('/canvas/')) return href;
        return null;
      }
      return href;
    } catch (e) { return null; }
  };
  document.querySelectorAll('a[href]').forEach(a => {
    const u = unwrap(a.href);
    if (u) links.add(u);
  });
  return Array.from(links);
}
"""


def dismiss_overlays(page) -> None:
    """쿠키 동의·로그인 prompt 가 뜨면 닫기."""
    candidates = [
        "button:has-text('모두 허용')",
        "button:has-text('Allow all')",
        "button:has-text('Accept All')",
        "button:has-text('확인')",
        "button:has-text('Decline')",
        "div[role='dialog'] button[aria-label='Close']",
        "div[aria-label='닫기']",
        "[aria-label='Close']",
    ]
    for sel in candidates:
        try:
            page.locator(sel).first.click(timeout=1500)
            page.wait_for_timeout(500)
        except Exception:
            pass


def scrape_brand_page(page, seed_ad_id: str, debug_dir: Path | None = None, debug_tag: str = "") -> dict[str, Any]:
    """광고주 페이지(seed_ad_id 의 페이지)를 한 번 로드해서 모든 광고 카드의 자산을 일괄 추출."""
    url = ADLIB_URL_TPL.format(ad_id=seed_ad_id)
    started = time.time()
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
    except PlaywrightTimeout:
        return {"status": "timeout_goto", "elapsed": time.time() - started, "cards": {}}

    page.wait_for_timeout(2500)
    dismiss_overlays(page)
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PlaywrightTimeout:
        pass
    page.wait_for_timeout(1500)
    # lazy-load 된 카드들 다 그려지도록 페이지 끝까지 스크롤 (왕복)
    try:
        # 끝까지 내려가면서 새 카드 트리거
        for _ in range(12):
            page.evaluate("() => window.scrollBy(0, window.innerHeight * 1.5)")
            page.wait_for_timeout(700)
        # 위로 다시
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(1500)
        # 한 번 더 끝까지
        for _ in range(8):
            page.evaluate("() => window.scrollBy(0, window.innerHeight * 1.5)")
            page.wait_for_timeout(500)
    except Exception:
        pass
    page.wait_for_timeout(1500)

    if debug_dir is not None:
        try:
            debug_dir.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(debug_dir / f"{debug_tag or seed_ad_id}.png"), full_page=True)
            (debug_dir / f"{debug_tag or seed_ad_id}.html").write_text(page.content(), encoding="utf-8")
        except Exception:
            pass

    try:
        page_result = page.evaluate(EXTRACT_PAGE_JS)
    except Exception as e:
        page_result = {"error": str(e), "cards": {}}

    page_result["seed_ad_id"] = seed_ad_id
    page_result["url"] = url
    page_result["elapsed"] = round(time.time() - started, 2)
    return page_result


def collect_target_ads(dashboard: dict, only_fb_com: bool = True, ad_ids: list[str] | None = None):
    targets = []
    for slug, b in dashboard["brands"].items():
        for ad in b["ads"]:
            aid = ad["ad_id"]
            if ad_ids and aid not in ad_ids:
                continue
            if only_fb_com and ad.get("domain") != "fb.com":
                continue
            targets.append({"brand_slug": slug, "ad_id": aid, "format": ad.get("format")})
    return targets


def merge_into_dashboard(dashboard: dict, results: dict[str, dict]) -> int:
    """결과를 dashboard.json 의 각 ad 객체에 additional_assets 필드로 머지. 갱신된 광고 수 반환."""
    n = 0
    for slug, b in dashboard["brands"].items():
        for ad in b["ads"]:
            r = results.get(ad["ad_id"])
            if not r:
                continue
            extras = {
                "links": r.get("links", []),
                "images": r.get("images", []),
                "videos": r.get("videos", []),
                "fallback_links": r.get("page_external_links", []),
                "scrape_status": r.get("status"),
                "scraped_at": r.get("scraped_at"),
            }
            # 메인 link_url / media src 와 중복되는 것은 제거
            main_link = ad.get("link_url", "")
            main_media = {m.get("src") for m in (ad.get("media") or []) if m.get("src")}
            extras["links"] = [u for u in extras["links"] if u and u != main_link]
            extras["images"] = [u for u in extras["images"] if u and u not in main_media]
            extras["videos"] = [u for u in extras["videos"] if u and u not in main_media]
            ad["additional_assets"] = extras
            n += 1
    return n


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--ad-ids", help="콤마로 구분된 ad_id 목록. 지정 시 dashboard 의 fb.com 필터 무시")
    parser.add_argument("--all", action="store_true", help="domain 무관 모든 광고 대상")
    parser.add_argument("--headed", action="store_true", help="브라우저 UI 표시 (디버그)")
    parser.add_argument("--sleep", type=float, default=2.0, help="광고 사이 대기 시간(초)")
    parser.add_argument("--no-merge", action="store_true", help="dashboard.json 머지 생략 (raw 만 저장)")
    parser.add_argument("--debug", action="store_true", help="각 광고별 스크린샷·HTML 저장")
    args = parser.parse_args()

    if not DASHBOARD_JSON.exists():
        sys.exit(f"dashboard.json 없음: {DASHBOARD_JSON}")

    with DASHBOARD_JSON.open(encoding="utf-8") as f:
        dashboard = json.load(f)

    only_fb = not args.all
    ad_ids_filter = None
    if args.ad_ids:
        ad_ids_filter = [s.strip() for s in args.ad_ids.split(",") if s.strip()]
        only_fb = False

    targets = collect_target_ads(dashboard, only_fb_com=only_fb, ad_ids=ad_ids_filter)
    if not targets:
        sys.exit("대상 광고 없음.")

    print(f"대상 광고: {len(targets)}건")
    for t in targets:
        print(f"  {t['brand_slug']:12} {t['ad_id']:20} {t.get('format')}")
    print()

    results: dict[str, dict] = {}
    started_all = time.time()

    with sync_playwright() as pw:
        browser = pw.chromium.launch(
            headless=not args.headed,
            args=["--disable-blink-features=AutomationControlled"],
        )
        context = browser.new_context(
            locale="ko-KR",
            user_agent=(
                "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
                "Mobile/15E148 Safari/604.1"
            ),
            viewport={"width": 414, "height": 896},
            is_mobile=True,
            has_touch=True,
        )
        page = context.new_page()

        debug_dir = (DASHBOARD_DIR / "_debug") if args.debug else None

        # brand_slug 별로 묶어서 페이지 1회 진입 → 모든 카드 일괄 추출
        by_brand: dict[str, list] = {}
        for t in targets:
            by_brand.setdefault(t["brand_slug"], []).append(t)

        print(f"브랜드별 페이지 진입: {len(by_brand)}회 (이전: {len(targets)}회)\n")
        for slug, brand_targets in by_brand.items():
            seed = brand_targets[0]["ad_id"]
            print(f"== {slug} ({len(brand_targets)}건, seed={seed})")
            try:
                page_result = scrape_brand_page(page, seed, debug_dir=debug_dir, debug_tag=slug)
            except Exception as e:
                page_result = {"error": str(e), "cards": {}}

            cards = page_result.get("cards", {})
            print(f"   페이지 카드 총 {page_result.get('n_unique_ad_ids', 0)}건 ({page_result.get('elapsed', '?')}s)")
            for t in brand_targets:
                aid = t["ad_id"]
                card = cards.get(aid)
                if card:
                    r = {
                        "found": True,
                        "ad_id": aid,
                        "brand_slug": slug,
                        "links": card.get("links", []),
                        "images": card.get("images", []),
                        "videos": card.get("videos", []),
                        "card_text_length": card.get("card_text_length"),
                        "status": "ok",
                        "scraped_at": datetime.now().isoformat(timespec="seconds"),
                    }
                else:
                    r = {
                        "found": False,
                        "ad_id": aid,
                        "brand_slug": slug,
                        "status": "card_not_in_page",
                        "scraped_at": datetime.now().isoformat(timespec="seconds"),
                    }
                results[aid] = r
                n_links = len(r.get("links") or [])
                n_imgs = len(r.get("images") or [])
                n_vids = len(r.get("videos") or [])
                print(f"   {aid} → {r['status']} (links={n_links} imgs={n_imgs} vids={n_vids})")
            print()

            if list(by_brand.keys()).index(slug) < len(by_brand) - 1:
                page.wait_for_timeout(int(args.sleep * 1000))

        context.close()
        browser.close()

    # raw 저장
    RAW_OUTPUT.write_text(
        json.dumps({
            "scraped_at": datetime.now().isoformat(timespec="seconds"),
            "n_targets": len(targets),
            "n_found": sum(1 for r in results.values() if r.get("status") == "ok"),
            "results": results,
        }, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nraw 저장: {RAW_OUTPUT}")

    if not args.no_merge:
        n = merge_into_dashboard(dashboard, results)
        DASHBOARD_JSON.write_text(json.dumps(dashboard, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"dashboard.json 머지: {n}건 갱신")

    print(f"총 {round(time.time()-started_all,1)}s 소요")


if __name__ == "__main__":
    main()

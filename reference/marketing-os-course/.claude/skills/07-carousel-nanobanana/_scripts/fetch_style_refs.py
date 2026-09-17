#!/usr/bin/env python3
"""
07-carousel-nanobanana — IG reference 자동 수집

reference-urls.md 의 활성 URL 들을 Apify `apify/instagram-post-scraper` 로 다운로드 →
references/styles/{slot}/ref-NN-{shortcode}.jpg 로 저장.

사전 준비
  - Apify 가입 → API 토큰: https://console.apify.com/settings/integrations
  - 액터 1회 활성화: https://apify.com/apify/instagram-post-scraper
  - 환경변수: export APIFY_TOKEN="apify_api_..."

사용
  python3 fetch_style_refs.py                          # 전체 활성 URL 다운로드
  python3 fetch_style_refs.py --slot 03-glossier       # 특정 슬롯만
  python3 fetch_style_refs.py --dry-run                # URL 파싱·분배만 출력
  python3 fetch_style_refs.py --actor apify/instagram-scraper  # 액터 변경
"""

import argparse
import json
import os
import pathlib
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


API_BASE = "https://api.apify.com/v2"
DEFAULT_ACTOR = "apify/instagram-scraper"
SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
STYLES_DIR = SKILL_DIR / "references" / "styles"
URLS_FILE = STYLES_DIR / "reference-urls.md"

VALID_SLOTS = {
    "01-versed",
    "02-glowrecipe",
    "03-glossier",
    "04-tula",
    "05-herbivore",
}

URL_LINE_RE = re.compile(
    r"(?P<url>https?://(?:www\.)?instagram\.com/(?:p|reel)/[A-Za-z0-9_-]+/?(?:\?[^\s]*)?)"
    r"\s*→\s*"
    r"(?P<slot>[\w-]+)"
    r"(?:\s*#\s*(?P<memo>.+))?"
)
SHORTCODE_RE = re.compile(r"/(?:p|reel)/([A-Za-z0-9_-]+)")
IMG_INDEX_RE = re.compile(r"[?&]img_index=(\d+)")


# ──────────────────────── HTTP / Apify ────────────────────────

def http(method, url, payload=None, raw=False, timeout=120):
    headers = {"Content-Type": "application/json"}
    body = json.dumps(payload).encode() if payload else None
    req = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as r:
            data = r.read()
    except HTTPError as e:
        sys.exit(f"HTTP {e.code} on {method} {url}\n{e.read().decode(errors='ignore')[:500]}")
    return data if raw else json.loads(data)


def run_actor(token, actor_id, run_input):
    actor_path = actor_id.replace("/", "~")
    url = f"{API_BASE}/acts/{actor_path}/runs?token={token}"
    return http("POST", url, payload=run_input)["data"]


def wait_run(token, run_id, poll=5, max_wait=600):
    url = f"{API_BASE}/actor-runs/{run_id}?token={token}"
    waited = 0
    while waited < max_wait:
        data = http("GET", url)["data"]
        status = data["status"]
        if status in ("SUCCEEDED", "FAILED", "ABORTED", "TIMED-OUT"):
            return data
        time.sleep(poll)
        waited += poll
    raise TimeoutError(f"Run {run_id} did not finish within {max_wait}s")


def get_items(token, dataset_id):
    url = f"{API_BASE}/datasets/{dataset_id}/items?token={token}&clean=true&format=json"
    return http("GET", url)


def download(url, dest):
    if not url:
        return False
    if dest.exists():
        print(f"  · 이미 존재 (스킵): {dest.name}")
        return False
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=60) as r:
            dest.write_bytes(r.read())
        return True
    except (HTTPError, URLError, TimeoutError) as e:
        print(f"  · 다운로드 실패: {url[:80]}... → {e}")
        return False


# ──────────────────────── reference-urls.md 파싱 ────────────────────────

def parse_url_file(path):
    """활성 (주석 처리되지 않은) URL 라인만 추출 → [(url, slot, img_index, memo)]"""
    if not path.exists():
        sys.exit(f"❌ {path} 없음. reference-urls.md 먼저 작성하세요.")

    entries = []
    skipped_invalid_slot = []
    in_fence = False
    in_url_section = False  # ## URL 리스트 섹션 진입 여부
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("```"):
            # URL 리스트 섹션 안의 코드펜스는 콘텐츠로 취급 (펜스 자체만 스킵, 본문 파싱)
            # 그 외 섹션의 코드펜스는 in_fence 토글로 스킵
            if not in_url_section:
                in_fence = not in_fence
            continue
        if line.startswith("## "):
            in_url_section = "URL 리스트" in line
            in_fence = False
            continue
        if in_fence or not in_url_section:
            continue
        if not line or line.startswith("#") or line.startswith(">"):
            continue
        m = URL_LINE_RE.search(line)
        if not m:
            continue
        url = m.group("url")
        slot = m.group("slot")
        memo = (m.group("memo") or "").strip()
        if slot not in VALID_SLOTS:
            skipped_invalid_slot.append((url, slot))
            continue
        sc_m = SHORTCODE_RE.search(url)
        idx_m = IMG_INDEX_RE.search(url)
        shortcode = sc_m.group(1) if sc_m else ""
        img_index = int(idx_m.group(1)) if idx_m else None  # None = 전체 슬라이드
        entries.append({
            "url": url,
            "slot": slot,
            "shortcode": shortcode,
            "img_index": img_index,
            "memo": memo,
        })

    if skipped_invalid_slot:
        print("⚠️  유효하지 않은 슬롯 라벨 (스킵됨):")
        for u, s in skipped_invalid_slot:
            print(f"   - {s} ← {u[:60]}")
        print(f"   유효 슬롯: {sorted(VALID_SLOTS)}")
    return entries


def next_ref_number(slot_dir):
    """슬롯 폴더의 기존 ref-NN-*.{png,jpg,jpeg} 다음 번호 반환"""
    if not slot_dir.exists():
        return 1
    nums = []
    for f in slot_dir.iterdir():
        m = re.match(r"ref-(\d+)", f.name)
        if m:
            nums.append(int(m.group(1)))
    return (max(nums) if nums else 0) + 1


# ──────────────────────── Apify IG 호출 ────────────────────────

def fetch_post_data(token, actor, urls):
    """URL 리스트 → 게시물 dataset items"""
    run_input = {
        "directUrls": urls,
        "resultsType": "posts",
        "resultsLimit": len(urls),
        "addParentData": False,
    }
    print(f"▶ Apify {actor} 실행 ({len(urls)}개 URL)...")
    run = run_actor(token, actor, run_input)
    run_id = run["id"]
    final = wait_run(token, run_id)
    if final["status"] != "SUCCEEDED":
        sys.exit(f"❌ Apify run {final['status']}: {final.get('statusMessage', '')}")
    items = get_items(token, final["defaultDatasetId"])
    print(f"  · {len(items)} 게시물 데이터 회수")
    return items


def extract_image_url(post, img_index):
    """게시물 item 에서 img_index (1-base) 의 이미지 URL 추출.
    apify/instagram-post-scraper 와 apify/instagram-scraper 양쪽 응답 schema 호환."""
    # 1) childPosts (Sidecar 캐러셀)
    children = post.get("childPosts") or []
    if children and 1 <= img_index <= len(children):
        child = children[img_index - 1]
        return child.get("displayUrl") or child.get("imageUrl")
    # 2) images 배열
    images = post.get("images") or []
    if images and 1 <= img_index <= len(images):
        candidate = images[img_index - 1]
        if isinstance(candidate, str):
            return candidate
        if isinstance(candidate, dict):
            return candidate.get("url") or candidate.get("displayUrl")
    # 3) displayUrl (단일 이미지 게시물 또는 첫 슬라이드)
    return post.get("displayUrl") or post.get("imageUrl")


def extract_all_image_urls(post):
    """게시물 item 에서 모든 슬라이드 이미지 URL 리스트 추출 (1-base).
    캐러셀 → childPosts/images 전체. 단일 이미지 → displayUrl 1장."""
    urls = []
    # 1) childPosts (Sidecar 캐러셀) 우선
    children = post.get("childPosts") or []
    if children:
        for child in children:
            u = child.get("displayUrl") or child.get("imageUrl")
            urls.append(u)
        return urls
    # 2) images 배열
    images = post.get("images") or []
    if images:
        for c in images:
            if isinstance(c, str):
                urls.append(c)
            elif isinstance(c, dict):
                urls.append(c.get("url") or c.get("displayUrl"))
        return urls
    # 3) 단일 이미지 게시물
    single = post.get("displayUrl") or post.get("imageUrl")
    return [single] if single else []


# ──────────────────────── 메인 ────────────────────────

def main():
    parser = argparse.ArgumentParser(description="IG reference 자동 수집")
    parser.add_argument("--slot", choices=sorted(VALID_SLOTS), help="특정 슬롯만 다운로드")
    parser.add_argument("--dry-run", action="store_true", help="URL 파싱·분배만 출력 (Apify 호출 ❌)")
    parser.add_argument("--actor", default=DEFAULT_ACTOR, help=f"Apify 액터 ID (디폴트: {DEFAULT_ACTOR})")
    args = parser.parse_args()

    entries = parse_url_file(URLS_FILE)
    if args.slot:
        entries = [e for e in entries if e["slot"] == args.slot]

    if not entries:
        print("⚠️  활성 URL 없음. reference-urls.md 의 URL 라인 주석(#)을 풀거나 새 URL 을 추가하세요.")
        return

    # 슬롯별 분포 출력
    from collections import Counter
    dist = Counter(e["slot"] for e in entries)
    print(f"📋 활성 URL {len(entries)}개:")
    for slot in sorted(dist):
        print(f"   {slot}: {dist[slot]}장")

    if args.dry_run:
        print("\n--dry-run 종료 (다운로드 ❌)")
        return

    token = os.environ.get("APIFY_TOKEN")
    if not token:
        sys.exit("❌ APIFY_TOKEN 미설정. export APIFY_TOKEN='apify_api_...'")

    # Apify 일괄 호출 (URL 중복 제거)
    unique_urls = list({e["url"].split("?")[0]: e["url"].split("?")[0] for e in entries}.values())
    posts = fetch_post_data(token, args.actor, unique_urls)

    # shortcode → post 매핑
    sc_to_post = {}
    for p in posts:
        sc = p.get("shortCode") or p.get("shortcode") or ""
        if sc:
            sc_to_post[sc] = p

    # 다운로드 진행
    downloaded = 0
    skipped = 0
    failed = 0
    for entry in entries:
        slot = entry["slot"]
        sc = entry["shortcode"]
        idx = entry["img_index"]  # None = 전체 슬라이드
        memo = entry["memo"]

        post = sc_to_post.get(sc)
        if not post:
            print(f"  · 게시물 데이터 없음: {sc} ({slot})")
            failed += 1
            continue

        # idx=None 이면 전체 슬라이드, 아니면 단일 슬라이드만
        if idx is None:
            all_urls = extract_all_image_urls(post)
            if not all_urls:
                print(f"  · 이미지 URL 추출 실패 (전체): {sc} ({slot})")
                failed += 1
                continue
            targets = list(enumerate(all_urls, start=1))  # [(1, url1), (2, url2), ...]
            print(f"  · {sc} ({slot}): 전체 {len(targets)}슬라이드")
        else:
            img_url = extract_image_url(post, idx)
            if not img_url:
                print(f"  · 이미지 URL 추출 실패: {sc}#{idx} ({slot})")
                failed += 1
                continue
            targets = [(idx, img_url)]

        slot_dir = STYLES_DIR / slot
        memo_slug = re.sub(r"[^\w가-힣-]+", "-", memo).strip("-")[:30] if memo else ""
        suffix = f"-{memo_slug}" if memo_slug else ""

        for slide_idx, img_url in targets:
            n = next_ref_number(slot_dir)
            ext = ".jpg"
            if ".png" in img_url.lower().split("?")[0]:
                ext = ".png"
            dest = slot_dir / f"ref-{n:02d}-{sc}-i{slide_idx}{suffix}{ext}"

            if dest.exists():
                skipped += 1
                print(f"  · 이미 존재: {dest.name}")
                continue

            ok = download(img_url, dest)
            if ok:
                print(f"  ✅ {slot}/{dest.name}")
                downloaded += 1
            else:
                failed += 1

    print()
    print(f"📊 완료: 다운로드 {downloaded} / 스킵 {skipped} / 실패 {failed}")
    print(f"📂 저장 위치: {STYLES_DIR}/{{slot}}/")


if __name__ == "__main__":
    main()

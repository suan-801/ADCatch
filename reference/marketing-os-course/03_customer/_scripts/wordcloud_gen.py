#!/usr/bin/env python3
"""03-pain-from-reviews 자동 워드클라우드 생성기 (generic).

입력:
  - 03_customer/visuals/wordcloud_frequency.csv  (label, count, bucket, category)
    * bucket: pain | desire | trend
    * category: pain 의 강도(h/m/l/n) 또는 desire 의 4축(func/sense/social/identity)
  - 01_brand/brand_brief.md                       (컬러 팔레트 6슬롯 자동 추출)

출력:
  - 03_customer/visuals/pain_wordcloud.png        (bucket=pain 항목)
  - 03_customer/visuals/desire_wordcloud.png      (bucket=desire 항목)
  - 03_customer/visuals/trend_wordcloud.png       (bucket=trend 항목, 있으면)

사용:
  python3 03_customer/_scripts/wordcloud_gen.py
  python3 03_customer/_scripts/wordcloud_gen.py --csv path/to/freq.csv --out-dir path/to/out

원칙:
  - 브랜드·카테고리 무관 (재사용)
  - 컬러는 brand_brief.md 6슬롯에서 동적 로드, 실패 시 디폴트 폴백
  - wordcloud / matplotlib 미설치 시 친절한 안내 메시지
"""

from __future__ import annotations

import argparse
import csv
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
DEFAULT_CSV = ROOT / "03_customer" / "visuals" / "wordcloud_frequency.csv"
DEFAULT_OUT_DIR = ROOT / "03_customer" / "visuals"
DEFAULT_BRAND_BRIEF = ROOT / "01_brand" / "brand_brief.md"
FONT_PATH = "/System/Library/Fonts/AppleSDGothicNeo.ttc"  # macOS 시스템 한글 폰트

FALLBACK_COLORS = {
    "BG-Light":         "#FFF7EE",
    "BG-Deep":          "#2D2418",
    "BRAND-Signature":  "#FF7A2E",
    "BRAND-Sub":        "#FFEFD5",
    "TEXT-Primary":     "#2A1F14",
    "TEXT-Sub":         "#7A6651",
}

PAIN_STRENGTH_COLORS = {
    "h": "#D63C2F",
    "m": "#A8201A",
    "l": "#7A4F2E",
    "n": "#7A6651",
}


def load_brand_colors(brand_brief_path: pathlib.Path) -> dict[str, str]:
    """brand_brief.md 컬러 팔레트 6슬롯 표에서 HEX 값 추출. 실패 시 fallback."""
    colors = dict(FALLBACK_COLORS)
    if not brand_brief_path.exists():
        return colors
    text = brand_brief_path.read_text(encoding="utf-8")
    pattern = re.compile(r"`(BG-Light|BG-Deep|BRAND-Signature|BRAND-Sub|TEXT-Primary|TEXT-Sub)`.*?`(#[0-9A-Fa-f]{6})`")
    for slot, hex_val in pattern.findall(text):
        colors[slot] = hex_val.upper()
    return colors


def load_frequency_csv(csv_path: pathlib.Path) -> list[dict]:
    rows = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            label = (row.get("label") or "").strip()
            count_str = (row.get("count") or "0").strip()
            bucket = (row.get("bucket") or "").strip().lower()
            category = (row.get("category") or "").strip().lower()
            if not label or not count_str.isdigit():
                continue
            count = int(count_str)
            if count < 1:
                continue
            rows.append({"label": label, "count": count, "bucket": bucket, "category": category})
    return rows


def color_func_pain(colors):
    def f(word, *a, **kw):
        cat = WORD_CAT.get(word, "n")
        return PAIN_STRENGTH_COLORS.get(cat, colors["TEXT-Sub"])
    return f


def color_func_desire(colors):
    desire_palette = {
        "func":     colors["BRAND-Signature"],
        "sense":    "#D4AF37",
        "social":   "#5C7A3D",
        "identity": colors["TEXT-Primary"],
        "":         colors["BRAND-Signature"],
    }
    def f(word, *a, **kw):
        cat = WORD_CAT.get(word, "")
        return desire_palette.get(cat, colors["BRAND-Signature"])
    return f


def color_func_trend(colors):
    def f(word, *a, **kw):
        return colors["TEXT-Primary"]
    return f


WORD_CAT: dict[str, str] = {}


def build_one(rows, bucket, color_func, bg_color, font_path, out_path):
    from wordcloud import WordCloud
    bucket_rows = [r for r in rows if r["bucket"] == bucket]
    if not bucket_rows:
        return None
    WORD_CAT.clear()
    for r in bucket_rows:
        WORD_CAT[r["label"]] = r["category"]
    freq = {r["label"]: r["count"] for r in bucket_rows}
    wc = WordCloud(
        font_path=font_path,
        width=1920,
        height=1080,
        background_color=bg_color,
        prefer_horizontal=0.9,
        max_font_size=340,
        min_font_size=18,
        relative_scaling=0.5,
        margin=8,
        collocations=False,
        color_func=color_func,
        random_state=42,
    )
    wc.generate_from_frequencies(freq)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wc.to_file(str(out_path))
    return {"path": out_path, "n_words": len(freq), "total": sum(freq.values())}


def main():
    ap = argparse.ArgumentParser(description="03 고객 분석 워드클라우드 generic 빌더")
    ap.add_argument("--csv", default=str(DEFAULT_CSV), help="빈도 CSV 경로")
    ap.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR), help="PNG 저장 폴더")
    ap.add_argument("--brand-brief", default=str(DEFAULT_BRAND_BRIEF), help="컬러 팔레트 추출용 brand_brief.md")
    ap.add_argument("--font", default=FONT_PATH, help="한글 폰트 경로")
    args = ap.parse_args()

    csv_path = pathlib.Path(args.csv)
    out_dir = pathlib.Path(args.out_dir)
    brand_brief = pathlib.Path(args.brand_brief)

    if not csv_path.exists():
        sys.exit(f"[ERROR] 빈도 CSV 없음: {csv_path}\n"
                 f"        03_customer/visuals/wordcloud_frequency.csv 를 먼저 생성하세요 (Step 6.5).")

    try:
        from wordcloud import WordCloud  # noqa: F401
    except ImportError:
        sys.exit("[ERROR] wordcloud 미설치.\n"
                 "        pip install wordcloud matplotlib")

    colors = load_brand_colors(brand_brief)
    bg = colors["BG-Light"]
    rows = load_frequency_csv(csv_path)
    if not rows:
        sys.exit(f"[ERROR] 빈도 CSV 가 비어있음: {csv_path}")

    print(f"브랜드 컬러: BG={bg}  Signature={colors['BRAND-Signature']}  TEXT={colors['TEXT-Primary']}")
    print(f"빈도 CSV: {csv_path} ({len(rows)} 행)")

    out_paths = []
    for bucket, suffix, color_func in [
        ("pain", "pain_wordcloud.png", color_func_pain(colors)),
        ("desire", "desire_wordcloud.png", color_func_desire(colors)),
        ("trend", "trend_wordcloud.png", color_func_trend(colors)),
    ]:
        result = build_one(rows, bucket, color_func, bg, args.font, out_dir / suffix)
        if result is None:
            print(f"  [{bucket:6}] 항목 없음 — 스킵")
            continue
        rel = result["path"].relative_to(ROOT)
        print(f"  [{bucket:6}] {result['n_words']} 단어 · 총 멘션 {result['total']} → {rel}")
        out_paths.append(result["path"])

    if not out_paths:
        sys.exit("[ERROR] 생성된 워드클라우드 없음 — 빈도 CSV bucket 컬럼 확인 (pain/desire/trend).")

    print(f"\n완료. {len(out_paths)} 개 PNG 저장.")


if __name__ == "__main__":
    main()

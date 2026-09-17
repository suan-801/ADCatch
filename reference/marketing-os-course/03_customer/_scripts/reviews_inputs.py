#!/usr/bin/env python3
"""고객 분석 PDP URL 통합 입력 파일 파서.

입력
  03_customer/_inputs/reviews_pdp.md

섹션 헤딩으로 자사·경쟁사·트렌드 시드 자동 분류:
  ## 자사 PDP            → our_pdps
  ## 경쟁사 PDP          → competitor_pdps
  ## 카테고리·트렌드 시드 → trend_seeds

사용 (다른 스크립트에서)
  from reviews_inputs import load_inputs, INPUTS_PATH
  inputs = load_inputs()
  # inputs = {
  #   "our_pdps": [{"url": "...", "note": "...", "is_oliveyoung": bool, "goods_no": "..."}],
  #   "competitor_pdps": [...],
  #   "trend_seeds": ["비건 카로틴 광채 세럼", ...],
  # }

본 모듈은 02 의 `competitor_inputs.py` 와 동일한 패턴 — Less is More 원칙 유지.
"""

import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parents[2]   # Claudecode_MarketingOS_student/
INPUTS_DIR = ROOT / "03_customer" / "_inputs"
INPUTS_PATH = INPUTS_DIR / "reviews_pdp.md"

_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_URL_RE = re.compile(r"https?://[^\s<>\"'`)\]]+")
_GOODS_NO_RE = re.compile(r"goodsNo=([A-Z0-9]+)", re.IGNORECASE)

_SECTION_ALIASES = {
    "자사 pdp": "our_pdps",
    "자사pdp": "our_pdps",
    "our pdp": "our_pdps",
    "경쟁사 pdp": "competitor_pdps",
    "경쟁사pdp": "competitor_pdps",
    "competitor pdp": "competitor_pdps",
    "카테고리·트렌드 시드": "trend_seeds",
    "카테고리 트렌드 시드": "trend_seeds",
    "트렌드 시드": "trend_seeds",
    "trend seeds": "trend_seeds",
}


def _strip_section_modifier(title):
    """`## 자사 PDP (만족 포인트 분석)` → `자사 pdp`."""
    base = re.sub(r"\(.*?\)", "", title).strip().lower()
    base = re.sub(r"\s+", " ", base)
    return base


def _split_sections(text):
    """본문을 `## 헤딩` 단위로 분해."""
    matches = list(_SECTION_RE.finditer(text))
    sections = {}
    for i, m in enumerate(matches):
        key = _SECTION_ALIASES.get(_strip_section_modifier(m.group(1)))
        if not key:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sections[key] = text[start:end].strip()
    return sections


def _parse_url_block(block):
    """URL 블록에서 URL + 메모 추출.

    포맷:
      https://...   # 메모 (선택)
    빈 줄·인라인 주석은 무시. URL 라인 맨 앞 `#` 은 비활성화.
    """
    items = []
    for raw in block.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # 라인이 `#` 으로 시작하면 — 일반 주석 또는 비활성화된 URL
        stripped = line.lstrip()
        if stripped.startswith("#"):
            # 비활성화 URL 도 스킵 (사용자가 의도적으로 막은 것)
            continue
        # URL 추출
        url_match = _URL_RE.search(line)
        if not url_match:
            continue
        url = url_match.group(0)
        # URL 뒤 `# 메모`
        tail = line[url_match.end():].strip()
        note = tail.lstrip("#").strip() if tail.startswith("#") else ""
        # 올영 PDP 여부 + goodsNo
        is_oy = "oliveyoung.co.kr" in url
        gno_match = _GOODS_NO_RE.search(url)
        goods_no = gno_match.group(1) if gno_match else ""
        items.append({
            "url": url,
            "note": note,
            "is_oliveyoung": is_oy,
            "goods_no": goods_no,
        })
    return items


def _parse_text_block(block):
    """트렌드 시드 블록 — 라인별 텍스트 (URL 없음). 빈 줄·`#` 시작 라인 무시."""
    items = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        items.append(line)
    return items


def load_inputs(path=None):
    """`reviews_pdp.md` 파싱.

    반환값:
      {
        "our_pdps": [...],
        "competitor_pdps": [...],
        "trend_seeds": [...],
        "source_path": str,
      }
    파일이 없으면 빈 구조 반환 (예외 ❌).
    """
    p = pathlib.Path(path) if path else INPUTS_PATH
    empty = {"our_pdps": [], "competitor_pdps": [], "trend_seeds": [], "source_path": str(p)}
    if not p.exists():
        return empty

    text = p.read_text(encoding="utf-8")
    sections = _split_sections(text)
    return {
        "our_pdps":        _parse_url_block(sections.get("our_pdps", "")),
        "competitor_pdps": _parse_url_block(sections.get("competitor_pdps", "")),
        "trend_seeds":     _parse_text_block(sections.get("trend_seeds", "")),
        "source_path":     str(p),
    }


if __name__ == "__main__":
    import json
    out = load_inputs()
    print(json.dumps(out, ensure_ascii=False, indent=2))

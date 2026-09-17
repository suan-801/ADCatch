#!/usr/bin/env python3
"""
cro_report — Clarity 데이터로 CRO 마크다운 리포트 1페이지 생성.

호출 예산: 일 10회 한도 / 본 스크립트 ≤ 4회.
- 1회: trend (no dimension)
- 1회: dimension1=URL (TOP 페이지 페인)
- (옵션) 1회: dimension1=Source
- (옵션) 1회: list-session-recordings (별도 REST/MCP)

--dry-run: API 호출 ❌, mock 데이터로 템플릿만 검증.

사용:
  python3 cro_report.py --brand sample_brand --period 7d
  python3 cro_report.py --brand sample_brand --period 7d --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from jinja2 import Environment, FileSystemLoader

from lib.env_loader import load_env
from lib.clarity_client import (
    call as clarity_call,
    remaining_quota,
    _read_count,
    _to_int,
    _to_float,
    _metric,
    _sessions_with,
)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
OUTPUTS = ROOT.parent / "11_dashboard" / "cro"

# 임계값 (CRO 인사이트 규칙을 코드화)
THRESHOLDS = {
    "rage":     {"red": 10.0, "yellow": 5.0},
    "dead":     {"red": 15.0, "yellow": 10.0},
    "scroll":   {"red": 35.0, "yellow": 25.0},
    "quickback":{"red": 25.0, "yellow": 15.0},
}


def light(pct: float, metric: str) -> str:
    t = THRESHOLDS[metric]
    if pct >= t["red"]:
        return "🔴"
    if pct >= t["yellow"]:
        return "🟡"
    return "🟢"


def note_for(metric: str, pct: float) -> str:
    if pct >= THRESHOLDS[metric]["red"]:
        return {
            "rage": "클릭 가능해 보이는 비클릭 요소 다수",
            "dead": "비반응 컨트롤 — JS 에러 또는 broken link 의심",
            "scroll": "스캐닝 패턴 과다 — CTA 위치 재검토",
            "quickback": "LP 첫인상 mismatch — 광고/LP sync 필요",
        }[metric]
    if pct >= THRESHOLDS[metric]["yellow"]:
        return "주의 — 추세 관찰"
    return "양호"


def trend_block(payload: list) -> dict:
    total_sessions = _to_int((_metric(payload, "Traffic") or {}).get("totalSessionCount", 0))
    if total_sessions == 0:
        total_sessions = 1  # 0 나눗셈 방지

    def pct(name: str) -> float:
        v = _sessions_with(payload, name)
        return v / total_sessions * 100

    rage_pct = pct("RageClickCount")
    dead_pct = pct("DeadClickCount")
    scroll_pct = pct("ExcessiveScroll")
    quickback_pct = pct("QuickbackClick")

    summary_parts = []
    for k, p in [("rage", rage_pct), ("dead", dead_pct),
                 ("scroll", scroll_pct), ("quickback", quickback_pct)]:
        if p >= THRESHOLDS[k]["red"]:
            summary_parts.append(f"{k} {p:.1f}% (red)")
    summary = (
        f"위험 {len(summary_parts)}건 — " + ", ".join(summary_parts)
        if summary_parts else "주요 메트릭 모두 양호 — 신규 A/B 1세트 권장"
    )

    return {
        "sessions": _to_int((_metric(payload, "Traffic") or {}).get("totalSessionCount", 0)),
        "rage_pct": rage_pct,     "rage_note": note_for("rage", rage_pct),
        "dead_pct": dead_pct,     "dead_note": note_for("dead", dead_pct),
        "scroll_pct": scroll_pct, "scroll_note": note_for("scroll", scroll_pct),
        "quickback_pct": quickback_pct, "quickback_note": note_for("quickback", quickback_pct),
        "summary": summary,
    }


def pages_block(payload_url: list, top_n: int = 5) -> list[dict]:
    """dimension1=URL 페이로드에서 TOP N 페인 페이지 추출."""
    rows: dict[str, dict] = {}
    for m in payload_url:
        name = m.get("metricName", "")
        for info in m.get("information") or []:
            url = info.get("Url") or info.get("URL") or info.get("url") or ""
            if not url:
                continue
            row = rows.setdefault(url, {"url": url, "sessions": 0,
                                        "rage_pct": 0.0, "dead_pct": 0.0,
                                        "scroll_pct": 0.0, "quickback_pct": 0.0})
            sess = _to_int(info.get("sessionsCount", 0))
            row["sessions"] = max(row["sessions"], sess)
            pct = _to_float(info.get("sessionsWithMetricPercentage", 0))
            if name == "RageClickCount": row["rage_pct"] = pct
            elif name == "DeadClickCount": row["dead_pct"] = pct
            elif name == "ExcessiveScroll": row["scroll_pct"] = pct
            elif name == "QuickbackClick": row["quickback_pct"] = pct
    out = []
    for r in rows.values():
        labels = []
        if r["rage_pct"] >= 10: labels.append("rage 위험")
        if r["dead_pct"] >= 15: labels.append("dead 위험")
        if r["scroll_pct"] >= 35: labels.append("스크롤 과다")
        if r["quickback_pct"] >= 25: labels.append("즉시이탈")
        r["label"] = " · ".join(labels) or "관찰"
        score = r["rage_pct"] + r["dead_pct"] + r["scroll_pct"] * 0.5 + r["quickback_pct"]
        r["_score"] = score
        out.append(r)
    out.sort(key=lambda x: (-x["_score"], -x["sessions"]))
    return out[:top_n]


def hypotheses_from(trend: dict, pages: list[dict]) -> list[dict]:
    """CRO 인사이트 규칙 표를 코드화. 최대 3개."""
    h: list[dict] = []

    if trend["quickback_pct"] >= THRESHOLDS["quickback"]["red"]:
        h.append({
            "title": "광고-LP 첫인상 mismatch",
            "evidence": f"quick_back {trend['quickback_pct']:.1f}% (red), 광고 클릭 후 30초 이내 이탈 다수",
            "hypothesis": "광고 1단 카피·hero 비주얼과 LP 헤더가 동일 메시지를 전달하지 못함",
            "action": "LP 헤더 카피 = 광고 1단 그대로 sync. hero 이미지 = 광고 메인컷 재사용",
            "validation": "LP 패치 후 7일 quick_back 추이, Meta CTR 동일 가정시 ROAS 비교",
            "linked_skill": "/08-landing-page (LP 패치) 또는 /05-ad-image-nanobanana (광고 카피 수정)",
        })

    if trend["rage_pct"] >= THRESHOLDS["rage"]["red"]:
        target = pages[0]["url"] if pages else "메인 페이지"
        h.append({
            "title": "클릭 가능해 보이는 비클릭 요소",
            "evidence": f"rage_click {trend['rage_pct']:.1f}% (red), TOP 페인 페이지 `{target}`",
            "hypothesis": "제품 카드·텍스트·이미지가 링크처럼 보이지만 정적 — 사용자 좌절",
            "action": "해당 페이지 reactive 요소 검수 → 명시 CTA 버튼화 + 카드 전체 영역 클릭 가능",
            "validation": "Clarity 세션 녹화로 페인 위치 확인 + 패치 후 rage% 추이",
            "linked_skill": "/08-landing-page (LP 패치)",
        })

    if trend["dead_pct"] >= THRESHOLDS["dead"]["red"]:
        h.append({
            "title": "비반응 컨트롤 (JS 에러 의심)",
            "evidence": f"dead_click {trend['dead_pct']:.1f}% (red)",
            "hypothesis": "form submit 또는 옵션 선택 버튼이 반응하지 않거나 시각 피드백 부재",
            "action": "콘솔 에러 확인 + 로딩 스피너/disabled 상태 시각화 추가",
            "validation": "패치 후 dead% 추이 + Clarity 녹화 표본",
            "linked_skill": "프론트엔드 패치 (OS_v1 범위 외)",
        })

    if trend["scroll_pct"] >= THRESHOLDS["scroll"]["red"]:
        h.append({
            "title": "스캐닝 패턴 과다 — CTA 위치 재검토",
            "evidence": f"excessive_scroll {trend['scroll_pct']:.1f}% (red)",
            "hypothesis": "핵심 CTA 또는 가치 제안이 fold 아래에 있어 사용자가 빠르게 훑음",
            "action": "first viewport 에 1차 CTA + H2 헤더로 섹션 가시화",
            "validation": "패치 후 scroll% 추이 + 평균 세션 길이",
            "linked_skill": "/08-landing-page (LP 재배치)",
        })

    if not h:
        h.append({
            "title": "주요 메트릭 양호 — 신규 A/B 1세트",
            "evidence": "rage/dead/scroll/quickback 모두 yellow 이하",
            "hypothesis": "현재 LP 가 안정. 더 큰 개선은 신규 비주얼·카피 실험 필요",
            "action": "07 카드뉴스 또는 05 광고 이미지 1세트 신규 제작 → A/B",
            "validation": "신규 vs 기존 CTR · ROAS · quickback 비교",
            "linked_skill": "/05-ad-image-nanobanana 또는 /07-carousel-nanobanana",
        })

    return h[:3]


def next_actions_from(hypotheses: list[dict], trend: dict) -> list[dict]:
    actions = []
    for h in hypotheses[:2]:
        actions.append({
            "priority_label": "[우선]",
            "title": h["title"],
            "detail": h["action"],
        })
    if trend["sessions"] < 100:
        actions.append({
            "priority_label": "[관찰]",
            "title": "표본 부족",
            "detail": f"세션 {trend['sessions']}건 — 결론 신뢰도 낮음. 7일 더 누적 후 재실행 권장.",
        })
    actions.append({
        "priority_label": "[정기]",
        "title": "다음 CRO 리포트",
        "detail": "주 1회 (Clarity 호출 4회 예산) — 가설 검증 + 신규 페인 발굴",
    })
    return actions


def mock_payload_trend() -> list:
    """--dry-run / Clarity 미연동 시 사용. CRO 인사이트 규칙 시나리오."""
    return [
        {"metricName": "Traffic", "information": [{"totalSessionCount": "1240", "totalBotSessionCount": "12"}]},
        {"metricName": "RageClickCount", "information": [{"sessionsCount": "1240", "sessionsWithMetricPercentage": "12.3"}]},
        {"metricName": "DeadClickCount", "information": [{"sessionsCount": "1240", "sessionsWithMetricPercentage": "8.4"}]},
        {"metricName": "ExcessiveScroll", "information": [{"sessionsCount": "1240", "sessionsWithMetricPercentage": "29.1"}]},
        {"metricName": "QuickbackClick", "information": [{"sessionsCount": "1240", "sessionsWithMetricPercentage": "27.5"}]},
    ]


def mock_payload_url() -> list:
    """URL 차원 mock — [브랜드명] 자사몰 PDP/홈 시나리오."""
    return [
        {"metricName": "RageClickCount", "information": [
            {"Url": "/products/summer-tester", "sessionsCount": "420", "sessionsWithMetricPercentage": "18.2"},
            {"Url": "/", "sessionsCount": "510", "sessionsWithMetricPercentage": "9.0"},
            {"Url": "/cart", "sessionsCount": "120", "sessionsWithMetricPercentage": "22.5"},
        ]},
        {"metricName": "DeadClickCount", "information": [
            {"Url": "/products/summer-tester", "sessionsCount": "420", "sessionsWithMetricPercentage": "11.8"},
            {"Url": "/cart", "sessionsCount": "120", "sessionsWithMetricPercentage": "19.0"},
        ]},
        {"metricName": "ExcessiveScroll", "information": [
            {"Url": "/products/summer-tester", "sessionsCount": "420", "sessionsWithMetricPercentage": "38.0"},
        ]},
        {"metricName": "QuickbackClick", "information": [
            {"Url": "/products/summer-tester", "sessionsCount": "420", "sessionsWithMetricPercentage": "31.0"},
            {"Url": "/", "sessionsCount": "510", "sessionsWithMetricPercentage": "16.0"},
        ]},
    ]


def render(args, trend: dict, pages: list[dict], dry_run: bool, calls_used: int) -> str:
    env_j = Environment(
        loader=FileSystemLoader(str(TEMPLATES)),
        trim_blocks=True, lstrip_blocks=True,
    )
    tmpl = env_j.get_template("cro_report.md.j2")

    today = date.today()
    until = today
    since = until - timedelta(days=int(args.period.rstrip("d")) - 1)
    period_label = args.period

    hypotheses = hypotheses_from(trend, pages)
    next_actions = next_actions_from(hypotheses, trend)

    source_note = "Clarity API live" if not dry_run else "Clarity dry-run (mock data)"

    return tmpl.render(
        brand=args.brand,
        brand_display=args.brand.upper(),
        period_label=period_label,
        since=since.isoformat(),
        until=until.isoformat(),
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M KST"),
        clarity_calls_used=calls_used,
        source_note=source_note,
        trend=trend,
        pages=pages,
        ad_lp_mapping=[],  # Phase 2: Source 차원 호출 추가
        hypotheses=hypotheses,
        sessions=[],       # Phase 2: list-session-recordings MCP 연동
        next_actions=next_actions,
        light=light,
    )


def next_version(folder: Path, base: str) -> int:
    n = 1
    while (folder / f"{base}-cro-v{n}.md").exists():
        n += 1
    return n


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--brand", default="sample_brand")
    p.add_argument("--period", default="7d", choices=["1d", "3d", "7d"])
    p.add_argument("--top-urls", type=int, default=5)
    p.add_argument("--dry-run", action="store_true",
                   help="Clarity API 호출 ❌, mock 데이터로 템플릿 검증만")
    p.add_argument("--skip-url-dim", action="store_true",
                   help="URL 차원 호출 skip — trend 1회만 사용 (호출 예산 절약)")
    args = p.parse_args()

    env = load_env()
    token = env.get("CLARITY_API_TOKEN")

    num_days = int(args.period.rstrip("d"))
    if num_days > 3:
        # Clarity API 는 numOfDays ≤ 3. 7d 요청 시 3d 로 캡 + 표시는 7d 유지 (트렌드 근사)
        api_days = 3
    else:
        api_days = num_days

    dry_run = args.dry_run or not token
    if dry_run and not args.dry_run:
        print("  ⚠️ CLARITY_API_TOKEN 미설정 — dry-run 모드로 전환")
    print(f"▶ cro_report — brand={args.brand} period={args.period} dry_run={dry_run}")

    if dry_run:
        trend_payload = mock_payload_trend()
        url_payload = mock_payload_url()
        calls_used = 0
    else:
        before = _read_count()
        rem = remaining_quota()
        if rem < 2:
            print(f"  ⚠️ Clarity 잔여 호출 {rem}회 < 필요 2회. dry-run 으로 전환.")
            dry_run = True
            trend_payload = mock_payload_trend()
            url_payload = mock_payload_url()
            calls_used = 0
        else:
            print(f"  ✓ Clarity 잔여 호출 {rem}회")
            trend_payload = clarity_call(token, num_of_days=api_days,
                                         reason="cro-trend", reserve_for_cro=False)
            print("  ✓ Clarity trend 호출")
            if args.skip_url_dim or remaining_quota() < 1:
                url_payload = []
                print("  ⚠️ URL 차원 호출 skip")
            else:
                url_payload = clarity_call(token, num_of_days=api_days,
                                           dimension1="URL", reason="cro-url",
                                           reserve_for_cro=False)
                print("  ✓ Clarity URL 차원 호출")
            calls_used = _read_count() - before

    trend = trend_block(trend_payload)
    pages = pages_block(url_payload, top_n=args.top_urls) if url_payload else []

    md = render(args, trend, pages, dry_run, calls_used)

    folder = OUTPUTS / args.brand
    folder.mkdir(parents=True, exist_ok=True)
    iso = date.today().isocalendar()
    base = f"{iso.year}-W{iso.week:02d}"
    v = next_version(folder, base)
    md_path = folder / f"{base}-cro-v{v}.md"
    md_path.write_text(md, encoding="utf-8")
    print(f"  📄 CRO 마크다운: {md_path.relative_to(ROOT)}")
    print(f"     trend: rage={trend['rage_pct']:.1f}% dead={trend['dead_pct']:.1f}% "
          f"scroll={trend['scroll_pct']:.1f}% quickback={trend['quickback_pct']:.1f}%")
    print(f"     pages: {len(pages)}, hypotheses: {len(hypotheses_from(trend, pages))}, "
          f"calls_used: {calls_used}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

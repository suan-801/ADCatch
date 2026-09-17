"""룰베이스 AI 액션 제안 엔진 — Overview 대시보드 §7.

설계 원칙:
  - 외부 API 호출 ❌ (Claude/OpenAI 등). 룰만으로 결정 가능
  - brand_kpi.yml 임계값/목표값 + ETL 데이터 비교로 트리거
  - 우선순위: critical > high > med > low
  - 결과는 outputs/recommendations/{brand}/{date}.json 으로 dump

룰 카탈로그 (8개, 확장 가능):
  R1 ROAS_RED          critical  ROAS < red_at + spend 충분 → 캠페인 일시중지 검토
  R2 CPA_RED_RISING    high      CPA > cpa_red AND 7일 추세 ↑
  R3 CTR_LOW           high      CTR < red_pct
  R4 CLARITY_RAGE      high      Rage Click Δ > 50%
  R5 ORGANIC_DROP      med       신규유저 ↓ AND Organic 세션 ↓
  R6 REVENUE_PACING    high      월 매출 페이싱 < 80%
  R7 AD_FATIGUE        med       광고 freshness > 14일 AND CTR ↓
  R8 NPAY_GAP          low       GA4 conversions < (meta purchases) — 이벤트 합산 점검
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import date
from typing import Any

PRIORITY_ORDER = {"critical": 0, "high": 1, "med": 2, "low": 3}


@dataclass
class Recommendation:
    id: str
    priority: str           # critical | high | med | low
    emoji: str              # 카드 머리 이모지
    title: str              # 친근체 한 줄
    why: str                # "왜 이 제안인지" — 데이터 근거
    action: str             # "이렇게 해보세요" — 실행 액션
    link_skill: str = ""    # 클릭 시 가이드할 슬래시 스킬 (옵션)
    evidence: dict = field(default_factory=dict)  # {metric, value, threshold}


def _trend_direction(series: list[float]) -> str:
    """간단 추세 — 후반 절반 평균 vs 전반 절반 평균."""
    if len(series) < 2:
        return "flat"
    mid = len(series) // 2
    first = sum(series[:mid]) / max(mid, 1)
    last = sum(series[mid:]) / max(len(series) - mid, 1)
    if first == 0:
        return "up" if last > 0 else "flat"
    delta = (last - first) / abs(first)
    if delta > 0.10:
        return "up"
    if delta < -0.10:
        return "down"
    return "flat"


def run(*, meta_daily: list[dict], ga4_daily: list[dict], ga4_channel: list[dict],
        meta_breakdowns: list[dict], clarity_daily: list[dict] | None,
        thresholds, targets, target_date: date, revenue_mtd: float,
        purchases_mtd: float, days_into_month: int, days_in_month: int) -> list[Recommendation]:
    """모든 룰을 평가해 트리거된 제안만 반환. 우선순위 정렬."""
    out: list[Recommendation] = []
    last = meta_daily[-1] if meta_daily else {}
    last_ga4 = ga4_daily[-1] if ga4_daily else {}

    spend = float(last.get("spend") or 0)
    roas = float(last.get("roas") or 0)
    ctr = float(last.get("ctr") or 0)
    cpa = float(last.get("cpa") or 0)
    meta_purchases = float(last.get("purchases") or 0)

    # ─ R1: ROAS 빨강 ─
    if spend > thresholds.spend_min and roas < thresholds.roas_red and roas > 0:
        out.append(Recommendation(
            id="R1_ROAS_RED",
            priority="critical",
            emoji="🚨",
            title=f"ROAS {roas:.2f} — 빨강이에요",
            why=f"어제 {int(spend):,}원 쓰고 ROAS {roas:.2f} (빨강선 {thresholds.roas_red}). 이대로면 돈이 새요.",
            action="가장 안 좋은 캠페인 1개를 일시중지하고, 나머지에 예산 몰아주는 게 좋아요.",
            link_skill="",
            evidence={"metric": "roas", "value": roas, "threshold": thresholds.roas_red},
        ))

    # ─ R2: CPA 빨강 + 추세 상승 ─
    cpa_series = [float(r.get("cpa") or 0) for r in meta_daily[-7:] if r.get("cpa")]
    if cpa > thresholds.cpa_red and _trend_direction(cpa_series) == "up":
        out.append(Recommendation(
            id="R2_CPA_RISING",
            priority="high",
            emoji="📈",
            title=f"CPA {int(cpa):,}원 — 점점 비싸지고 있어요",
            why=f"빨강선({int(thresholds.cpa_red):,}원)을 넘었고, 7일 추세도 ↑. 한 명 데려오는 비용이 계속 오르는 중.",
            action="입찰가를 낮추거나, 후킹 약한 소재를 v2로 교체해보세요.",
            link_skill="/05-ad-image-nanobanana",
            evidence={"metric": "cpa", "value": cpa, "threshold": thresholds.cpa_red},
        ))

    # ─ R3: CTR 낮음 ─
    if ctr > 0 and ctr < thresholds.ctr_red_pct:
        out.append(Recommendation(
            id="R3_CTR_LOW",
            priority="high",
            emoji="🪝",
            title=f"CTR {ctr:.2f}% — 후킹이 약해요",
            why=f"CTR 빨강선 {thresholds.ctr_red_pct}% 미만. 사람들이 광고를 보고 클릭을 안 해요.",
            action="메시지 앵글을 더 강한 페인포인트로 바꾼 v2 소재를 만들어볼까요?",
            link_skill="/05-ad-image-nanobanana",
            evidence={"metric": "ctr", "value": ctr, "threshold": thresholds.ctr_red_pct},
        ))

    # ─ R4: Clarity Rage Click 급증 ─
    if clarity_daily and len(clarity_daily) >= 2:
        rages = [float(r.get("rage_clicks") or 0) for r in clarity_daily]
        sessions_c = [float(r.get("sessions") or 1) for r in clarity_daily]
        rage_pct = [r / s * 100 if s else 0 for r, s in zip(rages, sessions_c)]
        if len(rage_pct) >= 2:
            base = sum(rage_pct[:-1]) / max(len(rage_pct) - 1, 1)
            today = rage_pct[-1]
            if base > 0 and today > base * 1.5:
                out.append(Recommendation(
                    id="R4_CLARITY_RAGE",
                    priority="high",
                    emoji="😡",
                    title=f"Rage Click {today:.1f}% — 평소보다 많이 짜증내고 있어요",
                    why=f"직전 평균 {base:.1f}% → 오늘 {today:.1f}% (+{(today/base-1)*100:.0f}%). UX 어디가 막혔어요.",
                    action="Clarity 세션 녹화·페인 페이지로 이탈 원인을 찾아보세요.",
                    link_skill="",
                    evidence={"metric": "rage_click_pct", "value": today, "threshold": base * 1.5},
                ))

    # ─ R5: Organic 세션 + 신규유저 동반 하락 ─
    if ga4_daily and len(ga4_daily) >= 4:
        new_series = [float(r.get("new_users") or 0) for r in ga4_daily]
        if _trend_direction(new_series) == "down":
            organic_sessions = sum(
                float(r.get("sessions") or 0) for r in ga4_channel
                if (r.get("channel_group") or "").lower().startswith("organic")
            )
            if organic_sessions < 20:  # 임의 룩
                out.append(Recommendation(
                    id="R5_ORGANIC_DROP",
                    priority="med",
                    emoji="🌱",
                    title="신규유저가 줄고 있어요 — Organic 도 약해요",
                    why=f"7일 신규유저 추세 ↓ + Organic 세션 {int(organic_sessions)}건. 광고 채널만 의존하면 위험해요.",
                    action="네이버 블로그·콘텐츠 시드 5건 발행을 검토해보세요.",
                    link_skill="",
                    evidence={"metric": "new_users_trend", "value": "down", "threshold": "stable"},
                ))

    # ─ R6: 월 매출 페이싱 < 80% ─
    if targets.monthly_revenue_goal > 0 and days_in_month > 0:
        expected_pct = days_into_month / days_in_month
        actual_pct = revenue_mtd / targets.monthly_revenue_goal
        pacing = (actual_pct / expected_pct) if expected_pct > 0 else 0
        if pacing < 0.80:
            shortfall = targets.monthly_revenue_goal - revenue_mtd
            out.append(Recommendation(
                id="R6_REVENUE_PACING",
                priority="high",
                emoji="🚀",
                title=f"월 매출 페이싱 {int(pacing*100)}% — 살짝 부족해요",
                why=f"오늘까지 {int(revenue_mtd):,}원 (목표 {int(targets.monthly_revenue_goal):,}원 대비 {int(actual_pct*100)}%). 이 속도면 {int(shortfall):,}원 부족할 수 있어요.",
                action="베스트 캠페인 일예산 +20% 시뮬레이션을 해보세요.",
                link_skill="",
                evidence={"metric": "revenue_pacing", "value": pacing, "threshold": 0.80},
            ))

    # ─ R7: 광고 피로 (freshness 14일+ AND CTR 하락) ─
    if meta_breakdowns:
        ads = [r for r in meta_breakdowns if r.get("level") == "ad"]
        for r in ads[:5]:  # Top 5 만 검사
            ad_name = r.get("ad_name", "")
            ad_ctr = float(r.get("ctr") or 0)
            # freshness 는 t1/t2/t3 단계만 있어 직접 일수 추정 불가 — ad 명에서 yymmdd 추출 시도
            if not ad_name or ad_ctr == 0:
                continue
            # meta008_260327_hj 같은 패턴에서 260327 = 2026-03-27
            import re
            m = re.search(r"_(\d{6})_", ad_name)
            if not m:
                continue
            try:
                yy, mm, dd = int(m.group(1)[:2]), int(m.group(1)[2:4]), int(m.group(1)[4:])
                ad_date = date(2000 + yy, mm, dd)
                age_days = (target_date - ad_date).days
                if age_days > 14 and ad_ctr < thresholds.ctr_red_pct:
                    out.append(Recommendation(
                        id=f"R7_AD_FATIGUE_{ad_name}",
                        priority="med",
                        emoji="😴",
                        title=f"{ad_name} 피로해 보여요",
                        why=f"{age_days}일 됐고 CTR {ad_ctr:.2f}% (빨강선 {thresholds.ctr_red_pct}% 미만). 광고 피로 시작.",
                        action="v2 소재를 만들어 교체해볼까요?",
                        link_skill="/05-ad-image-nanobanana",
                        evidence={"metric": "ad_age_days", "value": age_days, "threshold": 14},
                    ))
                    break  # 한 번에 한 개만 (중복 방지)
            except (ValueError, IndexError):
                continue

    # ─ R8: 카페24+네이버페이 합산 누락 의심 ─
    ga4_conv = float(last_ga4.get("conversions") or 0)
    if meta_purchases > 0 and ga4_conv > 0 and ga4_conv < meta_purchases * 0.5:
        out.append(Recommendation(
            id="R8_NPAY_GAP",
            priority="low",
            emoji="🔍",
            title=f"GA4 구매({int(ga4_conv)}) vs Meta 구매({int(meta_purchases)}) — 차이가 커요",
            why="카페24 + 네이버페이 분리 결제 이벤트 합산 누락 가능성. (purchase + click_npay_purchase) 합산 필요.",
            action="GA4 conversions 설정에서 두 이벤트를 OR 로 묶었는지 확인해보세요.",
            link_skill="",
            evidence={"metric": "ga4_vs_meta_purchases", "value": ga4_conv, "threshold": meta_purchases * 0.5},
        ))

    out.sort(key=lambda r: PRIORITY_ORDER.get(r.priority, 99))
    return out


def to_jsonable(recs: list[Recommendation]) -> list[dict]:
    return [asdict(r) for r in recs]

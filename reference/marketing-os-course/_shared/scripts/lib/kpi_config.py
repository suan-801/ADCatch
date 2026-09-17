"""brand_kpi.yml 로더 + 신호등(🟢🟡🔴) 판정 헬퍼."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "brand_kpi.yml"


@dataclass
class Thresholds:
    roas_green: float
    roas_red: float
    ctr_red_pct: float
    cpa_red: float
    spend_min: float
    daily_budget: float | None = None

    @classmethod
    def from_dict(cls, d: dict) -> "Thresholds":
        return cls(
            roas_green=float(d.get("roas_green", 2.0)),
            roas_red=float(d.get("roas_red", 1.0)),
            ctr_red_pct=float(d.get("ctr_red_pct", 0.8)),
            cpa_red=float(d.get("cpa_red", 30000)),
            spend_min=float(d.get("spend_min", 10000)),
            daily_budget=float(d["daily_budget"]) if d.get("daily_budget") is not None else None,
        )


@dataclass
class Targets:
    """월/주 목표값 — Overview 달성률 계산용. brand_kpi.yml 의 sample_brand 키 하위."""
    kpi_period: str = "monthly"
    target_roas: float = 2.5
    target_cpa: float = 22000
    target_ctr_pct: float = 3.0
    monthly_revenue_goal: float = 0
    monthly_purchase_goal: float = 0

    @classmethod
    def from_dict(cls, d: dict) -> "Targets":
        return cls(
            kpi_period=str(d.get("kpi_period", "monthly")),
            target_roas=float(d.get("target_roas", 2.5)),
            target_cpa=float(d.get("target_cpa", 22000)),
            target_ctr_pct=float(d.get("target_ctr_pct", 3.0)),
            monthly_revenue_goal=float(d.get("monthly_revenue_goal", 0)),
            monthly_purchase_goal=float(d.get("monthly_purchase_goal", 0)),
        )


def load(brand: str = "sample_brand") -> Thresholds:
    if not CONFIG_PATH.exists():
        return Thresholds(roas_green=2.0, roas_red=1.0, ctr_red_pct=0.8, cpa_red=30000, spend_min=10000)
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return Thresholds.from_dict((data.get(brand) or {}))


def targets(brand: str = "sample_brand") -> Targets:
    """월/주 목표값 로더. 키가 없으면 안전한 디폴트 반환."""
    if not CONFIG_PATH.exists():
        return Targets()
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}
    return Targets.from_dict((data.get(brand) or {}))


def light(value: float, green_at: float, red_at: float, higher_is_better: bool = True) -> str:
    """🟢/🟡/🔴 — green_at 도달 시 🟢, red_at 미달 시 🔴."""
    if higher_is_better:
        if value >= green_at:
            return "🟢"
        if value < red_at:
            return "🔴"
        return "🟡"
    if value <= green_at:
        return "🟢"
    if value > red_at:
        return "🔴"
    return "🟡"

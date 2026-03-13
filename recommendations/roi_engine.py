"""
Staxx Intelligence — ROI Projection Engine

Given current monthly spend and swap recommendations, computes:
  - Total monthly / annual savings
  - % cost reduction
  - Break-even timeline vs Staxx subscription cost
  - 12-month savings projection with confidence bands
  - Waterfall chart data (original → per-task savings → new spend)

All computations are pure (no I/O).  The engine is designed to be
called after the RecommendationGenerator has already filtered cards
by risk tolerance.
"""

from __future__ import annotations

import math
from datetime import date, timedelta
from typing import NamedTuple

from pydantic import BaseModel, Field

from recommendations.generator import SwapCard

# ---------------------------------------------------------------------------
# Output schemas
# ---------------------------------------------------------------------------


class MonthlyDataPoint(BaseModel):
    """A single month in the 12-month savings projection."""

    month: str = Field(description="ISO-format month label, e.g. '2025-04'")
    cumulative_savings_usd: float
    cumulative_savings_lower: float = Field(description="95% CI lower bound")
    cumulative_savings_upper: float = Field(description="95% CI upper bound")
    remaining_cost_usd: float = Field(description="Projected spend after swap")


class WaterfallSegment(BaseModel):
    """One bar in the savings waterfall chart."""

    label: str
    value: float = Field(description="Dollar amount; positive = savings, negative = cost")
    category: str = Field(description="'original' | 'saving' | 'remaining'")
    task_type: str | None = None


class WaterfallData(BaseModel):
    """Full waterfall chart dataset."""

    segments: list[WaterfallSegment]
    total_original_usd: float
    total_savings_usd: float
    projected_spend_usd: float


class ROIProjection(BaseModel):
    """Complete ROI projection for an organisation."""

    org_id: str

    # --- Snapshot numbers ---
    original_monthly_cost_usd: float
    total_monthly_savings_usd: float
    annual_savings_usd: float
    cost_reduction_pct: float = Field(description="Percentage cost reduction (0–100)")
    projected_monthly_cost_usd: float

    # --- Staxx ROI ---
    staxx_subscription_usd: float = Field(
        description="Monthly Staxx subscription cost used for break-even"
    )
    break_even_months: float | None = Field(
        None,
        description="Months until cumulative savings exceed Staxx subscription cost. "
                    "None if savings are zero.",
    )

    # --- 12-month timeline ---
    monthly_projections: list[MonthlyDataPoint]

    # --- Waterfall ---
    waterfall: WaterfallData

    # --- Active card ids used for this projection ---
    included_card_ids: list[str]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class _TaskSavings(NamedTuple):
    task_type: str
    monthly_savings: float
    ci_lower: float
    ci_upper: float


def _aggregate_by_task(cards: list[SwapCard]) -> list[_TaskSavings]:
    """
    Aggregate approved swap cards by task_type, taking the best
    (highest-savings) card per (task_type, current_model) pair.

    Multiple candidate cards for the same task_type are summed only
    if they target different current_models; otherwise the best card wins.
    """
    # Key: (task_type, current_model) → best SwapCard by savings
    best: dict[tuple[str, str], SwapCard] = {}
    for card in cards:
        key = (card.task_type, card.current_model)
        if key not in best or card.monthly_savings_usd > best[key].monthly_savings_usd:
            best[key] = card

    # Aggregate across unique keys (same task_type, different current_models are additive)
    task_totals: dict[str, _TaskSavings] = {}
    for card in best.values():
        existing = task_totals.get(card.task_type)
        if existing is None:
            task_totals[card.task_type] = _TaskSavings(
                task_type=card.task_type,
                monthly_savings=card.monthly_savings_usd,
                ci_lower=card.monthly_savings_ci_lower,
                ci_upper=card.monthly_savings_ci_upper,
            )
        else:
            task_totals[card.task_type] = _TaskSavings(
                task_type=card.task_type,
                monthly_savings=existing.monthly_savings + card.monthly_savings_usd,
                # CIs add in quadrature (independent estimates)
                ci_lower=existing.ci_lower + card.monthly_savings_ci_lower,
                ci_upper=existing.ci_upper + card.monthly_savings_ci_upper,
            )

    return list(task_totals.values())


def _monthly_label(base: date, offset_months: int) -> str:
    """Return 'YYYY-MM' label for base + offset_months."""
    month = base.month - 1 + offset_months
    year = base.year + month // 12
    month = month % 12 + 1
    return f"{year}-{month:02d}"


def _build_monthly_projections(
    base_date: date,
    original_monthly_cost: float,
    monthly_savings: float,
    ci_lower: float,
    ci_upper: float,
    months: int = 12,
) -> list[MonthlyDataPoint]:
    """
    Build month-by-month cumulative savings projection.

    Assumes savings are realised starting from month 1 (i.e., swap is
    implemented at the beginning of month 1).
    """
    points: list[MonthlyDataPoint] = []
    for i in range(1, months + 1):
        cumulative = monthly_savings * i
        cum_lower = ci_lower * i
        cum_upper = ci_upper * i
        remaining = max(0.0, original_monthly_cost - monthly_savings)
        points.append(
            MonthlyDataPoint(
                month=_monthly_label(base_date, i),
                cumulative_savings_usd=round(cumulative, 2),
                cumulative_savings_lower=round(cum_lower, 2),
                cumulative_savings_upper=round(cum_upper, 2),
                remaining_cost_usd=round(remaining, 2),
            )
        )
    return points


def _build_waterfall(
    original_monthly_cost: float,
    task_savings: list[_TaskSavings],
) -> WaterfallData:
    """
    Build waterfall chart data.

    Structure:
      [Original spend] → [−Saving: task A] → [−Saving: task B] → [Remaining]
    """
    segments: list[WaterfallSegment] = [
        WaterfallSegment(
            label="Current Spend",
            value=round(original_monthly_cost, 2),
            category="original",
        )
    ]

    total_savings = 0.0
    for ts in sorted(task_savings, key=lambda x: x.monthly_savings, reverse=True):
        segments.append(
            WaterfallSegment(
                label=f"{ts.task_type} savings",
                value=round(-ts.monthly_savings, 2),
                category="saving",
                task_type=ts.task_type,
            )
        )
        total_savings += ts.monthly_savings

    projected = max(0.0, original_monthly_cost - total_savings)
    segments.append(
        WaterfallSegment(
            label="Projected Spend",
            value=round(projected, 2),
            category="remaining",
        )
    )

    return WaterfallData(
        segments=segments,
        total_original_usd=round(original_monthly_cost, 2),
        total_savings_usd=round(total_savings, 2),
        projected_spend_usd=round(projected, 2),
    )


class ROIEngine:
    """
    Pure-computation ROI projection engine.

    Usage::

        engine = ROIEngine(staxx_subscription_usd=299.0)
        projection = engine.project(
            org_id="abc",
            approved_cards=cards,
            original_monthly_cost=12400.0,
        )
    """

    def __init__(self, staxx_subscription_usd: float = 299.0) -> None:
        self.staxx_subscription_usd = staxx_subscription_usd

    def project(
        self,
        org_id: str,
        approved_cards: list[SwapCard],
        original_monthly_cost: float,
        base_date: date | None = None,
    ) -> ROIProjection:
        """
        Compute a full ROI projection for the given cards.

        Args:
            org_id: Organisation identifier.
            approved_cards: SwapCards with status "active" or "approved".
                            Cards are expected to be pre-filtered by risk
                            tolerance before being passed here.
            original_monthly_cost: Current total monthly LLM spend in USD.
            base_date: Starting date for the 12-month timeline (default: today).

        Returns:
            ROIProjection with all computed fields.
        """
        if base_date is None:
            base_date = date.today()

        task_savings = _aggregate_by_task(approved_cards)

        total_monthly_savings = sum(ts.monthly_savings for ts in task_savings)
        total_ci_lower = sum(ts.ci_lower for ts in task_savings)
        total_ci_upper = sum(ts.ci_upper for ts in task_savings)
        annual_savings = total_monthly_savings * 12

        cost_reduction_pct = (
            (total_monthly_savings / original_monthly_cost * 100)
            if original_monthly_cost > 0
            else 0.0
        )
        projected_monthly_cost = max(0.0, original_monthly_cost - total_monthly_savings)

        # Break-even: how many months until cumulative savings exceed Staxx subscription?
        if total_monthly_savings > 0:
            # Staxx subscription is a one-time monthly cost; break-even is fraction of month
            break_even_months = self.staxx_subscription_usd / total_monthly_savings
        else:
            break_even_months = None

        monthly_projections = _build_monthly_projections(
            base_date=base_date,
            original_monthly_cost=original_monthly_cost,
            monthly_savings=total_monthly_savings,
            ci_lower=total_ci_lower,
            ci_upper=total_ci_upper,
            months=12,
        )

        waterfall = _build_waterfall(original_monthly_cost, task_savings)

        return ROIProjection(
            org_id=org_id,
            original_monthly_cost_usd=round(original_monthly_cost, 2),
            total_monthly_savings_usd=round(total_monthly_savings, 2),
            annual_savings_usd=round(annual_savings, 2),
            cost_reduction_pct=round(cost_reduction_pct, 1),
            projected_monthly_cost_usd=round(projected_monthly_cost, 2),
            staxx_subscription_usd=self.staxx_subscription_usd,
            break_even_months=(
                round(break_even_months, 2) if break_even_months is not None else None
            ),
            monthly_projections=monthly_projections,
            waterfall=waterfall,
            included_card_ids=[c.id for c in approved_cards],
        )

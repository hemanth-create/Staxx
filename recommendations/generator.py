"""
Staxx Intelligence — Swap Recommendation Generator

Consumes ScoringResult objects from the Scoring Engine and produces
human-readable, customer-facing SwapCards grouped by task type.

Risk tolerance levels:
  conservative  → only STRONG_YES candidates
  moderate      → STRONG_YES + YES  (default)
  aggressive    → STRONG_YES + YES + MAYBE
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field

from scoring.schemas import ModelScore, ScoringResult

logger = logging.getLogger(__name__)

RiskTolerance = Literal["conservative", "moderate", "aggressive"]

_RISK_ALLOW_MAP: dict[RiskTolerance, frozenset[str]] = {
    "conservative": frozenset({"STRONG_YES"}),
    "moderate": frozenset({"STRONG_YES", "YES"}),
    "aggressive": frozenset({"STRONG_YES", "YES", "MAYBE"}),
}


class MetricsSummary(BaseModel):
    """Key metrics included in each swap card for dashboard display."""

    sample_size: int
    cost_savings_monthly_usd: float
    cost_savings_ci_lower: float
    cost_savings_ci_upper: float
    latency_p95_ms: float
    latency_delta_pct: float
    error_rate: float
    json_validity_rate: float | None
    output_consistency_cv: float
    topsis_score: float
    is_pareto_optimal: bool


class SwapCard(BaseModel):
    """
    A single actionable swap recommendation card.

    Designed for direct dashboard rendering — all display fields
    are pre-formatted strings alongside raw values for programmatic use.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    org_id: str
    task_type: str
    current_model: str
    recommended_model: str
    swap_recommendation: str  # STRONG_YES | YES | MAYBE
    confidence_pct: int = Field(ge=0, le=100)

    # Dollar amounts
    monthly_savings_usd: float
    annual_savings_usd: float
    monthly_savings_ci_lower: float
    monthly_savings_ci_upper: float
    original_monthly_cost_usd: float
    projected_monthly_cost_usd: float

    # Human-readable headline
    headline: str
    rationale: str

    # Full metrics block for detail view
    metrics: MetricsSummary

    generated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    status: str = "active"  # active | approved | dismissed


def _build_headline(
    task_type: str,
    current_model: str,
    recommended_model: str,
    monthly_savings: float,
    confidence_pct: int,
) -> str:
    return (
        f"Switch your {task_type} task from {current_model} → {recommended_model}. "
        f"Projected savings: ${monthly_savings:,.0f}/mo. "
        f"Confidence: {confidence_pct}%."
    )


def _build_rationale(
    score: ModelScore,
    original_monthly_cost: float,
) -> str:
    parts: list[str] = []

    savings_pct = (
        (score.cost_savings_monthly_usd / original_monthly_cost * 100)
        if original_monthly_cost > 0
        else 0.0
    )
    parts.append(
        f"Cost drops {savings_pct:.0f}% (${score.cost_savings_monthly_usd:,.0f}/mo "
        f"saved, 95% CI: ${score.cost_savings_ci_95[0]:,.0f}–${score.cost_savings_ci_95[1]:,.0f})."
    )

    latency_dir = "faster" if score.latency_delta_pct < 0 else "slower"
    parts.append(
        f"Latency is {abs(score.latency_delta_pct):.0f}% {latency_dir} "
        f"(p95: {score.latency_p95_ms:.0f} ms)."
    )

    if score.json_validity_rate is not None:
        parts.append(
            f"JSON validity: {score.json_validity_rate * 100:.1f}%."
        )

    parts.append(
        f"Error rate: {score.error_rate * 100:.2f}%."
    )

    parts.append(
        f"Validated across {score.sample_size:,} production shadow runs."
    )

    return " ".join(parts)


def generate_swap_cards(
    scoring_result: ScoringResult,
    risk_tolerance: RiskTolerance = "moderate",
) -> list[SwapCard]:
    """
    Convert a ScoringResult into a list of SwapCards.

    Only candidates whose swap_recommendation is within the
    allowed set for the given risk_tolerance are included.

    Args:
        scoring_result: Output from the Scoring Engine.
        risk_tolerance: "conservative", "moderate", or "aggressive".

    Returns:
        List of SwapCards sorted by monthly_savings_usd descending.
    """
    allowed = _RISK_ALLOW_MAP[risk_tolerance]
    cards: list[SwapCard] = []

    for score in scoring_result.candidates:
        if score.swap_recommendation not in allowed:
            continue

        monthly_savings = score.cost_savings_monthly_usd
        annual_savings = monthly_savings * 12
        projected_cost = max(
            0.0, scoring_result.original_monthly_cost - monthly_savings
        )

        card = SwapCard(
            org_id=scoring_result.org_id,
            task_type=scoring_result.task_type,
            current_model=scoring_result.original_model,
            recommended_model=score.candidate_model,
            swap_recommendation=score.swap_recommendation,
            confidence_pct=score.swap_confidence,
            monthly_savings_usd=round(monthly_savings, 2),
            annual_savings_usd=round(annual_savings, 2),
            monthly_savings_ci_lower=score.cost_savings_ci_95[0],
            monthly_savings_ci_upper=score.cost_savings_ci_95[1],
            original_monthly_cost_usd=round(scoring_result.original_monthly_cost, 2),
            projected_monthly_cost_usd=round(projected_cost, 2),
            headline=_build_headline(
                scoring_result.task_type,
                scoring_result.original_model,
                score.candidate_model,
                monthly_savings,
                score.swap_confidence,
            ),
            rationale=_build_rationale(score, scoring_result.original_monthly_cost),
            metrics=MetricsSummary(
                sample_size=score.sample_size,
                cost_savings_monthly_usd=round(monthly_savings, 2),
                cost_savings_ci_lower=score.cost_savings_ci_95[0],
                cost_savings_ci_upper=score.cost_savings_ci_95[1],
                latency_p95_ms=score.latency_p95_ms,
                latency_delta_pct=score.latency_delta_pct,
                error_rate=score.error_rate,
                json_validity_rate=score.json_validity_rate,
                output_consistency_cv=score.output_consistency_cv,
                topsis_score=score.topsis_score,
                is_pareto_optimal=score.is_pareto_optimal,
            ),
        )
        cards.append(card)

    cards.sort(key=lambda c: c.monthly_savings_usd, reverse=True)
    logger.info(
        "Generated %d swap cards for org=%s task=%s tolerance=%s",
        len(cards),
        scoring_result.org_id,
        scoring_result.task_type,
        risk_tolerance,
    )
    return cards


class RecommendationGenerator:
    """
    Stateless generator that processes multiple ScoringResults
    and groups the resulting SwapCards by task_type.

    Usage::

        gen = RecommendationGenerator(risk_tolerance="moderate")
        grouped = gen.process(scoring_results)
        # grouped = {"summarization": [SwapCard, ...], "classification": [...]}
    """

    def __init__(self, risk_tolerance: RiskTolerance = "moderate") -> None:
        self.risk_tolerance = risk_tolerance

    def process(
        self, scoring_results: list[ScoringResult]
    ) -> dict[str, list[SwapCard]]:
        """
        Process a list of ScoringResults into SwapCards grouped by task_type.

        Args:
            scoring_results: All scoring results for an org.

        Returns:
            Dict mapping task_type → sorted list of SwapCards.
        """
        grouped: dict[str, list[SwapCard]] = {}
        for result in scoring_results:
            cards = generate_swap_cards(result, self.risk_tolerance)
            if not cards:
                continue
            existing = grouped.setdefault(result.task_type, [])
            existing.extend(cards)

        # Sort each group by savings descending
        for task in grouped:
            grouped[task].sort(key=lambda c: c.monthly_savings_usd, reverse=True)

        return grouped

    def process_flat(
        self, scoring_results: list[ScoringResult]
    ) -> list[SwapCard]:
        """Return all cards as a flat list sorted by savings descending."""
        all_cards: list[SwapCard] = []
        for result in scoring_results:
            all_cards.extend(generate_swap_cards(result, self.risk_tolerance))
        all_cards.sort(key=lambda c: c.monthly_savings_usd, reverse=True)
        return all_cards

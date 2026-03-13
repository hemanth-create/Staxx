"""
Staxx Intelligence — Recommendation Generator Tests

Tests cover:
  - SwapCard generation from ScoringResults
  - Risk tolerance filtering
  - Grouping by task_type
  - ROI projection maths
  - Waterfall chart construction
  - Break-even calculation
  - Edge cases: zero savings, zero spend, empty candidates, all NO
"""

from __future__ import annotations

import math
from datetime import date

import pytest

from recommendations.generator import (
    RecommendationGenerator,
    SwapCard,
    generate_swap_cards,
)
from recommendations.roi_engine import ROIEngine, ROIProjection
from scoring.schemas import ModelScore, ScoringResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_model_score(
    candidate_model: str,
    swap_recommendation: str,
    swap_confidence: int,
    monthly_savings: float,
    ci_lower: float = 0.0,
    ci_upper: float = 0.0,
    latency_p95_ms: float = 200.0,
    latency_delta_pct: float = -20.0,
    error_rate: float = 0.01,
    json_validity_rate: float | None = 0.99,
    output_consistency_cv: float = 0.05,
    output_length_ratio: float = 1.0,
    topsis_score: float = 0.75,
    is_pareto_optimal: bool = True,
    sample_size: int = 50,
) -> ModelScore:
    return ModelScore(
        candidate_model=candidate_model,
        sample_size=sample_size,
        cost_savings_monthly_usd=monthly_savings,
        cost_savings_ci_95=(ci_lower, ci_upper),
        latency_p50_ms=150.0,
        latency_p95_ms=latency_p95_ms,
        latency_p99_ms=300.0,
        latency_delta_pct=latency_delta_pct,
        json_validity_rate=json_validity_rate,
        error_rate=error_rate,
        output_consistency_cv=output_consistency_cv,
        output_length_ratio=output_length_ratio,
        topsis_score=topsis_score,
        is_pareto_optimal=is_pareto_optimal,
        swap_confidence=swap_confidence,
        swap_recommendation=swap_recommendation,
    )


def _make_scoring_result(
    org_id: str = "org-123",
    task_type: str = "summarization",
    original_model: str = "gpt-4o",
    original_monthly_cost: float = 12000.0,
    candidates: list[ModelScore] | None = None,
) -> ScoringResult:
    if candidates is None:
        candidates = [
            _make_model_score(
                "claude-haiku-3",
                swap_recommendation="STRONG_YES",
                swap_confidence=92,
                monthly_savings=9000.0,
                ci_lower=8500.0,
                ci_upper=9500.0,
            ),
            _make_model_score(
                "gpt-4o-mini",
                swap_recommendation="YES",
                swap_confidence=78,
                monthly_savings=5000.0,
                ci_lower=4500.0,
                ci_upper=5500.0,
            ),
            _make_model_score(
                "mistral-7b",
                swap_recommendation="MAYBE",
                swap_confidence=55,
                monthly_savings=2000.0,
                ci_lower=1000.0,
                ci_upper=3000.0,
            ),
            _make_model_score(
                "some-expensive-model",
                swap_recommendation="NO",
                swap_confidence=10,
                monthly_savings=-500.0,
            ),
        ]
    best = next(
        (c.candidate_model for c in candidates if c.swap_recommendation in ("STRONG_YES", "YES")),
        None,
    )
    return ScoringResult(
        org_id=org_id,
        task_type=task_type,
        original_model=original_model,
        original_monthly_cost=original_monthly_cost,
        candidates=candidates,
        best_candidate=best,
    )


# ---------------------------------------------------------------------------
# generate_swap_cards
# ---------------------------------------------------------------------------


class TestGenerateSwapCards:
    def test_conservative_only_strong_yes(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        assert len(cards) == 1
        assert cards[0].recommended_model == "claude-haiku-3"
        assert cards[0].swap_recommendation == "STRONG_YES"

    def test_moderate_strong_yes_and_yes(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="moderate")
        assert len(cards) == 2
        recs = {c.swap_recommendation for c in cards}
        assert recs == {"STRONG_YES", "YES"}

    def test_aggressive_includes_maybe(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="aggressive")
        assert len(cards) == 3
        recs = {c.swap_recommendation for c in cards}
        assert "MAYBE" in recs

    def test_no_cards_for_all_no(self) -> None:
        result = _make_scoring_result(
            candidates=[
                _make_model_score("m1", "NO", 10, -100.0),
                _make_model_score("m2", "INSUFFICIENT_DATA", 0, 0.0),
            ]
        )
        cards = generate_swap_cards(result, risk_tolerance="aggressive")
        assert cards == []

    def test_cards_sorted_by_savings_descending(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="moderate")
        savings = [c.monthly_savings_usd for c in cards]
        assert savings == sorted(savings, reverse=True)

    def test_annual_savings_is_12x_monthly(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        card = cards[0]
        assert card.annual_savings_usd == pytest.approx(card.monthly_savings_usd * 12)

    def test_projected_cost_is_non_negative(self) -> None:
        # Even if savings > original cost, projected must not go negative
        result = _make_scoring_result(
            original_monthly_cost=1000.0,
            candidates=[
                _make_model_score("cheap", "STRONG_YES", 95, monthly_savings=5000.0)
            ],
        )
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        assert cards[0].projected_monthly_cost_usd == 0.0

    def test_headline_contains_key_info(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        card = cards[0]
        assert card.current_model in card.headline
        assert card.recommended_model in card.headline
        assert str(card.confidence_pct) in card.headline

    def test_rationale_contains_sample_size(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        card = cards[0]
        assert "50" in card.rationale  # sample_size=50

    def test_metrics_populated(self) -> None:
        result = _make_scoring_result()
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        m = cards[0].metrics
        assert m.sample_size == 50
        assert m.is_pareto_optimal is True

    def test_card_org_id_matches(self) -> None:
        result = _make_scoring_result(org_id="my-org")
        cards = generate_swap_cards(result)
        assert all(c.org_id == "my-org" for c in cards)

    def test_no_json_validity_is_none(self) -> None:
        result = _make_scoring_result(
            candidates=[
                _make_model_score(
                    "m1", "STRONG_YES", 90, 1000.0,
                    json_validity_rate=None,
                )
            ]
        )
        cards = generate_swap_cards(result, risk_tolerance="conservative")
        assert cards[0].metrics.json_validity_rate is None


# ---------------------------------------------------------------------------
# RecommendationGenerator
# ---------------------------------------------------------------------------


class TestRecommendationGenerator:
    def test_process_groups_by_task_type(self) -> None:
        results = [
            _make_scoring_result(task_type="summarization"),
            _make_scoring_result(task_type="classification"),
        ]
        gen = RecommendationGenerator(risk_tolerance="moderate")
        grouped = gen.process(results)
        assert "summarization" in grouped
        assert "classification" in grouped

    def test_process_flat_returns_all_cards(self) -> None:
        results = [
            _make_scoring_result(task_type="summarization"),
            _make_scoring_result(task_type="classification"),
        ]
        gen = RecommendationGenerator(risk_tolerance="moderate")
        cards = gen.process_flat(results)
        assert len(cards) == 4  # 2 per task (STRONG_YES + YES)

    def test_process_flat_sorted_by_savings(self) -> None:
        results = [
            _make_scoring_result(task_type="summarization"),
            _make_scoring_result(task_type="classification"),
        ]
        gen = RecommendationGenerator(risk_tolerance="moderate")
        cards = gen.process_flat(results)
        savings = [c.monthly_savings_usd for c in cards]
        assert savings == sorted(savings, reverse=True)

    def test_empty_results_returns_empty(self) -> None:
        gen = RecommendationGenerator()
        assert gen.process([]) == {}
        assert gen.process_flat([]) == []

    def test_results_with_no_qualifying_candidates_excluded(self) -> None:
        results = [
            _make_scoring_result(
                task_type="qa",
                candidates=[_make_model_score("m1", "NO", 5, -100.0)],
            )
        ]
        gen = RecommendationGenerator(risk_tolerance="moderate")
        grouped = gen.process(results)
        assert "qa" not in grouped


# ---------------------------------------------------------------------------
# ROIEngine
# ---------------------------------------------------------------------------


class TestROIEngine:
    def _engine(self, sub: float = 299.0) -> ROIEngine:
        return ROIEngine(staxx_subscription_usd=sub)

    def _cards(self, monthly_savings: float, task_type: str = "summarization") -> list[SwapCard]:
        from recommendations.generator import MetricsSummary
        return [
            SwapCard(
                org_id="org-1",
                task_type=task_type,
                current_model="gpt-4o",
                recommended_model="haiku",
                swap_recommendation="STRONG_YES",
                confidence_pct=92,
                monthly_savings_usd=monthly_savings,
                annual_savings_usd=monthly_savings * 12,
                monthly_savings_ci_lower=monthly_savings * 0.9,
                monthly_savings_ci_upper=monthly_savings * 1.1,
                original_monthly_cost_usd=12000.0,
                projected_monthly_cost_usd=max(0.0, 12000.0 - monthly_savings),
                headline="Switch now",
                rationale="Because numbers",
                metrics=MetricsSummary(
                    sample_size=50,
                    cost_savings_monthly_usd=monthly_savings,
                    cost_savings_ci_lower=monthly_savings * 0.9,
                    cost_savings_ci_upper=monthly_savings * 1.1,
                    latency_p95_ms=200.0,
                    latency_delta_pct=-20.0,
                    error_rate=0.01,
                    json_validity_rate=0.99,
                    output_consistency_cv=0.05,
                    topsis_score=0.8,
                    is_pareto_optimal=True,
                ),
            )
        ]

    def test_total_monthly_savings(self) -> None:
        cards = self._cards(9000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=12000.0)
        assert proj.total_monthly_savings_usd == pytest.approx(9000.0)

    def test_annual_savings_is_12x_monthly(self) -> None:
        cards = self._cards(9000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=12000.0)
        assert proj.annual_savings_usd == pytest.approx(108000.0)

    def test_cost_reduction_pct(self) -> None:
        cards = self._cards(6000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=12000.0)
        assert proj.cost_reduction_pct == pytest.approx(50.0)

    def test_projected_monthly_cost_non_negative(self) -> None:
        cards = self._cards(99999.0)  # savings > original
        proj = self._engine().project("org-1", cards, original_monthly_cost=1000.0)
        assert proj.projected_monthly_cost_usd == 0.0

    def test_break_even_calculation(self) -> None:
        cards = self._cards(1000.0)
        proj = self._engine(sub=500.0).project("org-1", cards, original_monthly_cost=5000.0)
        # Break-even = 500 / 1000 = 0.5 months
        assert proj.break_even_months == pytest.approx(0.5)

    def test_break_even_none_when_zero_savings(self) -> None:
        proj = self._engine().project("org-1", [], original_monthly_cost=5000.0)
        assert proj.break_even_months is None

    def test_monthly_projections_length(self) -> None:
        cards = self._cards(1000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=5000.0)
        assert len(proj.monthly_projections) == 12

    def test_cumulative_savings_increases_monotonically(self) -> None:
        cards = self._cards(1000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=5000.0)
        sav = [p.cumulative_savings_usd for p in proj.monthly_projections]
        assert all(sav[i] < sav[i + 1] for i in range(len(sav) - 1))

    def test_waterfall_segments_include_original_and_remaining(self) -> None:
        cards = self._cards(3000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=10000.0)
        categories = {s.category for s in proj.waterfall.segments}
        assert "original" in categories
        assert "remaining" in categories
        assert "saving" in categories

    def test_waterfall_math_balances(self) -> None:
        cards = self._cards(3000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=10000.0)
        w = proj.waterfall
        # original + total_savings (negative) = remaining
        assert w.total_original_usd - w.total_savings_usd == pytest.approx(
            w.projected_spend_usd, abs=0.01
        )

    def test_multiple_task_savings_are_additive(self) -> None:
        cards_a = self._cards(3000.0, task_type="summarization")
        cards_b = self._cards(2000.0, task_type="classification")
        proj = self._engine().project(
            "org-1", cards_a + cards_b, original_monthly_cost=12000.0
        )
        assert proj.total_monthly_savings_usd == pytest.approx(5000.0)

    def test_multiple_cards_same_task_takes_best(self) -> None:
        """Two cards for same (task_type, current_model) — only best wins."""
        from recommendations.generator import MetricsSummary

        def _card(savings: float, rec_model: str) -> SwapCard:
            return SwapCard(
                org_id="org-1",
                task_type="summarization",
                current_model="gpt-4o",
                recommended_model=rec_model,
                swap_recommendation="STRONG_YES",
                confidence_pct=90,
                monthly_savings_usd=savings,
                annual_savings_usd=savings * 12,
                monthly_savings_ci_lower=savings * 0.9,
                monthly_savings_ci_upper=savings * 1.1,
                original_monthly_cost_usd=12000.0,
                projected_monthly_cost_usd=12000.0 - savings,
                headline="h",
                rationale="r",
                metrics=MetricsSummary(
                    sample_size=30,
                    cost_savings_monthly_usd=savings,
                    cost_savings_ci_lower=savings * 0.9,
                    cost_savings_ci_upper=savings * 1.1,
                    latency_p95_ms=200,
                    latency_delta_pct=-10,
                    error_rate=0.01,
                    json_validity_rate=0.99,
                    output_consistency_cv=0.05,
                    topsis_score=0.7,
                    is_pareto_optimal=True,
                ),
            )

        cards = [_card(4000.0, "haiku"), _card(2000.0, "gpt-4o-mini")]
        proj = self._engine().project("org-1", cards, original_monthly_cost=12000.0)
        # Both target different recommended_models but same current_model+task
        # The aggregate should be the best per (task, current_model) key = 4000
        assert proj.total_monthly_savings_usd == pytest.approx(4000.0)

    def test_projection_base_date_used(self) -> None:
        cards = self._cards(1000.0)
        base = date(2025, 1, 1)
        proj = self._engine().project(
            "org-1", cards, original_monthly_cost=5000.0, base_date=base
        )
        assert proj.monthly_projections[0].month == "2025-02"
        assert proj.monthly_projections[11].month == "2026-01"

    def test_empty_cards_zero_savings(self) -> None:
        proj = self._engine().project("org-1", [], original_monthly_cost=5000.0)
        assert proj.total_monthly_savings_usd == 0.0
        assert proj.cost_reduction_pct == 0.0

    def test_included_card_ids_populated(self) -> None:
        cards = self._cards(1000.0)
        proj = self._engine().project("org-1", cards, original_monthly_cost=5000.0)
        assert len(proj.included_card_ids) == 1
        assert proj.included_card_ids[0] == cards[0].id

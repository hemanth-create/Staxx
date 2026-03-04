"""
Staxx Intelligence — TOPSIS Tests

Tests for the TOPSIS multi-criteria ranking algorithm.
"""

from __future__ import annotations

import pytest

from scoring.topsis import TOPSISInput, TOPSISWeights, topsis_rank


class TestTOPSISWeights:
    """Tests for weight validation."""

    def test_default_weights_sum_to_one(self):
        w = TOPSISWeights()
        total = w.cost + w.latency + w.quality + w.error + w.consistency
        assert abs(total - 1.0) < 0.01

    def test_custom_weights_valid(self):
        w = TOPSISWeights(cost=0.5, latency=0.2, quality=0.15, error=0.1, consistency=0.05)
        assert w.cost == 0.5

    def test_invalid_weights_raise(self):
        with pytest.raises(ValueError, match="must sum to 1.0"):
            TOPSISWeights(cost=0.5, latency=0.5, quality=0.5, error=0.1, consistency=0.05)


class TestTOPSISRank:
    """Tests for the TOPSIS ranking function."""

    def test_empty_candidates(self):
        result = topsis_rank([])
        assert result == {}

    def test_single_candidate(self):
        candidates = [
            TOPSISInput("gpt-4o-mini", cost_savings_pct=80, latency_p95_ms=200,
                        quality_score=0.98, error_rate=0.01, consistency_cv=0.15),
        ]
        result = topsis_rank(candidates)
        assert "gpt-4o-mini" in result
        assert 0.0 <= result["gpt-4o-mini"] <= 1.0

    def test_two_candidates_clear_winner(self):
        """A candidate with better scores on everything should rank higher."""
        candidates = [
            TOPSISInput("good_model", cost_savings_pct=90, latency_p95_ms=100,
                        quality_score=0.99, error_rate=0.01, consistency_cv=0.10),
            TOPSISInput("bad_model", cost_savings_pct=10, latency_p95_ms=5000,
                        quality_score=0.50, error_rate=0.20, consistency_cv=0.90),
        ]
        result = topsis_rank(candidates)
        assert result["good_model"] > result["bad_model"]

    def test_three_candidates_ranking_order(self):
        """Test ranking with three candidates of varying quality."""
        candidates = [
            TOPSISInput("best", cost_savings_pct=85, latency_p95_ms=150,
                        quality_score=0.98, error_rate=0.02, consistency_cv=0.12),
            TOPSISInput("mid", cost_savings_pct=60, latency_p95_ms=300,
                        quality_score=0.90, error_rate=0.05, consistency_cv=0.25),
            TOPSISInput("worst", cost_savings_pct=20, latency_p95_ms=800,
                        quality_score=0.70, error_rate=0.15, consistency_cv=0.50),
        ]
        result = topsis_rank(candidates)
        assert result["best"] > result["mid"] > result["worst"]

    def test_scores_between_zero_and_one(self):
        """All TOPSIS scores should be in [0, 1]."""
        candidates = [
            TOPSISInput("a", cost_savings_pct=50, latency_p95_ms=200,
                        quality_score=0.95, error_rate=0.03, consistency_cv=0.20),
            TOPSISInput("b", cost_savings_pct=70, latency_p95_ms=150,
                        quality_score=0.90, error_rate=0.05, consistency_cv=0.30),
            TOPSISInput("c", cost_savings_pct=30, latency_p95_ms=500,
                        quality_score=0.85, error_rate=0.08, consistency_cv=0.40),
        ]
        result = topsis_rank(candidates)
        for score in result.values():
            assert 0.0 <= score <= 1.0

    def test_custom_weights_affect_ranking(self):
        """Heavy cost weight should favour the cheapest candidate."""
        candidates = [
            # Cheap but slow
            TOPSISInput("cheap", cost_savings_pct=95, latency_p95_ms=1000,
                        quality_score=0.90, error_rate=0.03, consistency_cv=0.30),
            # Expensive but fast
            TOPSISInput("fast", cost_savings_pct=20, latency_p95_ms=50,
                        quality_score=0.95, error_rate=0.01, consistency_cv=0.10),
        ]

        # Default weights (cost=0.35) — could go either way
        # Heavy cost weights — should favour cheap
        cost_heavy = TOPSISWeights(cost=0.60, latency=0.10, quality=0.15, error=0.10, consistency=0.05)
        result_cost = topsis_rank(candidates, cost_heavy)
        assert result_cost["cheap"] > result_cost["fast"]

        # Heavy latency weights — should favour fast
        latency_heavy = TOPSISWeights(cost=0.10, latency=0.60, quality=0.15, error=0.10, consistency=0.05)
        result_lat = topsis_rank(candidates, latency_heavy)
        assert result_lat["fast"] > result_lat["cheap"]

    def test_identical_candidates_get_equal_scores(self):
        """Two identical candidates should get the same score."""
        inp = TOPSISInput("model", cost_savings_pct=50, latency_p95_ms=300,
                          quality_score=0.90, error_rate=0.05, consistency_cv=0.20)
        candidates = [
            TOPSISInput("a", **{k: v for k, v in vars(inp).items() if k != "candidate_model"}),
            TOPSISInput("b", **{k: v for k, v in vars(inp).items() if k != "candidate_model"}),
        ]
        result = topsis_rank(candidates)
        assert abs(result["a"] - result["b"]) < 0.001

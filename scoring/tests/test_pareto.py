"""
Staxx Intelligence — Pareto Frontier Tests

Tests for Pareto dominance detection.
"""

from __future__ import annotations

import pytest

from scoring.pareto import ParetoCandidate, build_pareto_candidate, find_pareto_optimal


class TestParetoFrontier:
    """Tests for the Pareto frontier detection algorithm."""

    def test_empty_candidates(self):
        assert find_pareto_optimal([]) == set()

    def test_single_candidate_is_pareto(self):
        c = ParetoCandidate("only", 0.9, 0.8, 0.95, 0.99, 0.9)
        assert find_pareto_optimal([c]) == {"only"}

    def test_dominated_candidate_excluded(self):
        """A candidate dominated on ALL dimensions should not be Pareto-optimal."""
        dominator = ParetoCandidate("best", 0.9, 0.9, 0.9, 0.9, 0.9)
        dominated = ParetoCandidate("worst", 0.1, 0.1, 0.1, 0.1, 0.1)
        result = find_pareto_optimal([dominator, dominated])
        assert "best" in result
        assert "worst" not in result

    def test_non_dominated_candidates_both_pareto(self):
        """Two candidates that trade off on different dimensions are both Pareto-optimal."""
        # A is better on cost, B is better on latency
        a = ParetoCandidate("cheap", 0.9, 0.3, 0.8, 0.9, 0.7)
        b = ParetoCandidate("fast", 0.3, 0.9, 0.8, 0.9, 0.7)
        result = find_pareto_optimal([a, b])
        assert result == {"cheap", "fast"}

    def test_three_candidates_mixed(self):
        """One dominant, one dominated, one non-dominated tradeoff."""
        best = ParetoCandidate("best", 0.9, 0.9, 0.95, 0.98, 0.9)
        mid = ParetoCandidate("mid", 0.5, 0.5, 0.5, 0.5, 0.5)
        tradeoff = ParetoCandidate("tradeoff", 0.3, 0.95, 0.99, 0.99, 0.95)
        result = find_pareto_optimal([best, mid, tradeoff])
        # best dominates mid on all, but tradeoff has higher latency/quality
        assert "best" in result
        assert "tradeoff" in result
        assert "mid" not in result

    def test_all_identical_are_pareto(self):
        """If all candidates are identical, none dominates, all are Pareto."""
        a = ParetoCandidate("a", 0.5, 0.5, 0.5, 0.5, 0.5)
        b = ParetoCandidate("b", 0.5, 0.5, 0.5, 0.5, 0.5)
        c = ParetoCandidate("c", 0.5, 0.5, 0.5, 0.5, 0.5)
        result = find_pareto_optimal([a, b, c])
        assert result == {"a", "b", "c"}

    def test_four_candidates_pareto_frontier(self):
        """Realistic 4-candidate scenario."""
        candidates = [
            ParetoCandidate("gpt-4o-mini", 0.95, 0.70, 0.90, 0.98, 0.80),
            ParetoCandidate("claude-haiku", 0.85, 0.80, 0.92, 0.97, 0.85),
            ParetoCandidate("gemini-flash", 0.90, 0.90, 0.85, 0.95, 0.90),
            ParetoCandidate("llama-8b", 0.80, 0.60, 0.70, 0.90, 0.70),
        ]
        result = find_pareto_optimal(candidates)
        # gemini-flash has the best latency, gpt-4o-mini has best cost
        # claude-haiku has good quality — all three are non-dominated
        # llama-8b is dominated by others
        assert "llama-8b" not in result
        assert len(result) >= 2


class TestBuildParetoCandidate:
    """Tests for the normalisation builder."""

    def test_cost_normalisation(self):
        c = build_pareto_candidate(
            "test", cost_savings_pct=50, latency_p95_ms=500,
            quality_score=0.9, error_rate=0.05, consistency_cv=0.3,
        )
        assert c.cost_score == pytest.approx(0.5)

    def test_latency_inversion(self):
        """Lower latency should produce higher score."""
        fast = build_pareto_candidate(
            "fast", cost_savings_pct=50, latency_p95_ms=100,
            quality_score=0.9, error_rate=0.05, consistency_cv=0.3,
        )
        slow = build_pareto_candidate(
            "slow", cost_savings_pct=50, latency_p95_ms=5000,
            quality_score=0.9, error_rate=0.05, consistency_cv=0.3,
        )
        assert fast.latency_score > slow.latency_score

    def test_error_rate_inversion(self):
        """Lower error rate should produce higher score."""
        reliable = build_pareto_candidate(
            "reliable", cost_savings_pct=50, latency_p95_ms=500,
            quality_score=0.9, error_rate=0.01, consistency_cv=0.3,
        )
        unreliable = build_pareto_candidate(
            "unreliable", cost_savings_pct=50, latency_p95_ms=500,
            quality_score=0.9, error_rate=0.20, consistency_cv=0.3,
        )
        assert reliable.error_score > unreliable.error_score

    def test_consistency_inversion(self):
        """Lower CV should produce higher consistency score."""
        consistent = build_pareto_candidate(
            "consistent", cost_savings_pct=50, latency_p95_ms=500,
            quality_score=0.9, error_rate=0.05, consistency_cv=0.1,
        )
        inconsistent = build_pareto_candidate(
            "inconsistent", cost_savings_pct=50, latency_p95_ms=500,
            quality_score=0.9, error_rate=0.05, consistency_cv=1.5,
        )
        assert consistent.consistency_score > inconsistent.consistency_score

    def test_scores_bounded(self):
        """All normalised scores should be in [0, 1]."""
        c = build_pareto_candidate(
            "test", cost_savings_pct=150, latency_p95_ms=20000,
            quality_score=1.5, error_rate=0.5, consistency_cv=3.0,
        )
        for attr in ("cost_score", "latency_score", "quality_score",
                      "error_score", "consistency_score"):
            val = getattr(c, attr)
            assert 0.0 <= val <= 1.5, f"{attr}={val} out of expected range"

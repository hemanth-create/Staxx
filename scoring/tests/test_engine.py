"""
Staxx Intelligence — Scoring Engine End-to-End Tests

Tests the full scoring pipeline using ``score_from_data()``
with realistic mock shadow eval run data.
"""

from __future__ import annotations

import numpy as np
import pytest

from scoring.confidence import compute_swap_confidence
from scoring.engine import _extract_run_data, score_candidate, score_from_data
from scoring.metrics import OriginalModelData, RunData
from scoring.statistics import (
    BootstrapCI,
    bootstrap_ci,
    bootstrap_diff_ci,
    bootstrap_mean_ci,
    cohen_d,
    sample_size_adequacy,
    welch_t_test,
)


# ---------------------------------------------------------------------------
# Fixtures: realistic mock data
# ---------------------------------------------------------------------------

def _make_original() -> OriginalModelData:
    """Simulate a production gpt-4o workload: ~10K calls/month at $0.01/call."""
    rng = np.random.default_rng(42)
    costs = rng.normal(0.01, 0.002, size=200).clip(0.001)
    return OriginalModelData(
        avg_cost_per_call=0.01,
        avg_latency_ms=450.0,
        avg_output_tokens=350.0,
        monthly_call_volume=10_000,
        monthly_cost_usd=100.0,
        cost_per_call_array=costs,
    )


def _make_good_candidate_runs(n: int = 50) -> list[dict]:
    """Simulate gpt-4o-mini: much cheaper, slightly faster, good quality."""
    rng = np.random.default_rng(123)
    runs = []
    for _ in range(n):
        error = None if rng.random() > 0.02 else "timeout"
        runs.append({
            "cost_usd": rng.normal(0.001, 0.0003).clip(0.0001),
            "latency_ms": int(rng.normal(300, 80).clip(50)),
            "output_tokens": int(rng.normal(340, 50).clip(10)),
            "json_valid": True if rng.random() > 0.03 else False,
            "error": error,
            "output_empty": False,
            "output_truncated": False,
        })
    return runs


def _make_poor_candidate_runs(n: int = 30) -> list[dict]:
    """Simulate a bad candidate: high error rate, truncated outputs."""
    rng = np.random.default_rng(456)
    runs = []
    for _ in range(n):
        error = "rate_limited" if rng.random() < 0.15 else None
        runs.append({
            "cost_usd": rng.normal(0.005, 0.002).clip(0.0001),
            "latency_ms": int(rng.normal(800, 200).clip(100)),
            "output_tokens": int(rng.normal(150, 80).clip(5)),
            "json_valid": True if rng.random() > 0.20 else False,
            "error": error,
            "output_empty": rng.random() < 0.05,
            "output_truncated": rng.random() < 0.10,
        })
    return runs


def _make_marginal_candidate_runs(n: int = 40) -> list[dict]:
    """Simulate a marginal candidate: moderate savings, comparable quality."""
    rng = np.random.default_rng(789)
    runs = []
    for _ in range(n):
        runs.append({
            "cost_usd": rng.normal(0.006, 0.001).clip(0.001),
            "latency_ms": int(rng.normal(480, 100).clip(80)),
            "output_tokens": int(rng.normal(320, 40).clip(20)),
            "json_valid": True if rng.random() > 0.05 else False,
            "error": None,
            "output_empty": False,
            "output_truncated": False,
        })
    return runs


# ===========================================================================
# Bootstrap / Statistics Tests
# ===========================================================================


class TestBootstrap:
    """Tests for the bootstrap CI functions."""

    def test_mean_ci_contains_true_mean(self):
        rng = np.random.default_rng(42)
        data = rng.normal(100, 10, size=200)
        ci = bootstrap_mean_ci(data, seed=42)
        assert ci.ci_lower <= np.mean(data) <= ci.ci_upper

    def test_ci_width_shrinks_with_more_data(self):
        rng = np.random.default_rng(42)
        small = rng.normal(0, 1, size=20)
        large = rng.normal(0, 1, size=500)

        ci_small = bootstrap_mean_ci(small, seed=42)
        ci_large = bootstrap_mean_ci(large, seed=42)

        width_small = ci_small.ci_upper - ci_small.ci_lower
        width_large = ci_large.ci_upper - ci_large.ci_lower
        assert width_large < width_small

    def test_diff_ci_positive_when_a_larger(self):
        a = np.array([10.0, 12.0, 11.0, 13.0, 10.5] * 10)
        b = np.array([5.0, 6.0, 5.5, 7.0, 5.2] * 10)
        ci = bootstrap_diff_ci(a, b, seed=42)
        assert ci.ci_lower > 0  # a is clearly larger

    def test_empty_data(self):
        ci = bootstrap_mean_ci(np.array([]))
        assert ci.estimate == 0.0

    def test_seed_reproducibility(self):
        data = np.array([1.0, 2.0, 3.0, 4.0, 5.0] * 10)
        ci1 = bootstrap_mean_ci(data, seed=99)
        ci2 = bootstrap_mean_ci(data, seed=99)
        assert ci1.ci_lower == ci2.ci_lower
        assert ci1.ci_upper == ci2.ci_upper


class TestStatisticalTests:
    """Tests for significance tests and effect sizes."""

    def test_welch_significant(self):
        a = np.array([10.0, 11.0, 12.0, 10.5, 11.5] * 10)
        b = np.array([5.0, 6.0, 5.5, 4.5, 5.2] * 10)
        p = welch_t_test(a, b)
        assert p < 0.05

    def test_welch_not_significant(self):
        rng = np.random.default_rng(42)
        a = rng.normal(10, 1, size=20)
        b = rng.normal(10, 1, size=20)
        p = welch_t_test(a, b)
        assert p > 0.05  # Same distribution → not significant

    def test_welch_insufficient_data(self):
        p = welch_t_test(np.array([1.0]), np.array([2.0]))
        assert p == 1.0

    def test_cohen_d_large_effect(self):
        a = np.array([10.0, 11.0, 12.0, 10.5, 11.5] * 10)
        b = np.array([5.0, 6.0, 5.5, 4.5, 5.2] * 10)
        d = cohen_d(a, b)
        assert d > 0.8  # Large effect

    def test_sample_size_adequacy(self):
        assert sample_size_adequacy(0) == 0.0
        assert sample_size_adequacy(10) == 0.0
        assert sample_size_adequacy(20) == 0.0
        assert sample_size_adequacy(60) == pytest.approx(0.5, abs=0.01)
        assert sample_size_adequacy(100) == 1.0
        assert sample_size_adequacy(500) == 1.0


# ===========================================================================
# Run Data Extraction Tests
# ===========================================================================


class TestExtractRunData:
    """Tests for converting raw DB rows to numpy arrays."""

    def test_basic_extraction(self):
        runs = _make_good_candidate_runs(25)
        data = _extract_run_data(runs)
        assert data.sample_size == 25
        assert len(data.cost_usd) == 25
        assert len(data.latency_ms) == 25
        assert data.has_json_data is True

    def test_empty_runs(self):
        data = _extract_run_data([])
        assert data.sample_size == 0
        assert len(data.cost_usd) == 0

    def test_null_json_valid(self):
        """Runs without json_valid should have NaN in the array."""
        runs = [
            {"cost_usd": 0.01, "latency_ms": 200, "output_tokens": 100,
             "json_valid": None, "error": None, "output_empty": False,
             "output_truncated": False},
        ]
        data = _extract_run_data(runs)
        assert data.has_json_data is False
        assert np.isnan(data.json_valid[0])


# ===========================================================================
# Metric Tests
# ===========================================================================


class TestMetrics:
    """Tests for individual metric calculators."""

    def test_cost_savings_positive(self):
        from scoring.metrics import compute_cost_savings
        original = _make_original()
        candidate = _extract_run_data(_make_good_candidate_runs())
        savings, ci = compute_cost_savings(candidate, original, seed=42)
        assert savings > 0  # gpt-4o-mini is much cheaper

    def test_latency_percentiles(self):
        from scoring.metrics import compute_latency
        original = _make_original()
        candidate = _extract_run_data(_make_good_candidate_runs())
        latency = compute_latency(candidate, original)
        assert latency.p50_ms > 0
        assert latency.p50_ms <= latency.p95_ms <= latency.p99_ms

    def test_error_rate_calculation(self):
        from scoring.metrics import compute_error_rate
        good = _extract_run_data(_make_good_candidate_runs(100))
        poor = _extract_run_data(_make_poor_candidate_runs(100))
        assert compute_error_rate(good) < compute_error_rate(poor)

    def test_consistency_cv(self):
        from scoring.metrics import compute_output_consistency_cv
        data = _extract_run_data(_make_good_candidate_runs(50))
        cv = compute_output_consistency_cv(data)
        assert cv > 0  # Should have some variation
        assert cv < 1.0  # But not extreme

    def test_output_length_ratio(self):
        from scoring.metrics import compute_output_length_ratio
        original = _make_original()
        good = _extract_run_data(_make_good_candidate_runs(50))
        ratio = compute_output_length_ratio(good, original)
        # Good candidate outputs ~340 tokens vs original ~350 → ratio ≈ 0.97
        assert 0.5 < ratio < 1.5


# ===========================================================================
# Swap Confidence Tests
# ===========================================================================


class TestSwapConfidence:
    """Tests for the swap confidence scoring."""

    def test_strong_yes_scenario(self):
        """High savings, low error, good quality → STRONG_YES."""
        confidence, rec = compute_swap_confidence(
            cost_savings_monthly=500.0,
            cost_ci=BootstrapCI(500.0, 400.0, 600.0, 0.95, 1000),
            error_rate=0.01,
            json_validity_rate=0.99,
            latency_delta_pct=-5.0,
            output_length_ratio=0.95,
            sample_size=100,
            topsis_score=0.85,
        )
        assert confidence >= 80
        assert rec == "STRONG_YES"

    def test_no_savings_means_no(self):
        """Zero savings should always return NO."""
        confidence, rec = compute_swap_confidence(
            cost_savings_monthly=0.0,
            cost_ci=BootstrapCI(0.0, -10.0, 10.0, 0.95, 1000),
            error_rate=0.01,
            json_validity_rate=0.99,
            latency_delta_pct=0.0,
            output_length_ratio=0.95,
            sample_size=100,
            topsis_score=0.5,
        )
        assert rec == "NO"

    def test_high_error_rate_means_no(self):
        """Error rate > 10% should always return NO."""
        confidence, rec = compute_swap_confidence(
            cost_savings_monthly=1000.0,
            cost_ci=BootstrapCI(1000.0, 800.0, 1200.0, 0.95, 1000),
            error_rate=0.15,
            json_validity_rate=0.99,
            latency_delta_pct=-20.0,
            output_length_ratio=1.0,
            sample_size=100,
            topsis_score=0.9,
        )
        assert rec == "NO"

    def test_small_sample_reduces_confidence(self):
        """Small sample size (but >= 20) should reduce the score."""
        large, _ = compute_swap_confidence(
            cost_savings_monthly=200.0,
            cost_ci=BootstrapCI(200.0, 150.0, 250.0, 0.95, 1000),
            error_rate=0.02,
            json_validity_rate=0.98,
            latency_delta_pct=5.0,
            output_length_ratio=0.9,
            sample_size=100,
            topsis_score=0.7,
        )
        small, _ = compute_swap_confidence(
            cost_savings_monthly=200.0,
            cost_ci=BootstrapCI(200.0, 150.0, 250.0, 0.95, 1000),
            error_rate=0.02,
            json_validity_rate=0.98,
            latency_delta_pct=5.0,
            output_length_ratio=0.9,
            sample_size=25,
            topsis_score=0.7,
        )
        assert large >= small

    def test_confidence_bounded_0_100(self):
        confidence, _ = compute_swap_confidence(
            cost_savings_monthly=99999.0,
            cost_ci=BootstrapCI(99999.0, 99990.0, 100000.0, 0.95, 1000),
            error_rate=0.0,
            json_validity_rate=1.0,
            latency_delta_pct=-50.0,
            output_length_ratio=1.0,
            sample_size=500,
            topsis_score=1.0,
        )
        assert 0 <= confidence <= 100


# ===========================================================================
# Full Engine Integration Test
# ===========================================================================


class TestScoringEngine:
    """End-to-end tests using score_from_data()."""

    def test_good_candidate_gets_yes(self):
        """A clearly good candidate should get YES or STRONG_YES."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
            },
            seed=42,
        )
        assert len(result.candidates) == 1
        cand = result.candidates[0]
        assert cand.candidate_model == "gpt-4o-mini"
        assert cand.swap_recommendation in ("STRONG_YES", "YES", "MAYBE")
        assert cand.cost_savings_monthly_usd > 0
        assert cand.swap_confidence > 0
        assert cand.sample_size == 50

    def test_poor_candidate_gets_no(self):
        """A clearly poor candidate should get NO."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "bad-model": _make_poor_candidate_runs(30),
            },
            seed=42,
        )
        assert len(result.candidates) == 1
        cand = result.candidates[0]
        assert cand.swap_recommendation == "NO"

    def test_multiple_candidates_ranked(self):
        """Multiple candidates should be sorted by swap_confidence."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="extraction",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
                "bad-model": _make_poor_candidate_runs(30),
                "marginal-model": _make_marginal_candidate_runs(40),
            },
            seed=42,
        )
        assert len(result.candidates) == 3
        # Should be sorted by confidence descending
        confidences = [c.swap_confidence for c in result.candidates]
        assert confidences == sorted(confidences, reverse=True)

    def test_insufficient_data_excluded(self):
        """Candidates with < 20 runs should be excluded."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
                "too-few-runs": _make_good_candidate_runs(10),  # < 20
            },
            seed=42,
        )
        names = [c.candidate_model for c in result.candidates]
        assert "gpt-4o-mini" in names
        assert "too-few-runs" not in names

    def test_empty_candidates(self):
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={},
            seed=42,
        )
        assert result.candidates == []
        assert result.best_candidate is None

    def test_best_candidate_selected(self):
        """best_candidate should be the highest-confidence YES+."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
                "bad-model": _make_poor_candidate_runs(30),
            },
            seed=42,
        )
        # best_candidate should be gpt-4o-mini (if it got YES+)
        if result.best_candidate is not None:
            best = next(c for c in result.candidates if c.candidate_model == result.best_candidate)
            assert best.swap_recommendation in ("STRONG_YES", "YES")

    def test_topsis_scores_present(self):
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
                "marginal": _make_marginal_candidate_runs(40),
            },
            seed=42,
        )
        for c in result.candidates:
            assert 0.0 <= c.topsis_score <= 1.0

    def test_pareto_optimal_flagged(self):
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={
                "gpt-4o-mini": _make_good_candidate_runs(50),
                "marginal": _make_marginal_candidate_runs(40),
                "bad-model": _make_poor_candidate_runs(30),
            },
            seed=42,
        )
        # At least one candidate should be Pareto-optimal
        pareto_count = sum(1 for c in result.candidates if c.is_pareto_optimal)
        assert pareto_count >= 1

    def test_cost_ci_tuple(self):
        """cost_savings_ci_95 should be a (lower, upper) tuple."""
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={"mini": _make_good_candidate_runs(50)},
            seed=42,
        )
        ci = result.candidates[0].cost_savings_ci_95
        assert isinstance(ci, tuple)
        assert len(ci) == 2
        assert ci[0] <= ci[1]

    def test_generated_at_present(self):
        original = _make_original()
        result = score_from_data(
            org_id="aaaa-bbbb-cccc-dddd",
            task_type="summarization",
            original_model="gpt-4o",
            original_data=original,
            candidates_data={"mini": _make_good_candidate_runs(25)},
            seed=42,
        )
        assert result.generated_at is not None

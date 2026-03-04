"""
Staxx Intelligence — Metric Calculators

Each function computes one dimension of the scoring rubric from
raw shadow evaluation run data.  All functions accept numpy arrays
and return plain Python scalars / tuples for easy serialisation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from scoring.statistics import bootstrap_diff_ci, bootstrap_mean_ci, BootstrapCI


# ---------------------------------------------------------------------------
# Data container for raw run data (avoids passing dicts everywhere)
# ---------------------------------------------------------------------------


@dataclass
class RunData:
    """Extracted arrays from shadow eval runs for a single candidate."""

    cost_usd: np.ndarray           # Cost of each candidate run
    latency_ms: np.ndarray         # Latency of each candidate run
    output_tokens: np.ndarray      # Output token count per run
    json_valid: np.ndarray         # Boolean array (NaN if not a JSON task)
    has_json_data: bool            # Whether JSON validity is relevant
    errors: np.ndarray             # Boolean array: True = error occurred
    sample_size: int


@dataclass
class OriginalModelData:
    """Aggregate data for the original (production) model."""

    avg_cost_per_call: float
    avg_latency_ms: float
    avg_output_tokens: float
    monthly_call_volume: int
    monthly_cost_usd: float
    cost_per_call_array: np.ndarray  # For bootstrap diff CI


# ---------------------------------------------------------------------------
# Cost Metrics
# ---------------------------------------------------------------------------


def compute_cost_savings(
    candidate: RunData,
    original: OriginalModelData,
    seed: Optional[int] = None,
) -> tuple[float, BootstrapCI]:
    """
    Compute average cost savings per call and projected monthly savings.

    Returns:
        (monthly_savings_usd, bootstrap_ci_on_monthly_savings)
    """
    if candidate.sample_size == 0:
        return 0.0, BootstrapCI(0.0, 0.0, 0.0, 0.95, 0)

    avg_candidate_cost = float(np.mean(candidate.cost_usd))
    savings_per_call = original.avg_cost_per_call - avg_candidate_cost
    monthly_savings = savings_per_call * original.monthly_call_volume

    # Bootstrap CI on the per-call savings, then scale to monthly
    per_call_ci = bootstrap_diff_ci(
        original.cost_per_call_array,
        candidate.cost_usd,
        seed=seed,
    )

    monthly_ci = BootstrapCI(
        estimate=monthly_savings,
        ci_lower=per_call_ci.ci_lower * original.monthly_call_volume,
        ci_upper=per_call_ci.ci_upper * original.monthly_call_volume,
        ci_level=per_call_ci.ci_level,
        n_iterations=per_call_ci.n_iterations,
    )

    return monthly_savings, monthly_ci


# ---------------------------------------------------------------------------
# Latency Metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LatencyMetrics:
    """Latency percentiles and delta vs original."""

    p50_ms: float
    p95_ms: float
    p99_ms: float
    delta_pct: float  # vs original p50; negative = faster


def compute_latency(
    candidate: RunData,
    original: OriginalModelData,
) -> LatencyMetrics:
    """Compute p50/p95/p99 latency for the candidate and delta vs original."""
    if candidate.sample_size == 0 or len(candidate.latency_ms) == 0:
        return LatencyMetrics(0.0, 0.0, 0.0, 0.0)

    valid_latencies = candidate.latency_ms[candidate.latency_ms > 0]
    if len(valid_latencies) == 0:
        return LatencyMetrics(0.0, 0.0, 0.0, 0.0)

    p50 = float(np.percentile(valid_latencies, 50))
    p95 = float(np.percentile(valid_latencies, 95))
    p99 = float(np.percentile(valid_latencies, 99))

    # Delta as percentage change: (candidate - original) / original × 100
    if original.avg_latency_ms > 0:
        delta_pct = ((p50 - original.avg_latency_ms) / original.avg_latency_ms) * 100
    else:
        delta_pct = 0.0

    return LatencyMetrics(
        p50_ms=round(p50, 2),
        p95_ms=round(p95, 2),
        p99_ms=round(p99, 2),
        delta_pct=round(delta_pct, 2),
    )


# ---------------------------------------------------------------------------
# Quality Metrics
# ---------------------------------------------------------------------------


def compute_json_validity_rate(candidate: RunData) -> Optional[float]:
    """
    Compute the JSON validity rate.

    Returns None if JSON validation is not applicable for this task type.
    """
    if not candidate.has_json_data:
        return None

    valid_mask = ~np.isnan(candidate.json_valid)
    if not np.any(valid_mask):
        return None

    valid_entries = candidate.json_valid[valid_mask]
    return float(np.mean(valid_entries))


def compute_error_rate(candidate: RunData) -> float:
    """Compute the fraction of runs that had errors."""
    if candidate.sample_size == 0:
        return 0.0
    return float(np.mean(candidate.errors))


# ---------------------------------------------------------------------------
# Consistency Metrics
# ---------------------------------------------------------------------------


def compute_output_consistency_cv(candidate: RunData) -> float:
    """
    Coefficient of Variation (CV) of output token lengths.

    CV = std / mean.  Lower is better (more consistent).
    Returns 0.0 if mean is 0 or sample is empty.
    """
    if candidate.sample_size == 0:
        return 0.0

    valid_tokens = candidate.output_tokens[candidate.output_tokens > 0]
    if len(valid_tokens) < 2:
        return 0.0

    mean_tokens = float(np.mean(valid_tokens))
    if mean_tokens == 0:
        return 0.0

    std_tokens = float(np.std(valid_tokens, ddof=1))
    return round(std_tokens / mean_tokens, 4)


def compute_output_length_ratio(
    candidate: RunData,
    original: OriginalModelData,
) -> float:
    """
    Average candidate output tokens / average original output tokens.

    Values < 1.0 suggest truncation; > 1.0 suggest verbosity.
    Returns 0.0 if original has no output data.
    """
    if original.avg_output_tokens <= 0:
        return 0.0

    if candidate.sample_size == 0:
        return 0.0

    valid_tokens = candidate.output_tokens[candidate.output_tokens > 0]
    if len(valid_tokens) == 0:
        return 0.0

    avg_candidate = float(np.mean(valid_tokens))
    return round(avg_candidate / original.avg_output_tokens, 4)

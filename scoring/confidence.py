"""
Staxx Intelligence — Swap Confidence Score

Produces a single 0–100 integer score representing overall
confidence in recommending a model swap.  Combines:

  1. Statistical significance of cost savings   (40 points)
  2. Quality parity (JSON validity + error rate) (30 points)
  3. Latency acceptability                       (15 points)
  4. Sample size adequacy                        (15 points)
"""

from __future__ import annotations

import numpy as np

from scoring.statistics import BootstrapCI, sample_size_adequacy


def compute_swap_confidence(
    cost_savings_monthly: float,
    cost_ci: BootstrapCI,
    error_rate: float,
    json_validity_rate: float | None,
    latency_delta_pct: float,
    output_length_ratio: float,
    sample_size: int,
    topsis_score: float,
) -> tuple[int, str]:
    """
    Compute the swap confidence score (0–100) and recommendation.

    Args:
        cost_savings_monthly: Projected monthly savings in USD.
        cost_ci: Bootstrap 95% CI on monthly savings.
        error_rate: Candidate error rate (0.0–1.0).
        json_validity_rate: JSON validity rate (None if N/A).
        latency_delta_pct: Latency change % (negative = faster).
        output_length_ratio: Candidate / original output length.
        sample_size: Number of valid shadow eval runs.
        topsis_score: TOPSIS multi-criteria score (0.0–1.0).

    Returns:
        (confidence_score, recommendation_string)
    """
    points = 0.0

    # =========================================================================
    # 1. COST SAVINGS SIGNIFICANCE (max 40 points)
    # =========================================================================
    cost_points = 0.0

    if cost_savings_monthly > 0:
        # Base points for positive savings
        cost_points += 10.0

        # Bonus if the entire 95% CI is above zero (statistically significant)
        if cost_ci.ci_lower > 0:
            cost_points += 15.0  # Strong evidence of real savings

        # Bonus proportional to magnitude of savings
        if cost_savings_monthly >= 1000:
            cost_points += 10.0
        elif cost_savings_monthly >= 100:
            cost_points += 7.0
        elif cost_savings_monthly >= 10:
            cost_points += 4.0
        else:
            cost_points += 1.0

        # Bonus for tight CI (precise estimate)
        if cost_ci.ci_upper > 0 and cost_ci.ci_lower > 0:
            ci_width_ratio = (cost_ci.ci_upper - cost_ci.ci_lower) / cost_ci.estimate if cost_ci.estimate != 0 else 999
            if ci_width_ratio < 0.5:
                cost_points += 5.0
            elif ci_width_ratio < 1.0:
                cost_points += 3.0

    points += min(40.0, cost_points)

    # =========================================================================
    # 2. QUALITY PARITY (max 30 points)
    # =========================================================================
    quality_points = 0.0

    # Error rate assessment
    if error_rate <= 0.01:
        quality_points += 12.0  # Near-zero errors
    elif error_rate <= 0.05:
        quality_points += 8.0
    elif error_rate <= 0.10:
        quality_points += 4.0
    # else: 0 points for high error rates

    # JSON validity assessment (skip if not applicable)
    if json_validity_rate is not None:
        if json_validity_rate >= 0.98:
            quality_points += 10.0
        elif json_validity_rate >= 0.95:
            quality_points += 7.0
        elif json_validity_rate >= 0.90:
            quality_points += 4.0
        elif json_validity_rate >= 0.80:
            quality_points += 2.0
    else:
        # Not a JSON task — give partial quality credit
        quality_points += 6.0

    # Output length ratio (penalise extreme truncation or verbosity)
    if 0.7 <= output_length_ratio <= 1.3:
        quality_points += 8.0  # Output length is reasonable
    elif 0.5 <= output_length_ratio <= 1.5:
        quality_points += 4.0
    elif 0.3 <= output_length_ratio <= 2.0:
        quality_points += 2.0

    points += min(30.0, quality_points)

    # =========================================================================
    # 3. LATENCY ACCEPTABILITY (max 15 points)
    # =========================================================================
    latency_points = 0.0

    if latency_delta_pct <= -10:
        latency_points = 15.0  # Significantly faster
    elif latency_delta_pct <= 0:
        latency_points = 13.0  # Same or slightly faster
    elif latency_delta_pct <= 10:
        latency_points = 10.0  # Slightly slower (acceptable)
    elif latency_delta_pct <= 25:
        latency_points = 6.0   # Moderately slower
    elif latency_delta_pct <= 50:
        latency_points = 3.0   # Noticeably slower
    else:
        latency_points = 0.0   # Unacceptably slower

    points += latency_points

    # =========================================================================
    # 4. SAMPLE SIZE ADEQUACY (max 15 points)
    # =========================================================================
    adequacy = sample_size_adequacy(sample_size, min_n=20, ideal_n=100)
    sample_points = adequacy * 15.0
    points += sample_points

    # =========================================================================
    # Final score and recommendation
    # =========================================================================
    confidence = int(round(min(100.0, max(0.0, points))))

    # Determine recommendation
    recommendation = _classify_recommendation(confidence, error_rate, cost_savings_monthly)

    return confidence, recommendation


def _classify_recommendation(
    confidence: int,
    error_rate: float,
    cost_savings: float,
) -> str:
    """
    Map confidence score to a recommendation string.

    Safety overrides:
      - Error rate > 10% → always NO regardless of score
      - No cost savings → cap at MAYBE
    """
    # Safety override: high error rate
    if error_rate > 0.10:
        return "NO"

    # Safety override: no savings
    if cost_savings <= 0:
        return "NO"

    if confidence >= 80:
        return "STRONG_YES"
    elif confidence >= 60:
        return "YES"
    elif confidence >= 40:
        return "MAYBE"
    else:
        return "NO"

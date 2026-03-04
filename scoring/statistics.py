"""
Staxx Intelligence — Statistical Utilities

Bootstrap confidence intervals and significance tests for
the scoring engine.  All functions operate on numpy arrays
for performance (< 500ms for 1000 runs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np


@dataclass(frozen=True)
class BootstrapCI:
    """Result of a bootstrap confidence interval estimation."""

    estimate: float       # Point estimate (mean of original sample)
    ci_lower: float       # Lower bound of CI
    ci_upper: float       # Upper bound of CI
    ci_level: float       # Confidence level (e.g. 0.95)
    n_iterations: int     # Number of bootstrap iterations used


def bootstrap_ci(
    data: np.ndarray,
    statistic: Callable[[np.ndarray], float] = np.mean,
    ci_level: float = 0.95,
    n_iterations: int = 1000,
    seed: Optional[int] = None,
) -> BootstrapCI:
    """
    Compute a bootstrap confidence interval for a statistic.

    Args:
        data: 1-D array of observations.
        statistic: Function that computes the statistic of interest.
        ci_level: Confidence level (default 0.95 for 95% CI).
        n_iterations: Number of bootstrap resamples.
        seed: Optional RNG seed for reproducibility.

    Returns:
        ``BootstrapCI`` with point estimate, lower/upper bounds.
    """
    if len(data) == 0:
        return BootstrapCI(
            estimate=0.0,
            ci_lower=0.0,
            ci_upper=0.0,
            ci_level=ci_level,
            n_iterations=0,
        )

    rng = np.random.default_rng(seed)
    point_estimate = float(statistic(data))

    # Generate all bootstrap samples at once for performance
    # Shape: (n_iterations, len(data))
    indices = rng.integers(0, len(data), size=(n_iterations, len(data)))
    bootstrap_samples = data[indices]

    # Compute the statistic for each bootstrap sample
    bootstrap_stats = np.array([
        statistic(sample) for sample in bootstrap_samples
    ])

    alpha = 1 - ci_level
    ci_lower = float(np.percentile(bootstrap_stats, 100 * alpha / 2))
    ci_upper = float(np.percentile(bootstrap_stats, 100 * (1 - alpha / 2)))

    return BootstrapCI(
        estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_level=ci_level,
        n_iterations=n_iterations,
    )


def bootstrap_mean_ci(
    data: np.ndarray,
    ci_level: float = 0.95,
    n_iterations: int = 1000,
    seed: Optional[int] = None,
) -> BootstrapCI:
    """Convenience wrapper: bootstrap CI on the mean."""
    return bootstrap_ci(data, np.mean, ci_level, n_iterations, seed)


def bootstrap_diff_ci(
    a: np.ndarray,
    b: np.ndarray,
    ci_level: float = 0.95,
    n_iterations: int = 1000,
    seed: Optional[int] = None,
) -> BootstrapCI:
    """
    Bootstrap CI on the difference of means (mean(a) - mean(b)).

    Useful for cost savings: original_costs - candidate_costs.
    If sample sizes differ, resamples each independently.
    """
    if len(a) == 0 or len(b) == 0:
        return BootstrapCI(0.0, 0.0, 0.0, ci_level, 0)

    rng = np.random.default_rng(seed)
    point_estimate = float(np.mean(a) - np.mean(b))

    diffs = np.empty(n_iterations)
    for i in range(n_iterations):
        a_sample = a[rng.integers(0, len(a), size=len(a))]
        b_sample = b[rng.integers(0, len(b), size=len(b))]
        diffs[i] = np.mean(a_sample) - np.mean(b_sample)

    alpha = 1 - ci_level
    ci_lower = float(np.percentile(diffs, 100 * alpha / 2))
    ci_upper = float(np.percentile(diffs, 100 * (1 - alpha / 2)))

    return BootstrapCI(
        estimate=point_estimate,
        ci_lower=ci_lower,
        ci_upper=ci_upper,
        ci_level=ci_level,
        n_iterations=n_iterations,
    )


def welch_t_test(a: np.ndarray, b: np.ndarray) -> float:
    """
    Two-sample Welch's t-test p-value.

    Tests whether the means of *a* and *b* are significantly different.
    Returns the two-sided p-value.
    """
    if len(a) < 2 or len(b) < 2:
        return 1.0  # Not enough data for significance

    from scipy import stats
    _, p_value = stats.ttest_ind(a, b, equal_var=False)
    return float(p_value)


def cohen_d(a: np.ndarray, b: np.ndarray) -> float:
    """
    Cohen's d effect size between two groups.

    Returns positive value when mean(a) > mean(b), indicating
    the original is more expensive (good for cost savings).
    """
    if len(a) < 2 or len(b) < 2:
        return 0.0

    na, nb = len(a), len(b)
    var_a, var_b = np.var(a, ddof=1), np.var(b, ddof=1)

    # Pooled standard deviation
    pooled_std = np.sqrt(((na - 1) * var_a + (nb - 1) * var_b) / (na + nb - 2))

    if pooled_std == 0:
        return 0.0

    return float((np.mean(a) - np.mean(b)) / pooled_std)


def sample_size_adequacy(n: int, min_n: int = 20, ideal_n: int = 100) -> float:
    """
    Return a 0.0–1.0 score indicating how adequate the sample size is.

    0.0 = below minimum, 0.5 = at minimum, 1.0 = at or above ideal.
    """
    if n < min_n:
        return 0.0
    if n >= ideal_n:
        return 1.0
    # Linear interpolation between min and ideal
    return (n - min_n) / (ideal_n - min_n)

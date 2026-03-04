"""
Staxx Intelligence — Pareto Frontier Detection

Identifies candidate models that are Pareto-optimal: not dominated
by any other candidate on any pair of metrics.

A candidate A *dominates* candidate B if A is better or equal on
ALL criteria and strictly better on at least one.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ParetoCandidate:
    """
    Candidate with normalised scores for Pareto analysis.

    All values are normalised so that HIGHER = BETTER.
    """

    candidate_model: str
    cost_score: float       # Higher = more savings
    latency_score: float    # Higher = lower latency (inverted)
    quality_score: float    # Higher = better quality
    error_score: float      # Higher = fewer errors (inverted)
    consistency_score: float  # Higher = more consistent (inverted)


def find_pareto_optimal(candidates: list[ParetoCandidate]) -> set[str]:
    """
    Find the set of Pareto-optimal candidate model names.

    A candidate is Pareto-optimal if no other candidate dominates it
    across ALL dimensions simultaneously.

    Args:
        candidates: List of candidates with normalised scores.

    Returns:
        Set of candidate model names that lie on the Pareto frontier.
    """
    if not candidates:
        return set()

    if len(candidates) == 1:
        return {candidates[0].candidate_model}

    n = len(candidates)

    # Build matrix: rows = candidates, cols = criteria
    matrix = np.zeros((n, 5))
    for i, c in enumerate(candidates):
        matrix[i] = [
            c.cost_score,
            c.latency_score,
            c.quality_score,
            c.error_score,
            c.consistency_score,
        ]

    pareto_set: set[str] = set()

    for i in range(n):
        is_dominated = False
        for j in range(n):
            if i == j:
                continue
            # j dominates i if j is >= on all and > on at least one
            if np.all(matrix[j] >= matrix[i]) and np.any(matrix[j] > matrix[i]):
                is_dominated = True
                break

        if not is_dominated:
            pareto_set.add(candidates[i].candidate_model)

    return pareto_set


def build_pareto_candidate(
    candidate_model: str,
    cost_savings_pct: float,
    latency_p95_ms: float,
    quality_score: float,
    error_rate: float,
    consistency_cv: float,
    max_latency_ms: float = 10000.0,
    max_cv: float = 2.0,
) -> ParetoCandidate:
    """
    Build a ``ParetoCandidate`` with properly normalised scores.

    Inverts "lower is better" metrics so all dimensions are
    "higher is better" for the dominance comparison.
    """
    # Cost: already higher = better (savings %)
    cost_score = max(0.0, cost_savings_pct / 100.0)

    # Latency: invert (lower ms = higher score)
    if max_latency_ms > 0:
        latency_score = max(0.0, 1.0 - latency_p95_ms / max_latency_ms)
    else:
        latency_score = 1.0

    # Quality: already higher = better
    quality_s = max(0.0, min(1.0, quality_score))

    # Error rate: invert (lower error = higher score)
    error_score = max(0.0, 1.0 - error_rate)

    # Consistency CV: invert (lower CV = higher score)
    if max_cv > 0:
        consistency_score = max(0.0, 1.0 - consistency_cv / max_cv)
    else:
        consistency_score = 1.0

    return ParetoCandidate(
        candidate_model=candidate_model,
        cost_score=cost_score,
        latency_score=latency_score,
        quality_score=quality_s,
        error_score=error_score,
        consistency_score=consistency_score,
    )
